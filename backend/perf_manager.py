"""
perf_manager.py — CheckMyServer Phase 5
k6 Performance Test Orchestration Engine

Responsibilities:
  - Generate temporary k6 JavaScript test scripts
  - Execute k6 via subprocess with timeout protection
  - Parse k6 JSON output to extract structured metrics
  - Compute degradation vs. historical benchmarks
  - Classify warning levels (none/warning/critical/degraded)
"""

import os
import json
import tempfile
import subprocess
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import database as db


# ---------------------------------------------------------------------------
# Config Defaults (overridden by config.json values passed in)
# ---------------------------------------------------------------------------

DEFAULT_MAX_VUS              = 50
DEFAULT_MAX_DURATION_SECONDS = 120
DEFAULT_LATENCY_WARN_MS      = 1000.0   # ms
DEFAULT_FAILURE_CRITICAL_PCT = 40.0     # %
DEFAULT_DEGRADATION_FACTOR   = 3.0      # 3× slower → degraded


# ---------------------------------------------------------------------------
# k6 Script Generator
# ---------------------------------------------------------------------------

def generate_k6_script(url: str, vus: int, duration_seconds: int,
                        method: str = 'GET',
                        headers: Optional[Dict] = None,
                        body: Optional[str] = None) -> str:
    """
    Generate a k6 JavaScript test script as a string.
    Returns the script content (not a file path).
    """
    method = method.upper()
    headers_json = json.dumps(headers or {})

    if method in ('POST', 'PUT', 'PATCH') and body:
        body_escaped = json.dumps(body)
        request_call = f'http.{method.lower()}(url, {body_escaped}, {{ headers }});'
    else:
        request_call = f'http.{method.lower()}(url, null, {{ headers }});'

    script = f"""import http from 'k6/http';
import {{ sleep, check }} from 'k6';

export const options = {{
  vus: {vus},
  duration: '{duration_seconds}s',
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)', 'count'],
}};

const url     = '{url}';
const headers = {headers_json};

export default function () {{
  const res = {request_call}
  check(res, {{
    'status is 2xx': (r) => r.status >= 200 && r.status < 300,
    'status is not 0': (r) => r.status !== 0,
  }});
  sleep(0.1);
}}
"""
    return script


# ---------------------------------------------------------------------------
# Metrics Parser
# ---------------------------------------------------------------------------

def parse_k6_summary(summary_json: Dict) -> Dict[str, Any]:
    """
    Parse k6 --summary-export JSON output and extract key metrics.

    k6 summary format (--summary-export):
      {
        "metrics": {
          "http_req_duration": { "avg": ..., "p(95)": ..., "max": ..., "min": ... },
          "http_reqs":         { "count": ..., "rate": ... },
          "http_req_failed":   { "passes": ..., "fails": ..., "value": ... }
        }
      }
    """
    metrics_raw = summary_json.get('metrics', {})

    # http_req_duration (latency)
    duration = metrics_raw.get('http_req_duration', {})
    avg_ms   = _safe_float(duration.get('avg'))
    p95_ms   = _safe_float(duration.get('p(95)'))
    max_ms   = _safe_float(duration.get('max'))
    min_ms   = _safe_float(duration.get('min'))

    # http_reqs (throughput)
    reqs        = metrics_raw.get('http_reqs', {})
    total_reqs  = int(_safe_float(reqs.get('count', 0)))
    rps         = _safe_float(reqs.get('rate'))

    # http_req_failed (failure rate)
    failed_metric = metrics_raw.get('http_req_failed', {})
    # k6 reports fraction failed as `value`, passes = successful checks, fails = failed checks
    failure_rate_fraction = _safe_float(failed_metric.get('value', 0))
    failure_rate_pct      = round(failure_rate_fraction * 100, 2)
    success_rate_pct      = round(100.0 - failure_rate_pct, 2)
    total_failed          = int(round(total_reqs * failure_rate_fraction))

    return {
        'avg_latency_ms':   round(avg_ms, 3) if avg_ms is not None else None,
        'p95_latency_ms':   round(p95_ms, 3) if p95_ms is not None else None,
        'max_latency_ms':   round(max_ms, 3) if max_ms is not None else None,
        'min_latency_ms':   round(min_ms, 3) if min_ms is not None else None,
        'success_rate':     success_rate_pct,
        'failure_rate':     failure_rate_pct,
        'requests_per_sec': round(rps, 3) if rps is not None else None,
        'total_requests':   total_reqs,
        'total_failed':     total_failed,
    }


def _safe_float(value) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Degradation Detection
# ---------------------------------------------------------------------------

def compute_degradation(url: str, current_avg_ms: Optional[float]) -> Optional[float]:
    """
    Compare current avg_latency_ms against the rolling average of the last
    5 benchmarks for the same URL.

    Returns degradation_pct:
      - Positive: current is X% SLOWER than historical avg
      - Negative: current is X% FASTER than historical avg
      - None: not enough historical data
    """
    if current_avg_ms is None:
        return None

    history = db.get_recent_benchmarks_for_url(url, limit=5)
    if not history:
        return None

    historical_avgs = [
        h['avg_latency_ms'] for h in history
        if h.get('avg_latency_ms') is not None
    ]
    if not historical_avgs:
        return None

    hist_avg = sum(historical_avgs) / len(historical_avgs)
    if hist_avg == 0:
        return None

    degradation_pct = ((current_avg_ms - hist_avg) / hist_avg) * 100
    return round(degradation_pct, 2)


# ---------------------------------------------------------------------------
# Warning Level Classifier
# ---------------------------------------------------------------------------

def classify_warning_level(metrics: Dict[str, Any],
                            latency_warn_ms: float = DEFAULT_LATENCY_WARN_MS,
                            failure_critical_pct: float = DEFAULT_FAILURE_CRITICAL_PCT,
                            degradation_factor: float = DEFAULT_DEGRADATION_FACTOR,
                            historical_avg_ms: Optional[float] = None) -> str:
    """
    Classify overall test health into: none | warning | critical | degraded.

    Priority (highest first):
      critical  — failure rate ≥ failure_critical_pct%
      degraded  — avg latency ≥ degradation_factor × historical average
      warning   — avg latency ≥ latency_warn_ms threshold
      none      — all good
    """
    failure_rate = metrics.get('failure_rate', 0) or 0
    avg_ms       = metrics.get('avg_latency_ms')

    if failure_rate >= failure_critical_pct:
        return 'critical'

    if avg_ms is not None and historical_avg_ms is not None and historical_avg_ms > 0:
        if avg_ms >= degradation_factor * historical_avg_ms:
            return 'degraded'

    if avg_ms is not None and avg_ms >= latency_warn_ms:
        return 'warning'

    return 'none'


# ---------------------------------------------------------------------------
# k6 Executor
# ---------------------------------------------------------------------------

def run_k6_test(test_id: int, url: str, vus: int, duration_seconds: int,
                method: str = 'GET',
                headers_str: Optional[str] = None,
                body: Optional[str] = None,
                perf_config: Optional[Dict] = None,
                sse_publish_fn=None):
    """
    Execute a k6 load test synchronously (designed to run in a background thread).

    Steps:
      1. Mark test as 'running' in DB
      2. Write temp k6 script to disk
      3. Run k6 with --summary-export to a temp JSON file
      4. Parse metrics from the summary JSON
      5. Compute degradation vs. historical benchmarks
      6. Classify warning level
      7. Save metrics to DB
      8. Mark test as 'completed' (or 'failed')
      9. Publish SSE event if sse_publish_fn provided
      10. Clean up temp files
    """
    cfg = perf_config or {}
    latency_warn   = cfg.get('latency_warning_threshold_ms', DEFAULT_LATENCY_WARN_MS)
    fail_critical  = cfg.get('failure_rate_critical_pct', DEFAULT_FAILURE_CRITICAL_PCT)

    # Parse headers JSON
    headers_dict: Optional[Dict] = None
    if headers_str:
        try:
            headers_dict = json.loads(headers_str)
        except (json.JSONDecodeError, TypeError):
            headers_dict = None

    script_content = generate_k6_script(url, vus, duration_seconds, method,
                                         headers_dict, body)

    script_file  = None
    summary_file = None

    try:
        # -- Mark as running --------------------------------------------------
        db.update_perf_test_status(
            test_id, 'running',
            started_at=datetime.now(timezone.utc).isoformat()
        )

        # -- Write temp script ------------------------------------------------
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', delete=False, encoding='utf-8'
        ) as sf:
            sf.write(script_content)
            script_file = sf.name

        # -- Write temp summary output path -----------------------------------
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as out:
            summary_file = out.name

        # -- Execute k6 -------------------------------------------------------
        timeout = duration_seconds + 45  # generous buffer

        import shutil
        k6_bin = shutil.which('k6') or r'C:\Program Files\k6\k6.exe'

        cmd = [
            k6_bin, 'run',
            '--summary-export', summary_file,
            '--quiet',
            script_file,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
        )

        # -- Parse summary JSON -----------------------------------------------
        metrics: Dict[str, Any] = {}
        parse_error = None

        if os.path.exists(summary_file) and os.path.getsize(summary_file) > 0:
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                metrics = parse_k6_summary(summary_data)
            except Exception as e:
                parse_error = f"Failed to parse k6 summary: {e}"
        else:
            # k6 may have failed to run — capture stderr
            stderr_snippet = (proc.stderr or '')[:500]
            parse_error = f"k6 produced no summary output. stderr: {stderr_snippet}"

        if parse_error and not metrics:
            db.update_perf_test_status(
                test_id, 'failed',
                completed_at=datetime.now(timezone.utc).isoformat(),
                error_message=parse_error
            )
            _publish_sse(sse_publish_fn, test_id, 'failed', None)
            return

        # -- Compute degradation ----------------------------------------------
        degradation_pct = compute_degradation(url, metrics.get('avg_latency_ms'))
        metrics['degradation_pct'] = degradation_pct

        # -- Determine historical avg for warning classification --------------
        history = db.get_recent_benchmarks_for_url(url, limit=5)
        hist_avgs = [
            h['avg_latency_ms'] for h in history
            if h.get('avg_latency_ms') is not None
        ]
        hist_avg_ms = (sum(hist_avgs) / len(hist_avgs)) if hist_avgs else None

        # -- Classify warning level -------------------------------------------
        warning_level = classify_warning_level(
            metrics,
            latency_warn_ms=latency_warn,
            failure_critical_pct=fail_critical,
            historical_avg_ms=hist_avg_ms,
        )
        metrics['warning_level'] = warning_level

        # -- Save metrics to DB -----------------------------------------------
        db.save_perf_metrics(test_id, metrics)

        # -- Mark completed ---------------------------------------------------
        db.update_perf_test_status(
            test_id, 'completed',
            completed_at=datetime.now(timezone.utc).isoformat()
        )

        # -- Publish SSE event ------------------------------------------------
        _publish_sse(sse_publish_fn, test_id, 'completed', metrics)
        print(f"[PerfManager] Test #{test_id} completed. "
              f"avg={metrics.get('avg_latency_ms')}ms "
              f"rps={metrics.get('requests_per_sec')} "
              f"warning={warning_level}")

    except subprocess.TimeoutExpired:
        err = f"k6 test timed out after {duration_seconds + 45}s"
        db.update_perf_test_status(
            test_id, 'failed',
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=err
        )
        _publish_sse(sse_publish_fn, test_id, 'failed', None)
        print(f"[PerfManager] Test #{test_id} timed out.")

    except FileNotFoundError:
        err = ("k6 executable not found. "
               "Please install k6: https://k6.io/docs/getting-started/installation/")
        db.update_perf_test_status(
            test_id, 'failed',
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=err
        )
        _publish_sse(sse_publish_fn, test_id, 'failed', None)
        print(f"[PerfManager] k6 not found for test #{test_id}.")

    except Exception as e:
        err = f"Unexpected error: {e}"
        db.update_perf_test_status(
            test_id, 'failed',
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=err
        )
        _publish_sse(sse_publish_fn, test_id, 'failed', None)
        print(f"[PerfManager] Test #{test_id} failed: {e}")

    finally:
        # -- Cleanup temp files -----------------------------------------------
        for f in [script_file, summary_file]:
            if f and os.path.exists(f):
                try:
                    os.unlink(f)
                except OSError:
                    pass


def _publish_sse(fn, test_id: int, status: str, metrics: Optional[Dict]):
    """Helper to publish SSE event if a publish function is provided."""
    if fn is None:
        return
    try:
        payload = {
            'type':    'perf_test_completed',
            'data': {
                'test_id': test_id,
                'status':  status,
                'metrics': metrics,
            }
        }
        fn(payload)
    except Exception as e:
        print(f"[PerfManager] SSE publish error: {e}")


# ---------------------------------------------------------------------------
# Thread Launcher
# ---------------------------------------------------------------------------

def start_test_thread(test_id: int, url: str, vus: int, duration_seconds: int,
                       method: str = 'GET',
                       headers_str: Optional[str] = None,
                       body: Optional[str] = None,
                       perf_config: Optional[Dict] = None,
                       sse_publish_fn=None) -> threading.Thread:
    """
    Launch run_k6_test in a daemon background thread.
    Returns the Thread object (already started).
    """
    t = threading.Thread(
        target=run_k6_test,
        args=(test_id, url, vus, duration_seconds, method,
              headers_str, body, perf_config, sse_publish_fn),
        daemon=True,
        name=f"k6-test-{test_id}",
    )
    t.start()
    return t

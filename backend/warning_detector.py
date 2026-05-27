"""
Warning Detector module for CheckMyServer
Detects intelligent warning conditions beyond simple threshold checks:
- Latency spikes (current > N× rolling baseline)
- Repeated instability patterns
"""

from typing import Dict, Optional
import database as db
import error_classifier as ec


# ── Tuneable constants ───────────────────────────────────────────────────────
SPIKE_MULTIPLIER       = 3.0   # current latency > 3× baseline → spike warning
INSTABILITY_WINDOW     = 10    # look at last N checks
INSTABILITY_THRESHOLD  = 3     # if ≥ this many are non-UP in last N checks → instability


def analyze_performance(server_id: int, check_result: Dict) -> Dict:
    """
    Analyze a completed check result for intelligent warning conditions.

    This enriches the check_result with an upgraded severity/category if a
    latency spike or instability pattern is detected, even when the raw HTTP
    status is 200 OK.

    Args:
        server_id:    Database ID of the server
        check_result: Full result dict from health_checker (mutated in place)

    Returns:
        The (possibly mutated) check_result dict.
    """
    # Only analyze UP checks — DOWN/WARNING are already classified
    if check_result.get("status") != "UP":
        return check_result

    response_time = check_result.get("response_time")
    if not response_time:
        return check_result

    # ── Latency spike detection ──────────────────────────────────────────────
    baseline = db.get_latency_baseline(server_id, sample_size=20)
    if baseline and baseline > 0:
        ratio = response_time / baseline
        if ratio >= SPIKE_MULTIPLIER:
            pct_increase = int((ratio - 1) * 100)
            check_result["error_category"]  = "Latency Spike"
            check_result["severity"]        = ec.SEVERITY_WARNING
            check_result["user_message"]    = (
                f"Response time is {pct_increase}% above the rolling baseline "
                f"({response_time:.3f}s vs baseline {baseline:.3f}s)."
            )
            check_result["suggested_cause"] = (
                "The server may be experiencing a sudden load increase, "
                "a blocking operation, or a memory/CPU bottleneck."
            )
            check_result["baseline_latency"] = baseline
            # Upgrade to WARNING status if we detect a significant spike
            check_result["status"] = "WARNING"
            return check_result

    # ── Repeated instability detection ──────────────────────────────────────
    recent_history = db.get_check_history(server_id, limit=INSTABILITY_WINDOW)
    if len(recent_history) >= INSTABILITY_WINDOW:
        non_up_count = sum(1 for h in recent_history if h.get("status") != "UP")
        if non_up_count >= INSTABILITY_THRESHOLD:
            check_result["error_category"]  = "Repeated Instability"
            check_result["severity"]        = ec.SEVERITY_WARNING
            check_result["user_message"]    = (
                f"Server has been unstable: {non_up_count} of the last "
                f"{INSTABILITY_WINDOW} checks were non-healthy."
            )
            check_result["suggested_cause"] = (
                "The server may be intermittently failing under load or "
                "experiencing flapping network connectivity."
            )
            # Don't upgrade status — just flag the pattern for alerting

    return check_result


def get_instability_score(server_id: int, window: int = 10) -> float:
    """
    Return a 0.0–1.0 instability score for the last N checks.
    0.0 = perfectly stable, 1.0 = all checks failed.
    """
    history = db.get_check_history(server_id, limit=window)
    if not history:
        return 0.0
    non_up = sum(1 for h in history if h.get("status") != "UP")
    return round(non_up / len(history), 2)

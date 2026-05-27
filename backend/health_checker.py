"""
Health Checker module for CheckMyServer
Performs HTTP checks, determines server status, and enriches results
with human-readable error classifications and severity levels via error_classifier.
"""

import aiohttp
import asyncio
import time
from typing import Dict, Optional
import error_classifier as ec


# Default thresholds (overridden by config passed from main.py)
DEFAULT_WARNING_THRESHOLD_S = 3.0
DEFAULT_HEALTHY_THRESHOLD_S = 1.0


async def check_server_health_async(
    url: str,
    timeout: int = 10,
    warning_threshold_s: float = DEFAULT_WARNING_THRESHOLD_S,
) -> Dict:
    """
    Check the health of a server asynchronously via HTTP GET request.

    Returns a result dict with:
        status            : UP | DOWN | WARNING
        response_time     : float (seconds) or None
        http_status_code  : int or None
        error             : raw error string (internal use / logs)
        error_category    : human-readable category from error_classifier
        severity          : healthy | warning | critical
        user_message      : friendly one-liner for display / emails
        suggested_cause   : suggested diagnosis for alerts
    """
    result = {
        "status":          "DOWN",
        "response_time":   None,
        "http_status_code": None,
        "error":           None,
        # Enriched fields from error_classifier
        "error_category":  None,
        "severity":        ec.SEVERITY_CRITICAL,
        "user_message":    None,
        "suggested_cause": None,
    }

    if not url:
        classification = ec.classify_error("URL is empty")
        result.update(_apply_classification(classification))
        result["error"] = "URL is empty"
        return result

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    start_time = time.time()

    try:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                response_time = time.time() - start_time
                result["response_time"]    = round(response_time, 3)
                result["http_status_code"] = response.status

                # Consume response body fully
                await response.read()

                # ── Determine status and classification ──────────────────────
                if response.status >= 500:
                    result["status"] = "DOWN"
                    raw_err = f"HTTP {response.status}"
                    result["error"] = raw_err
                    classification = ec.classify_error(raw_err, response.status)
                    result.update(_apply_classification(classification))

                elif response.status >= 400:
                    # 4xx → treat as DOWN but WARNING severity
                    result["status"] = "DOWN"
                    raw_err = f"HTTP {response.status}"
                    result["error"] = raw_err
                    classification = ec.classify_error(raw_err, response.status)
                    result.update(_apply_classification(classification))

                elif 200 <= response.status < 400:
                    # Check response time thresholds for warning
                    if response_time >= warning_threshold_s:
                        result["status"] = "WARNING"
                        raw_err = f"Slow response ({response_time:.3f}s)"
                        result["error"] = raw_err
                        classification = ec.classify_by_response_time(
                            response_time, warning_threshold_s
                        )
                        result.update(_apply_classification(classification))
                    else:
                        result["status"]   = "UP"
                        classification     = ec._healthy_result()
                        result.update(_apply_classification(classification))
                else:
                    result["status"] = "DOWN"
                    raw_err = f"HTTP {response.status}"
                    result["error"] = raw_err
                    classification = ec.classify_error(raw_err, response.status)
                    result.update(_apply_classification(classification))

                return result

    except asyncio.TimeoutError:
        response_time = time.time() - start_time
        result["response_time"] = round(response_time, 3)
        result["status"]        = "DOWN"
        result["error"]         = f"Timeout after {timeout}s"
        classification = ec.classify_error("timeout")
        result.update(_apply_classification(classification))
        return result

    except aiohttp.TooManyRedirects:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"]        = "DOWN"
        result["error"]         = "Too many redirects"
        classification = ec.classify_error("too many redirects")
        result.update(_apply_classification(classification))
        return result

    except aiohttp.ClientConnectorError as e:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"]        = "DOWN"
        result["error"]         = str(e)
        classification = ec.classify_error(str(e))
        result.update(_apply_classification(classification))
        return result

    except aiohttp.ClientSSLError as e:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"]        = "DOWN"
        result["error"]         = str(e)
        classification = ec.classify_error("ssl " + str(e))
        result.update(_apply_classification(classification))
        return result

    except aiohttp.ClientError as e:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"]        = "DOWN"
        result["error"]         = str(e)
        classification = ec.classify_error(str(e))
        result.update(_apply_classification(classification))
        return result

    except Exception as e:
        result["status"] = "DOWN"
        result["error"]  = str(e)
        classification = ec.classify_error(str(e))
        result.update(_apply_classification(classification))
        return result


def _apply_classification(classification: Dict) -> Dict:
    """Extract the error_classifier fields to merge into check result."""
    return {
        "error_category":  classification.get("category"),
        "severity":        classification.get("severity"),
        "user_message":    classification.get("user_message"),
        "suggested_cause": classification.get("suggested_cause"),
    }


def check_server_health(url: str, timeout: int = 10,
                         warning_threshold_s: float = DEFAULT_WARNING_THRESHOLD_S) -> Dict:
    """
    Synchronous wrapper for check_server_health_async (backward compatibility).
    """
    try:
        return asyncio.run(check_server_health_async(url, timeout, warning_threshold_s))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            check_server_health_async(url, timeout, warning_threshold_s)
        )


def is_status_up(http_code: Optional[int]) -> bool:
    """Check if HTTP status code indicates UP"""
    if http_code is None:
        return False
    return 200 <= http_code < 400


def format_health_check_result(result: Dict, server_name: str) -> str:
    """Format health check result for terminal printing"""
    status = result["status"]
    if status == "UP":
        status_symbol = "🟢"
    elif status == "WARNING":
        status_symbol = "🟡"
    else:
        status_symbol = "🔴"

    output = f"{status_symbol} {server_name}: {status}"

    if result["response_time"] is not None:
        output += f" ({result['response_time']:.3f}s)"

    # Show classified category instead of raw error
    if result.get("error_category") and result["error_category"] != "Healthy":
        output += f" — {result['error_category']}"
    elif result.get("error"):
        output += f" — {result['error']}"

    return output
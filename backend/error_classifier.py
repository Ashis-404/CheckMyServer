"""
Error Classifier module for CheckMyServer
Converts raw Python/network exceptions into human-readable, categorized diagnostics.
Eliminates raw stack traces from user-facing alerts and dashboard.
"""

from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------
SEVERITY_HEALTHY  = "healthy"
SEVERITY_WARNING  = "warning"
SEVERITY_CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Error classification rules
# Each rule is checked in order; first match wins.
# ---------------------------------------------------------------------------
_CLASSIFICATION_RULES = [
    # ── SSL / Certificate errors ────────────────────────────────────────────
    {
        "patterns": [
            "certificate_verify_failed",
            "ssl",
            "certificate",
            "cert",
            "handshake",
        ],
        "category":       "SSL Certificate Error",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server's SSL certificate could not be verified.",
        "suggested_cause": (
            "The certificate may be expired, self-signed, or issued for a different domain. "
            "Check your certificate validity and renewal date."
        ),
    },
    # ── DNS resolution failures ─────────────────────────────────────────────
    {
        "patterns": [
            "enotfound",
            "name or service not known",
            "nodename nor servname provided",
            "getaddrinfo",
            "failed to resolve",
            "temporary failure in name resolution",
        ],
        "category":       "DNS Resolution Failed",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server's hostname could not be resolved.",
        "suggested_cause": (
            "The domain name may be misspelled, DNS records may be misconfigured, "
            "or the domain may have expired."
        ),
    },
    # ── Connection refused ──────────────────────────────────────────────────
    {
        "patterns": [
            "winerror 10061",
            "connection refused",
            "econnrefused",
            "connect call failed",
            "no connection could be made",
        ],
        "category":       "Connection Refused",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server actively refused the connection.",
        "suggested_cause": (
            "No service is listening on the target port, the server firewall may be "
            "blocking requests, or the application process may be stopped."
        ),
    },
    # ── Connection timeout ──────────────────────────────────────────────────
    {
        "patterns": [
            "timeout",
            "timed out",
            "etimedout",
            "asyncio.timeouterror",
        ],
        "category":       "Connection Timeout",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server did not respond within the timeout window.",
        "suggested_cause": (
            "The server may be overloaded, the network path may be congested, "
            "or a firewall is silently dropping packets."
        ),
    },
    # ── Too many redirects ──────────────────────────────────────────────────
    {
        "patterns": [
            "too many redirects",
            "redirect",
            "exceeded",
        ],
        "category":       "Too Many Redirects",
        "severity":       SEVERITY_WARNING,
        "user_message":   "The server is caught in a redirect loop.",
        "suggested_cause": (
            "Check for misconfigured HTTP→HTTPS redirect rules or circular proxy rules."
        ),
    },
    # ── HTTP 5xx server errors ──────────────────────────────────────────────
    {
        "patterns": ["http 503"],
        "category":       "Service Unavailable",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server returned HTTP 503 — Service Unavailable.",
        "suggested_cause": (
            "The server may be under maintenance, overloaded, or its upstream "
            "dependencies are failing."
        ),
    },
    {
        "patterns": ["http 502"],
        "category":       "Bad Gateway",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server returned HTTP 502 — Bad Gateway.",
        "suggested_cause": (
            "A reverse proxy or load balancer received an invalid response "
            "from the upstream application server."
        ),
    },
    {
        "patterns": ["http 500"],
        "category":       "Internal Server Error",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server returned HTTP 500 — Internal Server Error.",
        "suggested_cause": (
            "The application threw an unhandled exception. Check server logs "
            "for stack traces and error details."
        ),
    },
    {
        "patterns": ["http 5"],
        "category":       "Server Error",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "The server returned a 5xx error response.",
        "suggested_cause": (
            "An unexpected server-side error occurred. Review application logs."
        ),
    },
    # ── HTTP 4xx client errors ──────────────────────────────────────────────
    {
        "patterns": ["http 404"],
        "category":       "Not Found",
        "severity":       SEVERITY_WARNING,
        "user_message":   "The server returned HTTP 404 — Not Found.",
        "suggested_cause": (
            "The monitored URL path may have changed. Update the server URL to "
            "a valid endpoint."
        ),
    },
    {
        "patterns": ["http 401", "http 403"],
        "category":       "Access Denied",
        "severity":       SEVERITY_WARNING,
        "user_message":   "The server returned an authorization error (401/403).",
        "suggested_cause": (
            "The monitoring request may require authentication credentials, "
            "or the IP may be blocked."
        ),
    },
    {
        "patterns": ["http 4"],
        "category":       "Client Error",
        "severity":       SEVERITY_WARNING,
        "user_message":   "The server returned a 4xx error response.",
        "suggested_cause": (
            "The request was rejected by the server. Check the monitored URL and headers."
        ),
    },
    # ── Slow response (populated by health_checker, not exception) ──────────
    {
        "patterns": ["slow response", "high latency"],
        "category":       "Slow Response",
        "severity":       SEVERITY_WARNING,
        "user_message":   "The server responded but with degraded performance.",
        "suggested_cause": (
            "The server may be under load, running resource-intensive tasks, "
            "or experiencing network congestion."
        ),
    },
    # ── Generic network/connection errors ───────────────────────────────────
    {
        "patterns": [
            "cannot connect to host",
            "network unreachable",
            "no route to host",
            "connection reset",
            "connection aborted",
            "broken pipe",
            "clientconnectorerror",
            "connection failed",
        ],
        "category":       "Network Error",
        "severity":       SEVERITY_CRITICAL,
        "user_message":   "A network-level error prevented connecting to the server.",
        "suggested_cause": (
            "The server may be offline, the network path may be disrupted, "
            "or a firewall may be blocking access."
        ),
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_error(error_message: Optional[str], http_status_code: Optional[int] = None) -> Dict:
    """
    Classify a monitoring error into a human-readable category with severity.

    Args:
        error_message:   The raw error string from the health checker
        http_status_code: The HTTP status code if available

    Returns:
        Dict with keys: category, severity, user_message, suggested_cause
    """
    if not error_message and http_status_code and 200 <= http_status_code < 400:
        return _healthy_result()

    search_text = (error_message or "").lower()

    # Also incorporate HTTP code patterns into search text for unified matching
    if http_status_code:
        search_text += f" http {http_status_code}"

    for rule in _CLASSIFICATION_RULES:
        for pattern in rule["patterns"]:
            if pattern in search_text:
                return {
                    "category":        rule["category"],
                    "severity":        rule["severity"],
                    "user_message":    rule["user_message"],
                    "suggested_cause": rule["suggested_cause"],
                }

    # Fallback for unknown errors
    if error_message:
        return {
            "category":        "Unknown Error",
            "severity":        SEVERITY_CRITICAL,
            "user_message":    "An unexpected error occurred while contacting the server.",
            "suggested_cause": (
                "This error type is not yet classified. Review your server logs for details."
            ),
        }

    return _healthy_result()


def classify_by_response_time(response_time_s: float,
                               warning_threshold_s: float = 3.0,
                               healthy_threshold_s: float = 1.0) -> Dict:
    """
    Classify severity purely based on response time (for UP servers with slow responses).

    Args:
        response_time_s:      Response time in seconds
        warning_threshold_s:  Threshold above which to flag as Warning (default 3.0s)
        healthy_threshold_s:  Threshold above which to flag as slightly degraded (default 1.0s)
    """
    if response_time_s >= warning_threshold_s:
        return {
            "category":        "Slow Response",
            "severity":        SEVERITY_WARNING,
            "user_message":    f"Server responded in {response_time_s:.3f}s — above warning threshold.",
            "suggested_cause": (
                "The server may be under load, running resource-intensive tasks, "
                "or experiencing network congestion."
            ),
        }
    return _healthy_result()


def get_severity_for_status(status: str) -> str:
    """Map a monitoring status string to a severity level."""
    mapping = {
        "UP":      SEVERITY_HEALTHY,
        "WARNING": SEVERITY_WARNING,
        "DOWN":    SEVERITY_CRITICAL,
    }
    return mapping.get(status, SEVERITY_CRITICAL)


def _healthy_result() -> Dict:
    return {
        "category":        "Healthy",
        "severity":        SEVERITY_HEALTHY,
        "user_message":    "Server is responding normally.",
        "suggested_cause": "",
    }

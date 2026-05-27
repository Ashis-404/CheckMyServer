"""
Incident Manager module for CheckMyServer
Manages incident lifecycle: creation on consecutive failures, resolution on recovery.
Decoupled from main.py so it can be tested independently.
"""

from datetime import datetime
from typing import Dict, Optional, Tuple
import database as db


def format_duration(seconds: int) -> str:
    """Convert seconds into a human-readable duration string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s}s"
    else:
        h, rem = divmod(seconds, 3600)
        m, s   = divmod(rem, 60)
        return f"{h}h {m}m {s}s"


def handle_server_result(
    server_id:           int,
    server_name:         str,
    check_result:        Dict,
    current_stable_status:  str,
    previous_stable_status: str,
) -> Optional[Dict]:
    """
    Evaluate a completed health check and manage incident lifecycle.

    Rules:
    - UP   → DOWN/WARNING : Create incident (if none active)
    - DOWN/WARNING → UP   : Resolve active incident (if any)
    - No change           : No-op

    Args:
        server_id:              Database ID of the server
        server_name:            Display name of the server
        check_result:           Full result dict from health_checker
        current_stable_status:  Stable status after this check
        previous_stable_status: Stable status before this check

    Returns:
        An incident_event dict for SSE broadcasting, or None if no change occurred.
        {
          "event_type": "incident_created" | "incident_resolved",
          "incident":   { ... incident fields ... },
          "downtime_duration": "5m 30s"   (only on resolved)
        }
    """
    status_changed = current_stable_status != previous_stable_status

    # ── Transition: healthy → degraded / down → create incident ─────────────
    if status_changed and current_stable_status in ("DOWN", "WARNING"):
        # Don't create a duplicate incident if one is already active
        existing = db.get_active_incident(server_id)
        if not existing:
            reason          = check_result.get("user_message") or check_result.get("error") or "Unknown failure"
            error_category  = check_result.get("error_category")
            severity        = check_result.get("severity", "critical")
            # Normalize severity: WARNING status maps to "warning"
            if current_stable_status == "WARNING":
                severity = "warning"

            incident_id = db.create_incident(server_id, reason, error_category, severity)
            if incident_id:
                incident = db.get_active_incident(server_id)
                return {
                    "event_type": "incident_created",
                    "incident":   _serialize_incident(incident, server_name),
                    "downtime_duration": None,
                }

    # ── Transition: degraded → recovered → resolve incident ─────────────────
    elif status_changed and current_stable_status == "UP" and previous_stable_status in ("DOWN", "WARNING"):
        active = db.get_active_incident(server_id)
        if active:
            resolved = db.resolve_incident(active["id"])
            if resolved:
                duration_s   = resolved.get("duration_seconds") or 0
                duration_str = format_duration(duration_s)
                return {
                    "event_type":         "incident_resolved",
                    "incident":           _serialize_incident(resolved, server_name),
                    "downtime_duration":  duration_str,
                    "duration_seconds":   duration_s,
                    "response_time":      check_result.get("response_time"),
                }

    return None


def _serialize_incident(incident: Optional[Dict], server_name: str) -> Dict:
    """Normalize an incident dict for API/SSE consumption."""
    if not incident:
        return {}
    d = dict(incident)
    d["server_name"] = d.get("server_name") or server_name
    return d


def get_active_incidents_summary() -> Dict:
    """Return a summary count of active incidents across all servers."""
    active = db.get_incidents(status="active")
    critical = sum(1 for i in active if i.get("severity") == "critical")
    warning  = sum(1 for i in active if i.get("severity") == "warning")
    return {
        "total_active":    len(active),
        "critical_active": critical,
        "warning_active":  warning,
    }

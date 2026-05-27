"""
Email Templates module for CheckMyServer
Generates professional HTML (+ plain-text fallback) email bodies for all alert types.
All CSS is inline for maximum email client compatibility.
"""

from datetime import datetime
from typing import Dict, Optional


# ── Shared brand colors ──────────────────────────────────────────────────────
_COLOR_BG       = "#0f172a"
_COLOR_CARD     = "#1e293b"
_COLOR_BORDER   = "#334155"
_COLOR_TEXT     = "#e2e8f0"
_COLOR_MUTED    = "#94a3b8"
_COLOR_CRITICAL = "#ef4444"
_COLOR_WARNING  = "#f59e0b"
_COLOR_SUCCESS  = "#10b981"
_COLOR_ACCENT   = "#38bdf8"


def _base_template(header_color: str, header_icon: str, title: str, body_html: str) -> str:
    """Wrap content in the shared email frame."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{_COLOR_BG};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:{_COLOR_BG};padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header bar -->
          <tr>
            <td style="background:{header_color};border-radius:12px 12px 0 0;padding:28px 32px;text-align:center;">
              <div style="font-size:42px;line-height:1;">{header_icon}</div>
              <h1 style="margin:12px 0 0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:-0.3px;">{title}</h1>
            </td>
          </tr>

          <!-- Card body -->
          <tr>
            <td style="background-color:{_COLOR_CARD};padding:32px;border-left:1px solid {_COLOR_BORDER};border-right:1px solid {_COLOR_BORDER};">
              {body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:{_COLOR_BG};border-radius:0 0 12px 12px;border:1px solid {_COLOR_BORDER};border-top:none;padding:20px 32px;text-align:center;">
              <p style="margin:0;color:{_COLOR_MUTED};font-size:12px;">
                Sent by <strong style="color:{_COLOR_ACCENT};">CheckMyServer</strong> — Real-time Infrastructure Monitoring
              </p>
              <p style="margin:6px 0 0;color:{_COLOR_BORDER};font-size:11px;">You are receiving this because you registered this endpoint for monitoring.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _stat_row(label: str, value: str, value_color: str = _COLOR_TEXT) -> str:
    """Render a labeled data row inside the email card."""
    return f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid {_COLOR_BORDER};">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="color:{_COLOR_MUTED};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;width:45%;">{label}</td>
            <td style="color:{value_color};font-size:14px;font-weight:600;font-family:monospace;">{value}</td>
          </tr>
        </table>
      </td>
    </tr>"""


def _severity_badge(severity: str) -> str:
    color_map = {
        "critical": (_COLOR_CRITICAL, "#fef2f2"),
        "warning":  (_COLOR_WARNING,  "#fffbeb"),
        "healthy":  (_COLOR_SUCCESS,  "#f0fdf4"),
    }
    bg, text = color_map.get(severity, (_COLOR_MUTED, _COLOR_TEXT))
    label = severity.upper()
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:9999px;'
        f'background-color:{bg}22;color:{bg};border:1px solid {bg}66;'
        f'font-size:11px;font-weight:700;letter-spacing:1px;">{label}</span>'
    )


# ============================================================================
# PUBLIC EMAIL COMPOSERS
# ============================================================================

def compose_critical_alert(server_name: str, details: Dict) -> tuple:
    """
    Generate a Critical Alert email (server DOWN).
    Returns: (subject, html_body, plain_text_body)
    """
    url              = details.get("url", "N/A")
    error_category   = details.get("error_category", "Unknown Error")
    user_message     = details.get("user_message", "The server is not responding.")
    suggested_cause  = details.get("suggested_cause", "")
    response_time    = details.get("response_time")
    timestamp        = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity         = details.get("severity", "critical")

    rt_display = f"{response_time:.3f}s" if response_time else "N/A"

    cause_block = (
        f'<div style="background-color:#0d1117;border-radius:8px;padding:16px 20px;">'
        f'<p style="margin:0 0 6px;color:{_COLOR_MUTED};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Suggested Cause</p>'
        f'<p style="margin:0;color:{_COLOR_MUTED};font-size:14px;">{suggested_cause}</p></div>'
    ) if suggested_cause else ""

    body_html = (
        f'<p style="color:{_COLOR_TEXT};font-size:15px;margin:0 0 24px;">'
        f'Your server <strong style="color:{_COLOR_ACCENT};">{server_name}</strong> has gone '
        f'<strong style="color:{_COLOR_CRITICAL};">offline</strong> and is no longer responding.</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">'
        + _stat_row("Server", server_name)
        + _stat_row("URL", f'<a href="{url}" style="color:{_COLOR_ACCENT};text-decoration:none;">{url}</a>')
        + _stat_row("Severity", _severity_badge(severity))
        + _stat_row("Issue Type", f'<span style="color:{_COLOR_CRITICAL};">{error_category}</span>', _COLOR_CRITICAL)
        + _stat_row("Response Time", rt_display)
        + _stat_row("Detected At", timestamp)
        + f'</table>'
        f'<div style="background-color:#1a0a0a;border-left:3px solid {_COLOR_CRITICAL};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">'
        f'<p style="margin:0 0 6px;color:{_COLOR_CRITICAL};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Diagnosis</p>'
        f'<p style="margin:0;color:{_COLOR_TEXT};font-size:14px;">{user_message}</p></div>'
        + cause_block
    )

    subject = f"🔴 CRITICAL: {server_name} is DOWN — {error_category}"

    plain = f"""CRITICAL ALERT: {server_name} is DOWN

Server:         {server_name}
URL:            {url}
Issue:          {error_category}
Diagnosis:      {user_message}
Response Time:  {rt_display}
Detected At:    {timestamp}

{f"Suggested Cause: {suggested_cause}" if suggested_cause else ""}

---
CheckMyServer — Real-time Infrastructure Monitoring
"""

    html = _base_template(
        header_color=f"linear-gradient(135deg,#7f1d1d,{_COLOR_CRITICAL})",
        header_icon="🔴",
        title=f"Critical Alert — {server_name} is Offline",
        body_html=body_html,
    )
    return subject, html, plain


def compose_warning_alert(server_name: str, details: Dict) -> tuple:
    """
    Generate a Warning Alert email (degraded performance).
    Returns: (subject, html_body, plain_text_body)
    """
    url              = details.get("url", "N/A")
    error_category   = details.get("error_category", "Slow Response")
    user_message     = details.get("user_message", "Server performance is degraded.")
    suggested_cause  = details.get("suggested_cause", "")
    response_time    = details.get("response_time")
    baseline         = details.get("baseline_latency")
    timestamp        = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    rt_display   = f"{response_time:.3f}s" if response_time else "N/A"
    base_display = f"{baseline:.3f}s" if baseline else "N/A"

    cause_block = (
        f'<div style="background-color:#0d1117;border-radius:8px;padding:16px 20px;">'
        f'<p style="margin:0 0 6px;color:{_COLOR_MUTED};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Suggested Cause</p>'
        f'<p style="margin:0;color:{_COLOR_MUTED};font-size:14px;">{suggested_cause}</p></div>'
    ) if suggested_cause else ""

    body_html = (
        f'<p style="color:{_COLOR_TEXT};font-size:15px;margin:0 0 24px;">'
        f'<strong style="color:{_COLOR_ACCENT};">{server_name}</strong> is responding but with '
        f'<strong style="color:{_COLOR_WARNING};">degraded performance</strong>. '
        f'Action may be required before this becomes an outage.</p>'
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">'
        + _stat_row("Server", server_name)
        + _stat_row("URL", f'<a href="{url}" style="color:{_COLOR_ACCENT};text-decoration:none;">{url}</a>')
        + _stat_row("Issue Type", f'<span style="color:{_COLOR_WARNING};">{error_category}</span>', _COLOR_WARNING)
        + _stat_row("Response Time", f'<span style="color:{_COLOR_WARNING};">{rt_display}</span>', _COLOR_WARNING)
        + _stat_row("Baseline", base_display)
        + _stat_row("Detected At", timestamp)
        + f'</table>'
        f'<div style="background-color:#1a1200;border-left:3px solid {_COLOR_WARNING};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">'
        f'<p style="margin:0 0 6px;color:{_COLOR_WARNING};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Performance Warning</p>'
        f'<p style="margin:0;color:{_COLOR_TEXT};font-size:14px;">{user_message}</p></div>'
        + cause_block
    )

    subject = f"⚠️ WARNING: {server_name} — Performance Degraded"

    plain = f"""WARNING: {server_name} — Performance Degraded

Server:         {server_name}
URL:            {url}
Issue:          {error_category}
Response Time:  {rt_display}
Baseline:       {base_display}
Detected At:    {timestamp}
Diagnosis:      {user_message}

{f"Suggested Cause: {suggested_cause}" if suggested_cause else ""}

---
CheckMyServer — Real-time Infrastructure Monitoring
"""

    html = _base_template(
        header_color=f"linear-gradient(135deg,#78350f,{_COLOR_WARNING})",
        header_icon="⚠️",
        title=f"Performance Warning — {server_name}",
        body_html=body_html,
    )
    return subject, html, plain


def compose_recovery_alert(server_name: str, details: Dict) -> tuple:
    """
    Generate a Recovery Alert email (service restored).
    Returns: (subject, html_body, plain_text_body)
    """
    url              = details.get("url", "N/A")
    response_time    = details.get("response_time")
    downtime_str     = details.get("downtime_duration", "Unknown")
    incident_reason  = details.get("incident_reason", "Service was unavailable")
    timestamp        = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    rt_display = f"{response_time:.3f}s" if response_time else "N/A"

    body_html = f"""
    <p style="color:{_COLOR_TEXT};font-size:15px;margin:0 0 24px;">
      <strong style="color:{_COLOR_ACCENT};">{server_name}</strong> has
      <strong style="color:{_COLOR_SUCCESS};">recovered</strong> and is responding normally.
      Monitoring continues automatically.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      {_stat_row("Server",           server_name)}
      {_stat_row("URL",              f'<a href="{url}" style="color:{_COLOR_ACCENT};text-decoration:none;">{url}</a>')}
      {_stat_row("Status",           f'<span style="color:{_COLOR_SUCCESS};">✓ Operational</span>', _COLOR_SUCCESS)}
      {_stat_row("Response Time",    f'<span style="color:{_COLOR_SUCCESS};">{rt_display}</span>', _COLOR_SUCCESS)}
      {_stat_row("Total Downtime",   f'<span style="color:{_COLOR_WARNING};">{downtime_str}</span>', _COLOR_WARNING)}
      {_stat_row("Restored At",      timestamp)}
    </table>

    <div style="background-color:#021f12;border-left:3px solid {_COLOR_SUCCESS};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
      <p style="margin:0 0 6px;color:{_COLOR_SUCCESS};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">Incident Summary</p>
      <p style="margin:0;color:{_COLOR_TEXT};font-size:14px;">{incident_reason}</p>
    </div>
    """

    subject = f"✅ RECOVERED: {server_name} is back online — Downtime: {downtime_str}"

    plain = f"""RECOVERY: {server_name} is back online

Server:         {server_name}
URL:            {url}
Status:         OPERATIONAL
Response Time:  {rt_display}
Total Downtime: {downtime_str}
Restored At:    {timestamp}
Incident:       {incident_reason}

---
CheckMyServer — Real-time Infrastructure Monitoring
"""

    html = _base_template(
        header_color=f"linear-gradient(135deg,#052e16,{_COLOR_SUCCESS})",
        header_icon="✅",
        title=f"Recovery Alert — {server_name} Restored",
        body_html=body_html,
    )
    return subject, html, plain

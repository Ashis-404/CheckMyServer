"""
Alert Manager module for CheckMyServer
Handles email alert sending with professional HTML templates and anti-spam logic.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv
import database as db
import email_templates as templates

load_dotenv()


# ============================================================================
# CORE EMAIL SENDER
# ============================================================================

def _resolve_smtp_password(smtp_config: Dict) -> Optional[str]:
    """Resolve SMTP password from config directly or via env var."""
    if "password" in smtp_config:
        return smtp_config["password"]
    if "password_env_var" in smtp_config:
        return os.environ.get(smtp_config["password_env_var"])
    return None


def send_email(
    config: Dict,
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: str,
) -> bool:
    """
    Send an HTML email with a plain-text fallback.

    Args:
        config:     Full app config dict (must contain smtp key)
        to_email:   Recipient email address
        subject:    Email subject line
        html_body:  Full HTML content
        plain_body: Plain-text fallback

    Returns:
        True if sent successfully, False otherwise
    """
    if not config.get("smtp"):
        print("✗ SMTP config not found in config.json")
        return False

    smtp_config = config["smtp"]

    required = ["host", "port", "username", "from_email"]
    for field in required:
        if field not in smtp_config:
            print(f"✗ Missing SMTP config field: {field}")
            return False

    if not to_email:
        print("✗ Recipient email not provided")
        return False

    password = _resolve_smtp_password(smtp_config)
    if not password:
        print("✗ SMTP password not resolved. Check config.json or environment variables.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = smtp_config["from_email"]
        msg["To"]      = to_email
        msg["Subject"] = subject

        # Attach plain text first (fallback), then HTML (preferred)
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body,  "html"))

        server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
        if smtp_config.get("use_tls", True):
            server.starttls()
        server.login(smtp_config["username"], password)
        server.send_message(msg)
        server.quit()

        print(f"✓ Email sent to {to_email} — Subject: {subject[:60]}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("✗ SMTP authentication failed. Check username/password.")
        return False
    except smtplib.SMTPException as e:
        print(f"✗ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error sending email: {e}")
        return False


# ============================================================================
# ALERT COMPOSERS
# ============================================================================

def send_email_alert(
    config: Dict,
    server_name: str,
    user_email: str,
    alert_type: str,
    details: Dict,
) -> bool:
    """
    Compose and send an alert email using professional HTML templates.

    Args:
        config:      Full app config
        server_name: Display name of the server
        user_email:  Recipient
        alert_type:  'DOWN' | 'WARNING' | 'UP' | 'RECOVERY'
        details:     Context dict with url, error_category, user_message, etc.

    Returns:
        True if sent successfully, False otherwise
    """
    alert_type = alert_type.upper()

    if alert_type in ("DOWN", "CRITICAL"):
        subject, html, plain = templates.compose_critical_alert(server_name, details)
    elif alert_type == "WARNING":
        subject, html, plain = templates.compose_warning_alert(server_name, details)
    elif alert_type in ("UP", "RECOVERY"):
        subject, html, plain = templates.compose_recovery_alert(server_name, details)
    else:
        # Fallback: treat as critical
        subject, html, plain = templates.compose_critical_alert(server_name, details)

    return send_email(config, user_email, subject, html, plain)


# ============================================================================
# ANTI-SPAM + ORCHESTRATION
# ============================================================================

def should_send_alert(server_id: int, alert_type: str, cooldown_minutes: int = 5) -> bool:
    """
    Anti-spam: check if an alert of this type was recently sent within the cooldown window.
    Recovery (UP/RECOVERY) alerts always pass — we only cooldown DOWN/WARNING.
    """
    if alert_type.upper() in ("UP", "RECOVERY"):
        return True
    recent = db.get_recent_alert(server_id, alert_type, cooldown_minutes)
    return recent is None


def attempt_alert(
    config: Dict,
    server_id: int,
    server_name: str,
    user_email: str,
    alert_type: str,
    details: Dict,
    cooldown_minutes: int = 5,
) -> bool:
    """
    Attempt to send an alert with anti-spam checks and DB logging.

    Args:
        config:           Full app config
        server_id:        DB server ID
        server_name:      Display name
        user_email:       Recipient email
        alert_type:       'DOWN' | 'WARNING' | 'UP' | 'RECOVERY'
        details:          Alert details dict
        cooldown_minutes: Minutes between duplicate alerts

    Returns:
        True if alert was sent, False if skipped or failed
    """
    normalized = alert_type.upper()

    if not should_send_alert(server_id, normalized, cooldown_minutes):
        print(f"  ↷ Skipped {normalized} alert for {server_name} (cooldown active)")
        return False

    if send_email_alert(config, server_name, user_email, normalized, details):
        log_type = "RECOVERY" if normalized in ("UP", "RECOVERY") else normalized
        db.log_alert(server_id, log_type, f"{server_name}: {normalized}", datetime.now())
        return True

    return False


def send_recovery_alert(
    config: Dict,
    server_id: int,
    server_name: str,
    user_email: str,
    check_result: Dict,
    downtime_duration: str,
    incident_reason: str,
) -> bool:
    """
    Convenience wrapper for sending recovery emails with full incident context.
    Called by main.py when an incident is resolved.
    """
    details = {
        "url":               check_result.get("url") or "",
        "response_time":     check_result.get("response_time"),
        "downtime_duration": downtime_duration,
        "incident_reason":   incident_reason,
    }
    return attempt_alert(
        config, server_id, server_name, user_email,
        "RECOVERY", details, cooldown_minutes=0  # Never suppress recovery alerts
    )

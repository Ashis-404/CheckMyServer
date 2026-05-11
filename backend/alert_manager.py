"""
Alert Manager module for Smart Server Monitoring System
Handles email alert sending and anti-spam logic
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv
import database as db

# Load environment variables (e.g., from .env file)
load_dotenv()


def send_email_alert(config: Dict, server_name: str, user_email: str, alert_type: str, 
                     details: Dict) -> bool:
    """
    Send an email alert
    
    Args:
        config: SMTP configuration dict with keys: host, port, use_tls, username, password_env_var, from_email
        server_name: Name of the server
        user_email: Email address of the user who owns the server
        alert_type: 'UP' or 'DOWN'
        details: Dict with URL, response_time, error, etc.
    
    Returns:
        True if email sent successfully, False otherwise
    """
    
    if not config.get("smtp"):
        print("✗ SMTP config not found in config.json")
        return False
    
    smtp_config = config["smtp"]
    
    # Validate required SMTP fields (excluding password which we check next)
    required_fields = ["host", "port", "username", "from_email"]
    for field in required_fields:
        if field not in smtp_config:
            print(f"✗ Missing SMTP config field: {field}")
            return False
    
    # Validate user email
    if not user_email:
        print("✗ User email not provided for alert")
        return False
            
    # Resolve password (either read direct 'password' field, or read from env via 'password_env_var')
    password = None
    if "password" in smtp_config:
        password = smtp_config["password"]
    elif "password_env_var" in smtp_config:
        password = os.environ.get(smtp_config["password_env_var"])
        
    if not password:
        print("✗ Missing SMTP Password. Define 'password' directly in config or set 'password_env_var' and ensure the environment variable exists.")
        return False
    
    try:
        # Compose email
        subject, body = _compose_email(server_name, alert_type, details)
        
        # Send email
        msg = MIMEMultipart()
        msg["From"] = smtp_config["from_email"]
        msg["To"] = user_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
        
        if smtp_config.get("use_tls", True):
            server.starttls()
        
        # Use the resolved password here!
        server.login(smtp_config["username"], password)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Alert email sent to {user_email} for {server_name} ({alert_type})")
        return True
    
    except smtplib.SMTPAuthenticationError:
        print(f"✗ SMTP authentication failed. Check username/password in config.json")
        return False
    
    except smtplib.SMTPException as e:
        print(f"✗ SMTP error sending alert: {e}")
        return False
    
    except Exception as e:
        print(f"✗ Error sending alert email: {e}")
        return False


def _compose_email(server_name: str, alert_type: str, details: Dict) -> tuple:
    """Compose email subject and body"""
    
    url = details.get("url", "N/A")
    response_time = details.get("response_time", "N/A")
    error = details.get("error", "N/A")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if alert_type == "DOWN":
        subject = f"⚠️ ALERT: {server_name} is DOWN"
        body = f"""
Server Monitoring Alert

Server: {server_name}
Status: ⏹️ DOWN
URL: {url}
Timestamp: {timestamp}

Error Details:
{error}

Response Time: {response_time}s

---
Smart Server Monitoring System
"""
    elif alert_type == "UP":  # UP
        subject = f"✅ RECOVERED: {server_name} is UP"
        body = f"""
Server Recovery Notification

Server: {server_name}
Status: ✅ UP
URL: {url}
Timestamp: {timestamp}

Response Time: {response_time}s

The server has recovered and is responding normally.

---
Smart Server Monitoring System
"""
    else:
    # fallback (just in case)
        subject = f"ℹ️ NOTICE: {server_name} status = {alert_type}"
        body = f"{server_name} status changed to {alert_type}"
    return subject, body


def should_send_alert(server_id: int, alert_type: str, cooldown_minutes: int = 5) -> bool:
    """
    Check if we should send an alert (anti-spam logic)
    
    Don't send duplicate alerts within cooldown period
    """
    recent_alert = db.get_recent_alert(server_id, alert_type, cooldown_minutes)
    
    if recent_alert:
        # Alert was recently sent, skip
        return False
    
    return True


def attempt_alert(config: Dict, server_id: int, server_name: str, user_email: str,
                 alert_type: str, details: Dict, cooldown_minutes: int = 5) -> bool:
    """
    Attempt to send an alert with anti-spam checks and logging
    
    Args:
        config: SMTP configuration
        server_id: Database server ID
        server_name: Name of the server
        user_email: Email address to send alert to
        alert_type: 'UP' or 'DOWN'
        details: Alert details dict
        cooldown_minutes: Minutes to wait before sending another alert
    
    Returns:
        True if alert was sent, False if skipped or failed
    """
    if alert_type == "WARNING":
         print(f"  ⚠️ Warning detected for {server_name}, no alert sent")
         return False
    # Check anti-spam
    if not should_send_alert(server_id, alert_type, cooldown_minutes):
        print(f"  ↷ Skipped {alert_type} alert for {server_name} (sent recently)")
        return False
    
    # Send alert
    if send_email_alert(config, server_name, user_email, alert_type, details):
        # Log alert
        message = f"{server_name}: {alert_type}"
        db.log_alert(server_id, alert_type, message, datetime.now())
        return True
    
    return False

"""
CheckMyServer - Main Monitoring Scheduler
Continuously monitors server health, manages incident lifecycles,
detects state changes, and dispatches intelligent alerts.
"""

import json
import time
import sys
import asyncio
import aiohttp
from datetime import datetime
import database as db
import health_checker
import alert_manager
import incident_manager
import warning_detector
import logger as logger_module
import maintenance_manager
import notification_manager
import ssl_manager


CONFIG_FILE = "config.json"


import os

def load_config(log) -> dict:
    """Load configuration from config.json, with env var fallbacks/overrides"""
    config = {
        "check_interval": max(10, int(os.environ.get("MONITOR_INTERVAL", os.environ.get("CHECK_INTERVAL", 60)))),
        "alert_cooldown_minutes": int(os.environ.get("ALERT_COOLDOWN_MINUTES", 5)),
        "api_port": int(os.environ.get("API_PORT", 5000)),
        "email_sender": os.environ.get("EMAIL_SENDER", ""),
        "email_password": os.environ.get("EMAIL_PASSWORD", ""),
        "smtp_server": os.environ.get("SMTP_SERVER", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
        "max_concurrent_checks": int(os.environ.get("MAX_CONCURRENT_CHECKS", 10))
    }
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            file_config = json.load(f)
            # File config takes precedence unless env var was explicitly set
            for k, v in file_config.items():
                if k.upper() not in os.environ:
                    config[k] = v
        log.info(f"Config loaded: {CONFIG_FILE}")
    except FileNotFoundError:
        log.info(f"Config file not found: {CONFIG_FILE}, using env vars / defaults")
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {CONFIG_FILE}: {e}")
        sys.exit(1)
        
    return config


async def publish_event_async(api_port: int, event_type: str, data: dict):
    """Notify Flask API server of an update event asynchronously"""
    url     = f"http://localhost:{api_port}/api/events/publish"
    payload = {"type": event_type, "data": data}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                pass  # Fire and forget
    except Exception:
        pass  # Ignore — API server may not be running


def compute_stable_status(history: list, default: str = "UP") -> str:
    """
    Determine stable status based on consecutive checks.
    - Recovery (UP) is instant.
    - DOWN/WARNING requires 3 consecutive identical occurrences to be stable.
    """
    if not history:
        return default

    if history[0]["status"] == "UP":
        return "UP"

    if len(history) >= 3 and all(h["status"] == "DOWN" for h in history[:3]):
        return "DOWN"

    if len(history) >= 3 and all(h["status"] == "WARNING" for h in history[:3]):
        return "WARNING"

    return "UP"


async def check_and_process_server(server: dict, config: dict, cooldown_minutes: int, log):
    """Asynchronously checks a single server and manages state transitions / alerts"""
    server_id   = server["id"]
    server_name = server["name"]
    server_url  = server["url"]
    user_email  = server.get("email")

    warning_threshold_s = config.get("warning_threshold_ms", 3000) / 1000.0
    response_timeout    = config.get("response_timeout", 10)
    api_port            = config.get("api_port", 5000)

    # ── 1. Stable status BEFORE this check ──────────────────────────────────
    prev_history = db.get_check_history(server_id, limit=3)
    previous_stable = compute_stable_status(
        prev_history, default=server.get("last_status") or "UP"
    )

    # ── 2. Perform health check ──────────────────────────────────────────────
    check_result = await health_checker.check_server_health_async(
        server_url, response_timeout, warning_threshold_s
    )

    # ── 3. Run intelligent warning detector ─────────────────────────────────
    check_result = warning_detector.analyze_performance(server_id, check_result)

    # Log enriched result
    log.info(health_checker.format_health_check_result(check_result, server_name))

    # ── 4. Log check with enriched fields ───────────────────────────────────
    db.log_check(
        server_id      = server_id,
        status         = check_result["status"],
        response_time  = check_result["response_time"],
        http_status_code = check_result["http_status_code"],
        error_message  = check_result.get("error"),
        error_category = check_result.get("error_category"),
        severity       = check_result.get("severity"),
    )

    # ── 5. Stable status AFTER this check ───────────────────────────────────
    post_history = db.get_check_history(server_id, limit=3)
    current_stable = compute_stable_status(
        post_history, default=check_result["status"]
    )

    # ── 6. Publish SSE server_update event ──────────────────────────────────
    updated_server = {
        "id":              server_id,
        "name":            server_name,
        "url":             server_url,
        "email":           user_email,
        "last_status":     check_result["status"],
        "last_check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_24h":      db.calculate_uptime_percentage(server_id, days=1) or 0.0,
        "latest_check": {
            "status":         check_result["status"],
            "response_time":  check_result["response_time"],
            "http_status_code": check_result["http_status_code"],
            "error":          check_result.get("error"),
            "error_category": check_result.get("error_category"),
            "severity":       check_result.get("severity"),
            "user_message":   check_result.get("user_message"),
        },
    }
    await publish_event_async(api_port, "server_update", updated_server)

    # ── 7. Incident lifecycle & Maintenance management ─────────────────────────
    active_maintenance = maintenance_manager.get_active_maintenance(server_id)

    if previous_stable != current_stable:
        log.info(f"  ⚡ Stable status change: {previous_stable} → {current_stable} for {server_name}")

        if active_maintenance:
            log.info(f"  🛠️ Maintenance active for {server_name} — suppressing incidents and alerts.")
            # We don't create incidents or send alerts, but we DO log a notification of state change
            notification_manager.create_notification(
                server_id, "Maintenance", 
                f"{server_name} changed to {current_stable} during maintenance."
            )
            # Publish notification event
            await publish_event_async(api_port, "notification", {"server_id": server_id})
        else:
            # Normal incident management
            check_result["url"] = server_url

            incident_event = incident_manager.handle_server_result(
                server_id              = server_id,
                server_name            = server_name,
                check_result           = check_result,
                current_stable_status  = current_stable,
                previous_stable_status = previous_stable,
            )

            if incident_event:
                # Broadcast incident event via SSE
                await publish_event_async(api_port, incident_event["event_type"], incident_event)

                # ── Send alert emails ────────────────────────────────────────────
                if not user_email:
                    log.warning(f"  ⚠️ No email for {server_name} — skipping alert")
                else:
                    if incident_event["event_type"] == "incident_created":
                        # DOWN or WARNING alert
                        alert_type = "DOWN" if current_stable == "DOWN" else "WARNING"
                        
                        notification_manager.create_notification(
                            server_id, "Critical" if alert_type == "DOWN" else "Warning",
                            f"Incident created: {server_name} is {alert_type}."
                        )
                        await publish_event_async(api_port, "notification", {"server_id": server_id})

                        alert_manager.attempt_alert(
                            config, server_id, server_name, user_email,
                            alert_type, check_result, cooldown_minutes
                        )

                    elif incident_event["event_type"] == "incident_resolved":
                        # Recovery alert with downtime info
                        downtime = incident_event.get("downtime_duration", "Unknown")
                        incident = incident_event.get("incident", {})
                        reason   = incident.get("reason", "Service was unavailable")
                        
                        notification_manager.create_notification(
                            server_id, "Recovery",
                            f"{server_name} recovered after {downtime} seconds."
                        )
                        await publish_event_async(api_port, "notification", {"server_id": server_id})

                        alert_manager.send_recovery_alert(
                            config, server_id, server_name, user_email,
                            check_result, downtime, reason
                        )

            # Handle simple state changes (non-incident but still transitions)
            elif not incident_event and previous_stable != current_stable:
                if current_stable in ("DOWN", "WARNING"):
                    alert_type = "DOWN" if current_stable == "DOWN" else "WARNING"
                    
                    notification_manager.create_notification(
                        server_id, "Critical" if alert_type == "DOWN" else "Warning",
                        f"{server_name} state changed to {alert_type}."
                    )
                    await publish_event_async(api_port, "notification", {"server_id": server_id})

                    if user_email:
                        check_result["url"] = server_url
                        alert_manager.attempt_alert(
                            config, server_id, server_name, user_email,
                            alert_type, check_result, cooldown_minutes
                        )


async def monitor_servers(config: dict, log):
    """Main monitoring loop (Asynchronous)"""
    check_interval    = config.get("check_interval", 60)
    cooldown_minutes  = config.get("alert_cooldown_minutes", 5)
    api_port          = config.get("api_port", 5000)

    log.info(f"🚀 Starting monitoring (interval: {check_interval}s, cooldown: {cooldown_minutes}m)")

    try:
        iteration       = 0
        last_purge_time = 0
        purge_interval  = 86400  # 24 hours
        last_ssl_time   = 0
        ssl_interval    = 3600   # 1 hour

        while True:
            try:
                iteration += 1
                current_time = time.time()

                # Daily cleanup of old monitoring records
                if current_time - last_purge_time > purge_interval:
                    db.purge_old_records(days=30)
                    last_purge_time = current_time

                # Update maintenance statuses (activate/complete based on schedule)
                maintenance_manager.update_maintenance_statuses()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.info(f"[Check #{iteration}] {timestamp}")

                db_servers = db.get_all_servers()

                if not db_servers:
                    log.info("  ℹ️ No servers to monitor. Add servers via the dashboard.")
                else:
                    max_concurrent = config.get("max_concurrent_checks", 10)
                    semaphore = asyncio.Semaphore(max_concurrent)
                    
                    async def bounded_check(srv):
                        async with semaphore:
                            await check_and_process_server(srv, config, cooldown_minutes, log)
                            
                    tasks = [bounded_check(server) for server in db_servers]
                    await asyncio.gather(*tasks)

                    # Hourly SSL Checks
                    if current_time - last_ssl_time > ssl_interval:
                        log.info("🔒 Running hourly SSL checks...")
                        for server in db_servers:
                            if server['url'].startswith('https'):
                                # Run synchronously but they are fast enough
                                ssl_manager.update_ssl_status(server['id'], server['url'])
                        last_ssl_time = current_time

                # Print uptime summary
                log.info("📊 Uptime Summary:")
                for server in db_servers:
                    uptime = db.calculate_uptime_percentage(server["id"], days=1)
                    if uptime is not None:
                        log.info(f"  {server['name']}: {uptime}% (24h)")

                # Publish overall system status via SSE
                if db_servers:
                    fresh      = db.get_all_servers()
                    total      = len(fresh)
                    down_cnt   = sum(1 for s in fresh if s['last_status'] == 'DOWN')
                    warn_cnt   = sum(1 for s in fresh if s['last_status'] == 'WARNING')
                    inc_summary = incident_manager.get_active_incidents_summary()

                    if total == 0:
                        overall = "Unknown"
                    elif down_cnt == total:
                        overall = "Major Outage"
                    elif down_cnt > 0:
                        overall = "Partial Outage"
                    elif warn_cnt > 0:
                        overall = "Degraded Performance"
                    else:
                        overall = "All Systems Operational"

                    await publish_event_async(api_port, "status_update", {
                            "status":          overall,
                            "total_servers":   total,
                            "down_servers":    down_cnt,
                            "warning_servers": warn_cnt,
                            "active_incidents": inc_summary["total_active"],
                        })

                    log.info(f"⏳ Next check in {check_interval}s...")
            except Exception as e:
                log.error(f"Error during monitoring cycle: {e}", exc_info=True)
            finally:
                await asyncio.sleep(check_interval)

    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        log.info("🛑 Monitoring stopped by user")


def main():
    """Main entry point"""
    log = logger_module.setup_logger()
    log.info("System started: CheckMyServer Monitoring Engine")

    config = load_config(log)
    db.init_db()

    try:
        asyncio.run(monitor_servers(config, log))
    except KeyboardInterrupt:
        log.info("🛑 Monitoring stopped by user")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        log.info("System stopped")


if __name__ == "__main__":
    main()

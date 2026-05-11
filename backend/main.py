"""
Smart Server Monitoring System - Main Scheduler
Continuously monitors server health, logs checks, detects state changes, and sends alerts
"""

import json
import time
import sys
from datetime import datetime
import database as db
import health_checker
import alert_manager
import uptime_calculator
import logger as logger_module


CONFIG_FILE = "config.json"


def load_config() -> dict:
    """Load configuration from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        print(f"✓ Config loaded: {CONFIG_FILE}")
        return config
    except FileNotFoundError:
        print(f"✗ Config file not found: {CONFIG_FILE}")
        print(f"  Please copy {CONFIG_FILE}.example to {CONFIG_FILE} and configure it")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in {CONFIG_FILE}: {e}")
        sys.exit(1)


def monitor_servers(config: dict, log):
    """Main monitoring loop"""
    
    check_interval = config.get("check_interval", 60)
    cooldown_minutes = config.get("alert_cooldown_minutes", 5)
    
    print(f"\n🚀 Starting monitoring (interval: {check_interval}s, alert cooldown: {cooldown_minutes}m)")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")
    
    try:
        iteration = 0
        last_purge_time = 0
        purge_interval = 86400  # 24 hours
        
        while True:
            iteration += 1
            current_time = time.time()
            if current_time - last_purge_time > purge_interval:
                db.purge_old_records(days=30)
                last_purge_time = current_time

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[Check #{iteration}] {timestamp}")
            print("-" * 60)
            
            # Fetch latest servers from database
            db_servers = db.get_all_servers()
            
            for server in db_servers:
                server_id = server["id"]
                server_name = server["name"]
                server_url = server["url"]
                
                # Check server health
                check_result = health_checker.check_server_health(
                    server_url,
                    config.get("response_timeout", 2)
                )
                
                # Print result
                print(health_checker.format_health_check_result(check_result, server_name))
                
                # Get previous status BEFORE logging the new check
                previous_status = server.get("last_status")
                current_status = check_result["status"]
                
                # Log check to database
                db.log_check(
                    server_id=server_id,
                    status=current_status,
                    response_time=check_result["response_time"],
                    http_status_code=check_result["http_status_code"],
                    error_message=check_result["error"]
                )
                
                # Detect status transition
                if previous_status != current_status:
                    print(f"  ⚡ Status change: {previous_status or 'UNKNOWN'} → {current_status}")
                    
                    # Prepare alert details
                    alert_details = {
                        "url": server_url,
                        "response_time": check_result["response_time"],
                        "error": check_result["error"]
                    }
                    
                    # Get user email from server record
                    user_email = server.get("email")
                    if not user_email:
                         print(f"  ⚠️ No email configured for server {server_name}. Skipping alert.")
                    else:
                        # Send alert
                        alert_manager.attempt_alert(
                            config,
                            server_id,
                            server_name,
                            user_email,
                            current_status,
                            alert_details,
                            cooldown_minutes
                        )
            
            # Print uptime stats
            print("\n📊 Uptime Summary:")
            for server in db_servers:
                uptime = db.calculate_uptime_percentage(server["id"], days=1)
                if uptime is not None:
                    print(f"  {server['name']}: {uptime}% (24h)")
            
            print(f"\n⏳ Next check in {check_interval} seconds...", end="", flush=True)
            
            # Sleep before next iteration
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("🛑 Monitoring stopped by user")
        print("=" * 60)


def main():
    """Main entry point"""
    
    print("\n" + "=" * 60)
    print("🔍 Smart Server Monitoring System")
    print("=" * 60)
    
    # Setup logging
    log = logger_module.setup_logger()
    log.info("System started")
    
    # Load configuration
    config = load_config()
    
    # Initialize database
    db.init_db()
    
    # Start monitoring loop
    try:
        monitor_servers(config, log)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        log.info("System stopped")


if __name__ == "__main__":
    main()

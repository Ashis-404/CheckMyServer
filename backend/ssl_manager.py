"""
SSL Manager
Handles checking SSL certificates, updating DB, and generating notifications.
"""
import sqlite3
from typing import Dict, Optional, List
from datetime import datetime
import database as db
import ssl_checker
import notification_manager

def update_ssl_status(server_id: int, url: str) -> Optional[Dict]:
    """Check SSL for a server and update the DB."""
    result = ssl_checker.check_ssl(url)
    
    conn = db.get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        status = result.get('status', 'Error')
        days_remaining = result.get('days_remaining')
        expiry_date = result.get('expiry_date')
        issuer = result.get('issuer')
        
        # Upsert logic for SQLite
        cursor.execute(
            """INSERT INTO ssl_monitoring (server_id, status, days_remaining, expiry_date, issuer, last_checked)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(server_id) DO UPDATE SET
                 status=excluded.status,
                 days_remaining=excluded.days_remaining,
                 expiry_date=excluded.expiry_date,
                 issuer=excluded.issuer,
                 last_checked=excluded.last_checked
            """,
            (server_id, status, days_remaining, expiry_date, issuer, now)
        )
        conn.commit()
        
        # Check if we need to generate a notification
        if status in ['Critical', 'Expired']:
            msg = f"SSL Certificate for {url} is {status}."
            if days_remaining is not None:
                msg += f" ({days_remaining} days remaining)"
            notification_manager.create_notification(server_id, "SSL", msg)
            
        return result
    except sqlite3.Error as e:
        print(f"✗ DB error updating SSL: {e}")
        return None
    finally:
        conn.close()

def get_ssl_status(server_id: int) -> Optional[Dict]:
    """Get the latest SSL status from DB for a server."""
    conn = db.get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ssl_monitoring WHERE server_id = ?", (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"✗ DB error fetching SSL: {e}")
        return None
    finally:
        conn.close()

def get_all_ssl_statuses() -> Dict[int, Dict]:
    """Get SSL statuses for all servers. Returns a dict mapping server_id to status dict."""
    conn = db.get_connection()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ssl_monitoring")
        return {row['server_id']: dict(row) for row in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"✗ DB error fetching all SSL: {e}")
        return {}
    finally:
        conn.close()

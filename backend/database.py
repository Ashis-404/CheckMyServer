"""
Database module for Smart Server Monitoring System
Handles SQLite operations for logging checks, alerts, and server state
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Tuple, List, Dict


DB_FILE = "server_monitor.db"


def init_db():
    """Initialize database schema if not exists"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create servers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_check_time TIMESTAMP,
            last_status TEXT CHECK(last_status IS NULL OR last_status IN ('UP', 'DOWN', 'WARNING'))
        )
    """)
    
    # Migrate existing database: add email column if it doesn't exist
    cursor.execute("PRAGMA table_info(servers)")
    columns = [col[1] for col in cursor.fetchall()]
    if "email" not in columns:
        cursor.execute("ALTER TABLE servers ADD COLUMN email TEXT DEFAULT ''")
        print("✓ Migrated: Added email column to servers table")
    
    # Create monitoring_checks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL CHECK(status IN ('UP', 'DOWN', 'WARNING')),
            response_time REAL,
            http_status_code INTEGER,
            error_message TEXT,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)
    
    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alert_type TEXT NOT NULL CHECK(alert_type IN ('UP', 'DOWN', 'WARNING')),
            message TEXT,
            sent_at TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized: {DB_FILE}")


def get_connection():
    """Get a SQLite connection"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except sqlite3.Error as e:
        print(f"✗ Database connection error: {e}")
        return None


def add_server(name: str, url: str, email: str) -> Optional[int]:
    """Add a new server to monitor"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO servers (name, url, email) VALUES (?, ?, ?)",
            (name, url, email)
        )
        conn.commit()
        server_id = cursor.lastrowid
        print(f"✓ Server added: {name} (ID: {server_id}) - Email: {email}")
        return server_id
    except sqlite3.IntegrityError as e:
        print(f"✗ Server already exists: {name}")
        return None
    except sqlite3.Error as e:
        print(f"✗ Database error adding server: {e}")
        return None
    finally:
        conn.close()


def delete_server(server_id: int) -> bool:
    """Delete a server and all its associated records"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Delete related monitoring_checks
        cursor.execute("DELETE FROM monitoring_checks WHERE server_id = ?", (server_id,))
        # Delete related alerts
        cursor.execute("DELETE FROM alerts WHERE server_id = ?", (server_id,))
        # Delete server
        cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        
        conn.commit()
        print(f"✓ Server deleted: ID {server_id}")
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error deleting server: {e}")
        return False
    finally:
        conn.close()


def get_server_by_id(server_id: int) -> Optional[Dict]:
    """Get a specific server by ID"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching server: {e}")
        return None
    finally:
        conn.close()


def get_all_servers() -> List[Dict]:
    """Get all servers from database"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers")
        servers = [dict(row) for row in cursor.fetchall()]
        return servers
    except sqlite3.Error as e:
        print(f"✗ Database error fetching servers: {e}")
        return []
    finally:
        conn.close()


def log_check(server_id: int, status: str, response_time: float, 
              http_status_code: Optional[int] = None, error_message: Optional[str] = None):
    """Log a health check result"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO monitoring_checks 
               (server_id, status, response_time, http_status_code, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (server_id, status, response_time, http_status_code, error_message)
        )
        
        # Update last_check_time and last_status in servers table
        cursor.execute(
            """UPDATE servers 
               SET last_check_time = CURRENT_TIMESTAMP, last_status = ?
               WHERE id = ?""",
            (status, server_id)
        )
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error logging check: {e}")
        return False
    finally:
        conn.close()


def get_last_status(server_id: int) -> Optional[str]:
    """Get the last known status of a server"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT last_status FROM servers WHERE id = ?", (server_id,))
        row = cursor.fetchone()
        if row:
            return row['last_status']
        return None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching last status: {e}")
        return None
    finally:
        conn.close()


def update_last_status(server_id: int, status: str):
    """Update last known status of a server"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE servers SET last_status = ? WHERE id = ?",
            (status, server_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error updating status: {e}")
        return False
    finally:
        conn.close()


def log_alert(server_id: int, alert_type: str, message: str, sent_at: Optional[datetime] = None):
    """Log an alert that was sent"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        sent_at_str = sent_at.isoformat() if sent_at else None
        cursor.execute(
            """INSERT INTO alerts (server_id, alert_type, message, sent_at)
               VALUES (?, ?, ?, ?)""",
            (server_id, alert_type, message, sent_at_str)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error logging alert: {e}")
        return False
    finally:
        conn.close()


def get_recent_alert(server_id: int, alert_type: str, minutes: int = 5) -> Optional[Dict]:
    """Check if an alert was recently sent for this server/type within X minutes"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM alerts 
               WHERE server_id = ? AND alert_type = ?
               AND sent_at > datetime('now', '-' || ? || ' minutes')
               ORDER BY sent_at DESC
               LIMIT 1""",
            (server_id, alert_type, minutes)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching recent alert: {e}")
        return None
    finally:
        conn.close()


def calculate_uptime_percentage(server_id: int, days: int = 1) -> Optional[float]:
    """Calculate uptime percentage for a server over N days"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*) as total, 
                      SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) as up_count
               FROM monitoring_checks
               WHERE server_id = ? 
               AND timestamp > datetime('now', '-' || ? || ' days')""",
            (server_id, days)
        )
        row = cursor.fetchone()
        
        if row and row['total'] > 0:
            uptime_pct = (row['up_count'] / row['total']) * 100
            return round(uptime_pct, 2)
        return None
    except sqlite3.Error as e:
        print(f"✗ Database error calculating uptime: {e}")
        return None
    finally:
        conn.close()


def get_check_history(server_id: int, limit: int = 10) -> List[Dict]:
    """Get recent check history for a server"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM monitoring_checks
               WHERE server_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (server_id, limit)
        )
        checks = [dict(row) for row in cursor.fetchall()]
        return checks
    except sqlite3.Error as e:
        print(f"✗ Database error fetching history: {e}")
        return []
    finally:
        conn.close()


def purge_old_records(days: int = 30) -> int:
    """Delete monitoring checks older than `days` to save space"""
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM monitoring_checks WHERE timestamp <= datetime('now', '-' || ? || ' days')",
            (days,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            print(f"✓ Purged {deleted_count} old records")
        return deleted_count
    except sqlite3.Error as e:
        print(f"✗ Database error purging records: {e}")
        return 0
    finally:
        conn.close()

"""
Maintenance Manager
Handles scheduling, tracking, and evaluating maintenance windows.
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import database as db

def get_active_maintenance(server_id: int) -> Optional[Dict]:
    """Check if a specific server is currently under active maintenance."""
    conn = db.get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Check for active maintenance where the server_id is included in target_server_ids
        # target_server_ids is a comma-separated string like "1,2,3" or "all"
        cursor.execute(
            """SELECT * FROM maintenance_windows
               WHERE status = 'Active' 
               AND start_time <= ? AND end_time >= ?""",
            (now, now)
        )
        windows = cursor.fetchall()
        for w in windows:
            targets = w['target_server_ids'].split(',')
            if 'all' in targets or str(server_id) in targets:
                return dict(w)
        return None
    except sqlite3.Error as e:
        print(f"✗ DB error checking active maintenance: {e}")
        return None
    finally:
        conn.close()

def schedule_maintenance(title: str, description: str, target_server_ids: str, start_time: str, end_time: str) -> Optional[int]:
    """Schedule a new maintenance window."""
    conn = db.get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO maintenance_windows (title, description, target_server_ids, start_time, end_time, status)
               VALUES (?, ?, ?, ?, ?, 'Scheduled')""",
            (title, description, target_server_ids, start_time, end_time)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"✗ DB error scheduling maintenance: {e}")
        return None
    finally:
        conn.close()

def get_all_maintenance() -> List[Dict]:
    """Get all maintenance windows."""
    conn = db.get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM maintenance_windows ORDER BY start_time DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"✗ DB error fetching maintenance windows: {e}")
        return []
    finally:
        conn.close()

def update_maintenance_statuses() -> None:
    """Evaluate scheduled windows and update their statuses to Active or Completed based on current time."""
    conn = db.get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Move to Active
        cursor.execute(
            """UPDATE maintenance_windows 
               SET status = 'Active' 
               WHERE status = 'Scheduled' AND start_time <= ? AND end_time > ?""",
            (now, now)
        )
        
        # Move to Completed
        cursor.execute(
            """UPDATE maintenance_windows 
               SET status = 'Completed' 
               WHERE status IN ('Scheduled', 'Active') AND end_time <= ?""",
            (now,)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"✗ DB error updating maintenance statuses: {e}")
    finally:
        conn.close()

def delete_maintenance(m_id: int) -> bool:
    conn = db.get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM maintenance_windows WHERE id = ?", (m_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        return False
    finally:
        conn.close()

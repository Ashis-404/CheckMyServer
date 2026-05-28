"""
Notification Manager
Handles creating and fetching centralized notifications.
"""
import sqlite3
from typing import List, Dict, Optional
import database as db

def create_notification(server_id: Optional[int], severity: str, message: str) -> Optional[int]:
    """Create a new notification."""
    conn = db.get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO notifications (server_id, severity, message)
               VALUES (?, ?, ?)""",
            (server_id, severity, message)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"✗ DB error creating notification: {e}")
        return None
    finally:
        conn.close()

def get_notifications(limit: int = 50) -> List[Dict]:
    """Get recent notifications."""
    conn = db.get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT n.*, s.name as server_name 
               FROM notifications n
               LEFT JOIN servers s ON n.server_id = s.id
               ORDER BY n.created_at DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"✗ DB error fetching notifications: {e}")
        return []
    finally:
        conn.close()

def mark_as_read(notif_id: int) -> bool:
    """Mark a notification as read."""
    conn = db.get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        return False
    finally:
        conn.close()

def get_unread_count() -> int:
    """Get count of unread notifications."""
    conn = db.get_connection()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM notifications WHERE is_read = 0")
        row = cursor.fetchone()
        return row['cnt'] if row else 0
    except sqlite3.Error as e:
        return 0
    finally:
        conn.close()

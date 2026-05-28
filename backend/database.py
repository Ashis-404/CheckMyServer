"""
Database module for CheckMyServer
Handles SQLite operations for logging checks, alerts, incidents, server state,
and performance test results.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Tuple, List, Dict


import os

DB_FILE = os.environ.get("DB_PATH", "server_monitor.db")


def init_db():
    """Initialize database schema and run migrations if needed"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ── servers table ────────────────────────────────────────────────────────
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

    # ── monitoring_checks table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL CHECK(status IN ('UP', 'DOWN', 'WARNING')),
            response_time REAL,
            http_status_code INTEGER,
            error_message TEXT,
            error_category TEXT,
            severity TEXT,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)

    # ── alerts table ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alert_type TEXT NOT NULL CHECK(alert_type IN ('UP', 'DOWN', 'WARNING', 'RECOVERY')),
            message TEXT,
            sent_at TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)

    # ── incidents table ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            duration_seconds INTEGER,
            reason TEXT,
            error_category TEXT,
            severity TEXT DEFAULT 'critical',
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'resolved')),
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)

    # ── performance_tests table ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            url TEXT NOT NULL,
            vus INTEGER NOT NULL DEFAULT 10,
            duration_seconds INTEGER NOT NULL DEFAULT 30,
            method TEXT NOT NULL DEFAULT 'GET',
            headers TEXT,
            body TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'running', 'completed', 'failed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT
        )
    """)

    # ── performance_metrics table ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            avg_latency_ms REAL,
            p95_latency_ms REAL,
            max_latency_ms REAL,
            min_latency_ms REAL,
            success_rate REAL,
            failure_rate REAL,
            requests_per_sec REAL,
            total_requests INTEGER,
            total_failed INTEGER,
            degradation_pct REAL,
            warning_level TEXT DEFAULT 'none'
                CHECK(warning_level IN ('none', 'warning', 'critical', 'degraded')),
            FOREIGN KEY (test_id) REFERENCES performance_tests (id)
        )
    """)

    # ── maintenance_windows table ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            target_server_ids TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled'
                CHECK(status IN ('Scheduled', 'Active', 'Completed'))
        )
    """)

    # ── notifications table ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            severity TEXT NOT NULL CHECK(severity IN ('Info', 'Warning', 'Critical', 'Recovery', 'Maintenance', 'SSL')),
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)

    # ── ssl_monitoring table ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ssl_monitoring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER UNIQUE,
            status TEXT NOT NULL,
            days_remaining INTEGER,
            expiry_date TIMESTAMP,
            issuer TEXT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    """)

    conn.commit()

    # ── Migrations: add new columns to existing tables ───────────────────────
    _migrate(conn, cursor)

    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_FILE}")


def _migrate(conn, cursor):
    """Add new columns to existing tables without losing data"""
    # monitoring_checks: add error_category and severity columns
    cursor.execute("PRAGMA table_info(monitoring_checks)")
    mc_cols = [col[1] for col in cursor.fetchall()]
    if "error_category" not in mc_cols:
        cursor.execute("ALTER TABLE monitoring_checks ADD COLUMN error_category TEXT")
        print("Migrated: Added error_category to monitoring_checks")
    if "severity" not in mc_cols:
        cursor.execute("ALTER TABLE monitoring_checks ADD COLUMN severity TEXT")
        print("Migrated: Added severity to monitoring_checks")

    # servers: add email, consecutive_failures, public_slug, and is_public columns
    cursor.execute("PRAGMA table_info(servers)")
    srv_cols = [col[1] for col in cursor.fetchall()]
    if "email" not in srv_cols:
        cursor.execute("ALTER TABLE servers ADD COLUMN email TEXT DEFAULT ''")
        print("Migrated: Added email to servers")
    if "consecutive_failures" not in srv_cols:
        cursor.execute("ALTER TABLE servers ADD COLUMN consecutive_failures INTEGER DEFAULT 0")
        print("Migrated: Added consecutive_failures to servers")
    if "public_slug" not in srv_cols:
        cursor.execute("ALTER TABLE servers ADD COLUMN public_slug TEXT")
        print("Migrated: Added public_slug to servers")
    if "is_public" not in srv_cols:
        cursor.execute("ALTER TABLE servers ADD COLUMN is_public INTEGER DEFAULT 0")
        print("Migrated: Added is_public to servers")

    # maintenance_windows: ensure table exists
    cursor.execute("PRAGMA table_info(maintenance_windows)")
    mw_cols = [col[1] for col in cursor.fetchall()]
    if not mw_cols:
        print("Migrated: maintenance_windows table created")

    # notifications: ensure table exists
    cursor.execute("PRAGMA table_info(notifications)")
    notif_cols = [col[1] for col in cursor.fetchall()]
    if not notif_cols:
        print("Migrated: notifications table created")

    # ssl_monitoring: ensure table exists
    cursor.execute("PRAGMA table_info(ssl_monitoring)")
    ssl_cols = [col[1] for col in cursor.fetchall()]
    if not ssl_cols:
        print("Migrated: ssl_monitoring table created")

    # ssl_monitoring: ensure table exists
    cursor.execute("PRAGMA table_info(ssl_monitoring)")
    ssl_cols = [col[1] for col in cursor.fetchall()]
    if not ssl_cols:
        print("Migrated: ssl_monitoring table created")

    # performance_tests: ensure table exists (already created above for new DBs)
    cursor.execute("PRAGMA table_info(performance_tests)")
    pt_cols = [col[1] for col in cursor.fetchall()]
    if not pt_cols:
        print("Migrated: performance_tests table created")

    # performance_metrics: ensure table exists
    cursor.execute("PRAGMA table_info(performance_metrics)")
    pm_cols = [col[1] for col in cursor.fetchall()]
    if not pm_cols:
        print("Migrated: performance_metrics table created")

    # alerts: add RECOVERY to allowed types (SQLite CHECK constraints can't be altered;
    # we just make sure the table allows it via the CREATE TABLE above for new DBs.
    # For existing DBs we drop and recreate if the old constraint is present.)
    # We'll handle this gracefully by catching integrity errors when logging RECOVERY alerts.


# ============================================================================
# CONNECTION HELPER
# ============================================================================

def get_connection():
    """Get a SQLite connection with row_factory set"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"✗ Database connection error: {e}")
        return None


# ============================================================================
# SERVER CRUD
# ============================================================================

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
        print(f"✓ Server added: {name} (ID: {server_id})")
        return server_id
    except sqlite3.IntegrityError:
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
        cursor.execute("DELETE FROM monitoring_checks WHERE server_id = ?", (server_id,))
        cursor.execute("DELETE FROM alerts WHERE server_id = ?", (server_id,))
        cursor.execute("DELETE FROM incidents WHERE server_id = ?", (server_id,))
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
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"✗ Database error fetching servers: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# CHECK LOGGING
# ============================================================================

def log_check(server_id: int, status: str, response_time: float,
              http_status_code: Optional[int] = None,
              error_message: Optional[str] = None,
              error_category: Optional[str] = None,
              severity: Optional[str] = None) -> bool:
    """Log a health check result"""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO monitoring_checks
               (server_id, status, response_time, http_status_code,
                error_message, error_category, severity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (server_id, status, response_time, http_status_code,
             error_message, error_category, severity)
        )
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
        return row['last_status'] if row else None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching last status: {e}")
        return None
    finally:
        conn.close()


def update_last_status(server_id: int, status: str) -> bool:
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
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"✗ Database error fetching history: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# ALERTS
# ============================================================================

def log_alert(server_id: int, alert_type: str, message: str,
              sent_at: Optional[datetime] = None) -> bool:
    """Log an alert that was sent"""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sent_at_str = sent_at.isoformat() if sent_at else None
        # Use INSERT OR IGNORE to gracefully handle old DBs with strict CHECK constraints
        try:
            cursor.execute(
                """INSERT INTO alerts (server_id, alert_type, message, sent_at)
                   VALUES (?, ?, ?, ?)""",
                (server_id, alert_type, message, sent_at_str)
            )
        except sqlite3.IntegrityError:
            # Old DB with strict CHECK constraint not including RECOVERY — map to UP
            fallback = "UP" if alert_type == "RECOVERY" else alert_type
            cursor.execute(
                """INSERT INTO alerts (server_id, alert_type, message, sent_at)
                   VALUES (?, ?, ?, ?)""",
                (server_id, fallback, message, sent_at_str)
            )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"✗ Database error logging alert: {e}")
        return False
    finally:
        conn.close()


def get_recent_alert(server_id: int, alert_type: str, minutes: int = 5) -> Optional[Dict]:
    """Check if an alert was recently sent within X minutes"""
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


# ============================================================================
# UPTIME
# ============================================================================

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
            return round((row['up_count'] / row['total']) * 100, 2)
        return None
    except sqlite3.Error as e:
        print(f"✗ Database error calculating uptime: {e}")
        return None
    finally:
        conn.close()


# ============================================================================
# ANALYTICS
# ============================================================================

def get_server_analytics(server_id: int, days: int = 7) -> Dict:
    """
    Return aggregated performance analytics for a server.
    Includes latency stats, uptime periods, and failure/warning counts.
    """
    conn = get_connection()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()

        # Aggregate metrics over the requested period
        cursor.execute(
            """SELECT
                 COUNT(*) as total_checks,
                 AVG(CASE WHEN response_time IS NOT NULL THEN response_time END) as avg_latency,
                 MAX(response_time) as max_latency,
                 MIN(CASE WHEN response_time > 0 THEN response_time END) as min_latency,
                 SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) as up_count,
                 SUM(CASE WHEN status = 'DOWN' THEN 1 ELSE 0 END) as down_count,
                 SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) as warning_count
               FROM monitoring_checks
               WHERE server_id = ?
               AND timestamp > datetime('now', '-' || ? || ' days')""",
            (server_id, days)
        )
        row = cursor.fetchone()

        total = row['total_checks'] or 0
        up    = row['up_count'] or 0

        analytics = {
            "total_checks":  total,
            "avg_latency":   round(row['avg_latency'], 3) if row['avg_latency'] else None,
            "max_latency":   round(row['max_latency'], 3) if row['max_latency'] else None,
            "min_latency":   round(row['min_latency'], 3) if row['min_latency'] else None,
            "up_count":      up,
            "down_count":    row['down_count'] or 0,
            "warning_count": row['warning_count'] or 0,
            "uptime_pct":    round((up / total) * 100, 2) if total > 0 else None,
        }

        # Uptime over 24h, 7d, 30d
        analytics["uptime_24h"]  = calculate_uptime_percentage(server_id, days=1)
        analytics["uptime_7d"]   = calculate_uptime_percentage(server_id, days=7)
        analytics["uptime_30d"]  = calculate_uptime_percentage(server_id, days=30)

        # Hourly latency trend (last 24h, 24 buckets)
        cursor.execute(
            """SELECT
                 strftime('%Y-%m-%dT%H:00:00', timestamp) as hour,
                 AVG(response_time) as avg_rt,
                 COUNT(*) as checks,
                 SUM(CASE WHEN status='DOWN' THEN 1 ELSE 0 END) as failures
               FROM monitoring_checks
               WHERE server_id = ?
               AND timestamp > datetime('now', '-1 day')
               GROUP BY hour
               ORDER BY hour ASC""",
            (server_id,)
        )
        trend_rows = cursor.fetchall()
        analytics["latency_trend"] = [
            {
                "hour":     r["hour"],
                "avg_rt":   round(r["avg_rt"], 3) if r["avg_rt"] else None,
                "checks":   r["checks"],
                "failures": r["failures"],
            }
            for r in trend_rows
        ]

        return analytics
    except sqlite3.Error as e:
        print(f"✗ Database error fetching analytics: {e}")
        return {}
    finally:
        conn.close()


def get_latency_baseline(server_id: int, sample_size: int = 20) -> Optional[float]:
    """
    Get the rolling average latency over the last N successful checks.
    Used by warning_detector for spike detection.
    """
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT AVG(response_time) as baseline
               FROM (
                 SELECT response_time FROM monitoring_checks
                 WHERE server_id = ? AND status = 'UP' AND response_time IS NOT NULL
                 ORDER BY timestamp DESC
                 LIMIT ?
               )""",
            (server_id, sample_size)
        )
        row = cursor.fetchone()
        return round(row['baseline'], 3) if row and row['baseline'] else None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching baseline: {e}")
        return None
    finally:
        conn.close()


# ============================================================================
# INCIDENTS
# ============================================================================

def create_incident(server_id: int, reason: str,
                    error_category: Optional[str] = None,
                    severity: str = "critical") -> Optional[int]:
    """Create a new active incident for a server"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO incidents (server_id, reason, error_category, severity, status)
               VALUES (?, ?, ?, ?, 'active')""",
            (server_id, reason, error_category, severity)
        )
        conn.commit()
        incident_id = cursor.lastrowid
        print(f"🚨 Incident #{incident_id} created for server {server_id}: {reason}")
        return incident_id
    except sqlite3.Error as e:
        print(f"✗ Database error creating incident: {e}")
        return None
    finally:
        conn.close()


def resolve_incident(incident_id: int) -> Optional[Dict]:
    """
    Mark an incident as resolved and calculate duration.
    Returns the resolved incident dict.
    """
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        resolved_at = datetime.utcnow()

        # Fetch start time to compute duration
        cursor.execute("SELECT started_at FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        if not row:
            return None

        started_at = datetime.fromisoformat(row['started_at'])
        duration_s = int((resolved_at - started_at).total_seconds())

        cursor.execute(
            """UPDATE incidents
               SET status = 'resolved',
                   resolved_at = ?,
                   duration_seconds = ?
               WHERE id = ?""",
            (resolved_at.isoformat(), duration_s, incident_id)
        )
        conn.commit()

        # Return the updated incident
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        resolved = dict(row) if row else None
        if resolved:
            print(f"✅ Incident #{incident_id} resolved. Duration: {duration_s}s")
        return resolved
    except sqlite3.Error as e:
        print(f"✗ Database error resolving incident: {e}")
        return None
    finally:
        conn.close()


def get_active_incident(server_id: int) -> Optional[Dict]:
    """Get the current active incident for a server, if any"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM incidents
               WHERE server_id = ? AND status = 'active'
               ORDER BY started_at DESC
               LIMIT 1""",
            (server_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"✗ Database error fetching active incident: {e}")
        return None
    finally:
        conn.close()


def get_incidents(server_id: Optional[int] = None,
                  status: Optional[str] = None,
                  limit: int = 50) -> List[Dict]:
    """
    Get incidents with optional filters.
    Joins server name for display convenience.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        query = """
            SELECT i.*, s.name as server_name, s.url as server_url
            FROM incidents i
            JOIN servers s ON i.server_id = s.id
            WHERE 1=1
        """
        params = []
        if server_id is not None:
            query += " AND i.server_id = ?"
            params.append(server_id)
        if status:
            query += " AND i.status = ?"
            params.append(status)
        query += " ORDER BY i.started_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"✗ Database error fetching incidents: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# MAINTENANCE
# ============================================================================

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
            print(f"Purged {deleted_count} old monitoring records")
        return deleted_count
    except sqlite3.Error as e:
        print(f"Database error purging records: {e}")
        return 0
    finally:
        conn.close()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def create_perf_test(url: str, vus: int, duration_seconds: int,
                     method: str = 'GET',
                     headers: Optional[str] = None,
                     body: Optional[str] = None,
                     server_id: Optional[int] = None) -> Optional[int]:
    """Create a new performance test record with status 'pending'"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO performance_tests
               (server_id, url, vus, duration_seconds, method, headers, body, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (server_id, url, vus, duration_seconds, method, headers, body)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error creating perf test: {e}")
        return None
    finally:
        conn.close()


def update_perf_test_status(test_id: int, status: str,
                             started_at: Optional[str] = None,
                             completed_at: Optional[str] = None,
                             error_message: Optional[str] = None) -> bool:
    """Update the status of a performance test"""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        fields = ["status = ?"]
        params: list = [status]
        if started_at:
            fields.append("started_at = ?")
            params.append(started_at)
        if completed_at:
            fields.append("completed_at = ?")
            params.append(completed_at)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        params.append(test_id)
        cursor.execute(
            f"UPDATE performance_tests SET {', '.join(fields)} WHERE id = ?",
            params
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error updating perf test status: {e}")
        return False
    finally:
        conn.close()


def save_perf_metrics(test_id: int, metrics: Dict) -> Optional[int]:
    """Save parsed k6 metrics for a completed test"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO performance_metrics
               (test_id, avg_latency_ms, p95_latency_ms, max_latency_ms, min_latency_ms,
                success_rate, failure_rate, requests_per_sec, total_requests,
                total_failed, degradation_pct, warning_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                test_id,
                metrics.get('avg_latency_ms'),
                metrics.get('p95_latency_ms'),
                metrics.get('max_latency_ms'),
                metrics.get('min_latency_ms'),
                metrics.get('success_rate'),
                metrics.get('failure_rate'),
                metrics.get('requests_per_sec'),
                metrics.get('total_requests'),
                metrics.get('total_failed'),
                metrics.get('degradation_pct'),
                metrics.get('warning_level', 'none'),
            )
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error saving perf metrics: {e}")
        return None
    finally:
        conn.close()


def get_perf_test(test_id: int) -> Optional[Dict]:
    """Get a performance test by ID, including its metrics"""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM performance_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        # Attach metrics
        cursor.execute(
            "SELECT * FROM performance_metrics WHERE test_id = ? ORDER BY id DESC LIMIT 1",
            (test_id,)
        )
        m = cursor.fetchone()
        result['metrics'] = dict(m) if m else None
        return result
    except sqlite3.Error as e:
        print(f"DB error fetching perf test: {e}")
        return None
    finally:
        conn.close()


def get_perf_tests(server_id: Optional[int] = None,
                   limit: int = 20) -> List[Dict]:
    """Get recent performance tests, optionally filtered by server_id"""
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        query = """
            SELECT pt.*, pm.avg_latency_ms, pm.p95_latency_ms, pm.max_latency_ms,
                   pm.success_rate, pm.failure_rate, pm.requests_per_sec,
                   pm.total_requests, pm.degradation_pct, pm.warning_level
            FROM performance_tests pt
            LEFT JOIN performance_metrics pm ON pm.test_id = pt.id
            WHERE 1=1
        """
        params: list = []
        if server_id is not None:
            query += " AND pt.server_id = ?"
            params.append(server_id)
        query += " ORDER BY pt.created_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"DB error fetching perf tests: {e}")
        return []
    finally:
        conn.close()


def get_recent_benchmarks_for_url(url: str, limit: int = 5) -> List[Dict]:
    """
    Get recent completed performance metrics for a specific URL.
    Used for degradation comparison.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT pm.*, pt.created_at as test_created_at
               FROM performance_metrics pm
               JOIN performance_tests pt ON pm.test_id = pt.id
               WHERE pt.url = ? AND pt.status = 'completed'
               ORDER BY pt.created_at DESC
               LIMIT ?""",
            (url, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"DB error fetching benchmarks: {e}")
        return []
    finally:
        conn.close()


def delete_perf_test(test_id: int) -> bool:
    """Delete a performance test and its metrics"""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM performance_metrics WHERE test_id = ?", (test_id,))
        cursor.execute("DELETE FROM performance_tests WHERE id = ?", (test_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"DB error deleting perf test: {e}")
        return False
    finally:
        conn.close()

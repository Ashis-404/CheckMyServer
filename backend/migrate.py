"""
One-time migration script for CheckMyServer database upgrade.
Run from the backend/ directory: python migrate.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os

DB_FILE = "server_monitor.db"

def run_migration():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("Running database migration...")

    # 1. Create incidents table
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
    print("  [OK] incidents table ensured")

    # 2. Add error_category to monitoring_checks
    cursor.execute("PRAGMA table_info(monitoring_checks)")
    mc_cols = [r[1] for r in cursor.fetchall()]

    if "error_category" not in mc_cols:
        cursor.execute("ALTER TABLE monitoring_checks ADD COLUMN error_category TEXT")
        print("  [OK] Added error_category to monitoring_checks")
    else:
        print("  [--] error_category already exists")

    if "severity" not in mc_cols:
        cursor.execute("ALTER TABLE monitoring_checks ADD COLUMN severity TEXT")
        print("  [OK] Added severity to monitoring_checks")
    else:
        print("  [--] severity already exists")

    # 3. Add email to servers (legacy safety)
    cursor.execute("PRAGMA table_info(servers)")
    srv_cols = [r[1] for r in cursor.fetchall()]
    if "email" not in srv_cols:
        cursor.execute("ALTER TABLE servers ADD COLUMN email TEXT DEFAULT ''")
        print("  [OK] Added email to servers")
    else:
        print("  [--] email already exists in servers")

    conn.commit()
    conn.close()

    print("\nMigration complete!")

    # Verify
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)

    cur.execute("PRAGMA table_info(monitoring_checks)")
    cols = [r[1] for r in cur.fetchall()]
    print("monitoring_checks columns:", cols)
    conn.close()

if __name__ == "__main__":
    run_migration()

import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

conn = sqlite3.connect('backend/server_monitor.db')
cur  = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

cur.execute("PRAGMA table_info(monitoring_checks)")
mc_cols = [r[1] for r in cur.fetchall()]
print("monitoring_checks cols:", mc_cols)

cur.execute("PRAGMA table_info(incidents)")
inc_cols = [r[1] for r in cur.fetchall()]
print("incidents cols:", inc_cols)

conn.close()
print("Schema check complete.")

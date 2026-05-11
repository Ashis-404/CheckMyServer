# Setup & Testing Guide

This guide walks through setting up and testing the Smart Server Monitoring System.

## Step 0: Initial Setup

### Clone/Copy the Files

All core files should be in place:
```
Server_checker/
├── main.py
├── database.py
├── health_checker.py
├── alert_manager.py
├── uptime_calculator.py
├── logger.py
├── requirements.txt
├── servers.json.example
├── config.json.example
├── .gitignore
├── README.md
├── logs/
└── server_monitor.db (created on first run)
```

### Install Python 3.7+

```bash
python --version  # Should be 3.7 or higher
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

This installs only `requests` library. No other external dependencies.

---

## Step 1: Create Configuration Files

### Create servers.json

```bash
cp servers.json.example servers.json
```

Edit `servers.json` with your servers:

```json
{
  "servers": [
    {
      "name": "Test Website (httpbin)",
      "url": "https://httpbin.org/status/200"
    },
    {
      "name": "Test Down Server",
      "url": "https://httpbin.org/status/500"
    },
    {
      "name": "Test Unreachable",
      "url": "http://192.0.2.1"
    }
  ]
}
```

**Quick Testing URLs:**
- `https://httpbin.org/status/200` → Always returns 200 (UP)
- `https://httpbin.org/status/500` → Always returns 500 (DOWN)
- `https://httpbin.org/delay/5` → 5 second delay (test timeout)
- `http://192.0.2.1` → Non-existent IP (test connection error)

### Create config.json

```bash
cp config.json.example config.json
```

For **testing without email**, modify `config.json`:

```json
{
  "check_interval": 10,
  "response_timeout": 3,
  "smtp": {
    "host": "smtp.gmail.com",
    "port": 587,
    "use_tls": true,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_email": "your-email@gmail.com",
    "to_email": "your-email@gmail.com"
  },
  "alert_cooldown_minutes": 1
}
```

**Quick Testing Setup:**
- Set `check_interval` to **10** (faster testing)
- Set `alert_cooldown_minutes` to **1** (quicker recovery alerts)
- Leave SMTP config as-is (tests will skip email if invalid)

---

## Step 2: Run Initial Test

### Start the System

```bash
python main.py
```

### Expected Output (First Run)

```
============================================================
🔍 Smart Server Monitoring System
============================================================
✓ Config loaded: config.json
✓ Servers loaded: 3 server(s)
  - Test Website (httpbin) (https://httpbin.org/status/200)
  - Test Down Server (https://httpbin.org/status/500)
  - Test Unreachable (http://192.0.2.1)
✓ Database initialized: server_monitor.db

🚀 Starting monitoring (interval: 10s, alert cooldown: 1m)
============================================================
Press Ctrl+C to stop

[Check #1] 2026-04-26 12:30:45
────────────────────────────────────────────────────────────
🟢 Test Website (httpbin): UP (0.245s)
🔴 Test Down Server: DOWN - HTTP 500
🔴 Test Unreachable: DOWN - Connection failed: HTTPConnectionPool

📊 Uptime Summary:
  Test Website (httpbin): 100% (24h)
  Test Down Server: 0% (24h)
  Test Unreachable: 0% (24h)

⏳ Next check in 10 seconds...
```

### Verification Checklist ✓

- [ ] All 3 servers checked
- [ ] Status symbols correct (🟢 for 200, 🔴 for others)
- [ ] Response times shown
- [ ] Error messages included for DOWN servers
- [ ] Uptime % calculated correctly
- [ ] No crashes

---

## Step 3: Test Status Transitions & Alerts

### Test 1: UP → DOWN Transition

Modify `servers.json` to make a server "fail":

```json
{
  "name": "Test Website (httpbin)",
  "url": "https://httpbin.org/status/500"
}
```

**Keep running `main.py`** and wait for next check cycle (10s).

**Expected behavior:**
```
⚡ Status change: UP → DOWN
✓ Alert email sent for Test Website (httpbin) (DOWN)
```

If SMTP is configured correctly, you'll receive an email. Otherwise, it logs the attempt.

### Test 2: DOWN → UP Recovery

Change `servers.json` back:

```json
{
  "name": "Test Website (httpbin)",
  "url": "https://httpbin.org/status/200"
}
```

**Expected behavior (after restart or next cycle):**
```
⚡ Status change: DOWN → UP
✓ Alert email sent for Test Website (httpbin) (UP)
```

### Test 3: Anti-Spam Alert Logic

Make a server DOWN and keep it that way for 2+ check cycles.

**Expected behavior:**
- ✓ First DOWN cycle: Alert sent ("⚠️ ALERT: ... is DOWN")
- ✓ Second DOWN cycle: Skipped alert ("↷ Skipped DOWN alert ... sent recently")
- ✓ Third DOWN cycle: Still skipped
- ✓ After 1 minute: Alert can be sent again (due to cooldown)

---

## Step 4: Verify Database

### Check Logged Data

```bash
sqlite3 server_monitor.db
```

Inside SQLite prompt:

```sql
-- View all servers
SELECT * FROM servers;

-- View recent checks
SELECT * FROM monitoring_checks ORDER BY timestamp DESC LIMIT 10;

-- View alerts sent
SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 5;

-- Calculate uptime for a server (e.g., server_id=1)
SELECT COUNT(*) as total, 
       SUM(CASE WHEN status='UP' THEN 1 ELSE 0 END) as up_count
FROM monitoring_checks WHERE server_id=1;

-- Exit SQLite
.quit
```

---

## Step 5: Permission & File Logging

### Verify Log Files

Check that logs are being written:

```bash
cat logs/server_checker.log
```

Expected content:
```
2026-04-26 12:30:45 - INFO - 🟢 Test Website (httpbin): UP (0.245s)
2026-04-26 12:30:45 - INFO - 🔴 Test Down Server: DOWN - HTTP 500
2026-04-26 12:31:05 - INFO - ⚡ Status change: UP → DOWN
2026-04-26 12:31:06 - INFO - ✓ Alert email sent for Test Website (httpbin) (DOWN)
```

---

## Step 6: Production Testing with Real Servers

Once basic testing passes, configure with real servers:

```json
{
  "servers": [
    {
      "name": "Production API",
      "url": "https://api.yourdomain.com/health"
    },
    {
      "name": "Frontend App",
      "url": "https://yourdomain.com"
    }
  ]
}
```

Adjust intervals:

```json
{
  "check_interval": 60,
  "response_timeout": 5,
  "alert_cooldown_minutes": 5
}
```

---

## Troubleshooting

### Problem: Python/pip not found

**Solution:**
```bash
# Windows: Use py instead of python
py --version
py -m pip install -r requirements.txt
py main.py
```

### Problem: "config.json not found"

**Solution:**
```bash
cp config.json.example config.json
# Then edit config.json with your SMTP details
```

### Problem: Email not sending

Check `logs/server_checker.log` for SMTP errors. Common issues:

1. **Wrong password**: Use app-specific password for Gmail
2. **Firewall blocking**: Allow outbound TCP 587
3. **2FA not enabled**: Gmail requires app passwords
4. **Wrong host/port**: Double-check SMTP server details

### Problem: Database locked error

```bash
# Only one main.py instance should run at a time
# Kill any stuck processes:
taskkill /IM python.exe /F

# Then clean database (WARNING: deletes history):
del server_monitor.db
python main.py
```

### Problem: Status always shows UNKNOWN

**Solution:** Restart `main.py`. The first check sets initial state.

---

## Performance Baseline

Run this perf test to verify performance:

```bash
python -c "
import health_checker
import time

urls = [
    'https://httpbin.org/status/200',
    'https://httpbin.org/delay/1',
    'https://httpbin.org/status/500',
]

start = time.time()
for url in urls:
    result = health_checker.check_server_health(url, timeout=5)
    print(f'{url}: {result[\"status\"]} ({result[\"response_time\"]}s)')

print(f'\nTotal time: {time.time() - start:.2f}s')
"
```

Expected: ~3-4 seconds for 3 requests (varies by network).

---

## Next Steps After Setup

✓ When basic testing passes:
1. Replace test URLs with real servers
2. Configure SMTP with valid credentials (optional)
3. Set production check interval (60-300 seconds)
4. Run system continuously (use `nohup` or task scheduler)
5. Monitor `logs/server_checker.log` for issues

✓ Future enhancements:
- Add more servers to config
- Customize email templates
- Monitor SSL certificates (Phase 3)
- Deploy dashboard (Phase 3)

---

## Manual Database Cleanup

If you need to start fresh:

```bash
# Delete database (loses all history)
del server_monitor.db

# Delete Logs
del logs\server_checker.log

# Run again to recreate
python main.py
```

---

**You're ready to go! Run `python main.py` to start monitoring.** 🚀

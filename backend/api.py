"""
CheckMyServer - REST API
Serves dashboard data, server management, incident tracking,
analytics, public status pages, and performance test results.
"""

import json
import re
import queue
import threading
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import logger as logger_module
import os
import database as db
import incident_manager
import perf_manager
import maintenance_manager
import notification_manager
import ssl_manager

app = Flask(__name__)
CORS(app)

log = logger_module.setup_logger()

# Load performance config limits at startup
_perf_config: dict = {}

def _load_perf_config():
    global _perf_config
    try:
        with open('config.json', 'r') as f:
            cfg = json.load(f)
        _perf_config = cfg.get('performance', {})
    except Exception:
        _perf_config = {}

_load_perf_config()


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def is_valid_url(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_db_connection():
    try:
        conn = db.get_db_connection()
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        log.error(f"Flask DB connection error: {e}")
        return None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker/Cloud deployments"""
    return jsonify({"status": "ok", "version": "1.0.0"}), 200

@app.route('/api/status', methods=['GET'])
def get_overall_status():
    """Returns aggregated system health"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, last_status, last_check_time FROM servers")
        servers = cursor.fetchall()

        total     = len(servers)
        if total == 0:
            return jsonify({"status": "Unknown", "message": "No servers configured", "total": 0})

        down_cnt  = sum(1 for s in servers if s['last_status'] == 'DOWN')
        warn_cnt  = sum(1 for s in servers if s['last_status'] == 'WARNING')

        if down_cnt == total:
            overall = "Major Outage"
        elif down_cnt > 0:
            overall = "Partial Outage"
        elif warn_cnt > 0:
            overall = "Degraded Performance"
        else:
            overall = "All Systems Operational"

        inc_summary = incident_manager.get_active_incidents_summary()

        return jsonify({
            "status":           overall,
            "total_servers":    total,
            "down_servers":     down_cnt,
            "warning_servers":  warn_cnt,
            "active_incidents": inc_summary["total_active"],
        })
    finally:
        conn.close()


@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Returns all servers with current state, uptime, and latest classified error"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, url, email, created_at, last_check_time, last_status, public_slug, is_public FROM servers"
        )
        servers = [dict(row) for row in cursor.fetchall()]

        for server in servers:
            # Uptime
            uptime = db.calculate_uptime_percentage(server['id'], days=1)
            server['uptime_24h'] = uptime if uptime is not None else 0.0

            # Latest check details (response time + classified error)
            cursor.execute(
                """SELECT response_time, error_message, error_category, severity
                   FROM monitoring_checks
                   WHERE server_id = ?
                   ORDER BY timestamp DESC LIMIT 1""",
                (server['id'],)
            )
            latest = cursor.fetchone()
            if latest:
                server['last_response_time'] = latest['response_time']
                server['last_error_category'] = latest['error_category']
                server['last_severity']        = latest['severity']
            else:
                server['last_response_time']  = None
                server['last_error_category'] = None
                server['last_severity']        = None

            # Active incident for this server
            active_incident = db.get_active_incident(server['id'])
            server['active_incident'] = active_incident

            # Maintenance status
            active_maint = maintenance_manager.get_active_maintenance(server['id'])
            server['is_maintenance'] = active_maint is not None

            # SSL status
            server['ssl_status'] = ssl_manager.get_ssl_status(server['id'])

        return jsonify(servers)
    finally:
        conn.close()


@app.route('/api/servers', methods=['POST'])
def add_server():
    """Create a new server to monitor"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['name', 'url', 'email']):
            return jsonify({"error": "Missing required fields: name, url, email"}), 400

        name  = data.get('name', '').strip()
        url   = data.get('url', '').strip()
        email = data.get('email', '').strip()

        if not name or len(name) < 2:
            return jsonify({"error": "Server name must be at least 2 characters"}), 400
        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not is_valid_url(url):
            return jsonify({"error": "URL must start with http:// or https://"}), 400
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM servers WHERE url = ?", (url,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": "Server with this URL already exists"}), 400
            conn.close()

        server_id = db.add_server(name, url, email)
        if server_id:
            return jsonify({"message": "Server added successfully", "server_id": server_id}), 201
        return jsonify({"error": "Failed to add server (duplicate name?)"}), 409

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    if db.delete_server(server_id):
        return jsonify({"message": "Server deleted successfully"}), 200
    return jsonify({"error": "Failed to delete server"}), 500

@app.route('/api/servers/<int:server_id>/public', methods=['PUT'])
def update_server_public_status(server_id):
    """Update public status page settings for a server"""
    data = request.get_json()
    is_public = 1 if data.get('is_public') else 0
    public_slug = data.get('public_slug')
    
    conn = db.get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500
    try:
        cursor = conn.cursor()
        if public_slug:
            # ensure uniqueness
            cursor.execute("SELECT id FROM servers WHERE public_slug = ? AND id != ?", (public_slug, server_id))
            if cursor.fetchone():
                return jsonify({"error": "Slug already in use"}), 400
                
        cursor.execute(
            "UPDATE servers SET is_public = ?, public_slug = ? WHERE id = ?",
            (is_public, public_slug, server_id)
        )
        conn.commit()
        return jsonify({"message": "Updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# HISTORY
# ============================================================================

@app.route('/api/history/<int:server_id>', methods=['GET'])
def get_server_history(server_id):
    """Returns monitoring history for a server (includes classified errors)"""
    try:
        server = db.get_server_by_id(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
        history = db.get_check_history(server_id, limit=100)
        return jsonify({"server": dict(server), "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# METRICS (legacy — kept for backward compat)
# ============================================================================

@app.route('/api/metrics/<int:server_id>', methods=['GET'])
def get_server_metrics(server_id):
    """Returns the last 24h of raw metrics for a server"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM servers WHERE id = ?", (server_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Server not found"}), 404

        cursor.execute('''
            SELECT timestamp, status, response_time, http_status_code,
                   error_category, severity
            FROM monitoring_checks
            WHERE server_id = ? AND timestamp > datetime('now', '-1 day')
            ORDER BY timestamp ASC
        ''', (server_id,))
        return jsonify([dict(row) for row in cursor.fetchall()])
    finally:
        conn.close()


# ============================================================================
# ANALYTICS
# ============================================================================

@app.route('/api/analytics/<int:server_id>', methods=['GET'])
def get_analytics(server_id):
    days = request.args.get('days', 7, type=int)
    analytics = db.get_server_analytics(server_id, days)
    return jsonify(analytics)


# ============================================================================
# INCIDENTS
# ============================================================================

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """Returns incidents with optional filters: ?server_id=X&status=active|resolved"""
    try:
        server_id = request.args.get('server_id', type=int)
        status    = request.args.get('status')
        limit     = request.args.get('limit', 50, type=int)

        incidents = db.get_incidents(server_id=server_id, status=status, limit=limit)
        return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/incidents/<int:server_id>', methods=['GET'])
def get_server_incidents(server_id):
    """Returns incidents for a specific server"""
    try:
        server = db.get_server_by_id(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        status   = request.args.get('status')
        limit    = request.args.get('limit', 50, type=int)
        incidents = db.get_incidents(server_id=server_id, status=status, limit=limit)
        return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUBLIC STATUS PAGE
# ============================================================================

@app.route('/api/status/<slug>', methods=['GET'])
def get_public_status(slug):
    """
    Public status page data for a server identified by name slug.
    Slug is the server name lowercased with spaces replaced by hyphens.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers")
        all_servers = cursor.fetchall()

        # Match slug to server name
        target = None
        for s in all_servers:
            name_slug = s['name'].lower().replace(' ', '-').replace('_', '-')
            if name_slug == slug:
                target = dict(s)
                break

        if not target:
            return jsonify({"error": "Server not found"}), 404

        server_id = target['id']

        # Uptime stats
        uptime_24h = db.calculate_uptime_percentage(server_id, days=1)
        uptime_7d  = db.calculate_uptime_percentage(server_id, days=7)
        uptime_30d = db.calculate_uptime_percentage(server_id, days=30)

        # Recent incidents
        recent_incidents = db.get_incidents(server_id=server_id, limit=10)

        # Active incident
        active_incident = db.get_active_incident(server_id)

        # 90-day daily uptime grid
        cursor.execute('''
            SELECT DATE(timestamp) as day,
                   COUNT(*) as total,
                   SUM(CASE WHEN status='UP' THEN 1 ELSE 0 END) as up_count
            FROM monitoring_checks
            WHERE server_id = ?
            AND timestamp > datetime('now', '-90 days')
            GROUP BY day
            ORDER BY day ASC
        ''', (server_id,))
        daily_grid = [
            {
                "day":      row["day"],
                "uptime":   round((row["up_count"] / row["total"]) * 100, 1) if row["total"] > 0 else None,
                "checks":   row["total"],
            }
            for row in cursor.fetchall()
        ]

        return jsonify({
            "server": {
                "name":            target['name'],
                "url":             target['url'],
                "last_status":     target['last_status'],
                "last_check_time": target['last_check_time'],
            },
            "uptime": {
                "24h":  uptime_24h,
                "7d":   uptime_7d,
                "30d":  uptime_30d,
            },
            "active_incident":  active_incident,
            "recent_incidents": recent_incidents,
            "daily_grid":       daily_grid,
        })
    finally:
        conn.close()



# ============================================================================
# PERFORMANCE TESTING
# ============================================================================

def _sse_publish(payload: dict):
    """Internal helper: push an event dict to all SSE subscribers."""
    disconnected = []
    for i, q in enumerate(sse_subscribers):
        try:
            q.put_nowait(payload)
        except Exception:
            disconnected.append(i)
    for idx in sorted(disconnected, reverse=True):
        if idx < len(sse_subscribers):
            sse_subscribers.pop(idx)


@app.route('/api/perf/tests', methods=['POST'])
def create_perf_test():
    """
    Create and immediately launch a new k6 performance test.
    Returns {test_id, status: 'running'} immediately (non-blocking).
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        url       = (data.get('url') or '').strip()
        vus       = data.get('vus', 10)
        duration  = data.get('duration_seconds', 30)
        method    = (data.get('method') or 'GET').strip().upper()
        headers   = data.get('headers')
        body      = data.get('body')
        server_id = data.get('server_id')

        if not url:
            return jsonify({"error": "URL is required"}), 400
        if not is_valid_url(url):
            return jsonify({"error": "URL must start with http:// or https://"}), 400

        max_vus = _perf_config.get('max_vus', 50)
        max_dur = _perf_config.get('max_duration_seconds', 120)

        try:
            vus      = int(vus)
            duration = int(duration)
        except (TypeError, ValueError):
            return jsonify({"error": "vus and duration_seconds must be integers"}), 400

        if vus < 1 or vus > max_vus:
            return jsonify({"error": f"Virtual users must be between 1 and {max_vus}"}), 400
        if duration < 5 or duration > max_dur:
            return jsonify({"error": f"Duration must be between 5 and {max_dur} seconds"}), 400
        if method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'):
            return jsonify({"error": f"Unsupported HTTP method: {method}"}), 400

        if headers and isinstance(headers, str):
            try:
                json.loads(headers)
            except json.JSONDecodeError:
                return jsonify({"error": "headers must be valid JSON"}), 400

        headers_str = headers if isinstance(headers, str) else (
            json.dumps(headers) if headers else None
        )

        test_id = db.create_perf_test(
            url=url, vus=vus, duration_seconds=duration,
            method=method, headers=headers_str, body=body, server_id=server_id,
        )
        if not test_id:
            return jsonify({"error": "Failed to create performance test record"}), 500

        perf_manager.start_test_thread(
            test_id=test_id, url=url, vus=vus,
            duration_seconds=duration, method=method,
            headers_str=headers_str, body=body,
            perf_config=_perf_config,
            sse_publish_fn=_sse_publish,
        )

        return jsonify({
            "test_id": test_id,
            "status":  "running",
            "message": f"Performance test #{test_id} started ({vus} VUs for {duration}s)",
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/perf/tests', methods=['GET'])
def list_perf_tests():
    """List recent performance tests, optional ?server_id=X&limit=N"""
    try:
        server_id = request.args.get('server_id', type=int)
        limit     = request.args.get('limit', 20, type=int)
        return jsonify(db.get_perf_tests(server_id=server_id, limit=limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/perf/tests/<int:test_id>', methods=['GET'])
def get_perf_test_detail(test_id):
    """Get a single performance test by ID (includes metrics)"""
    try:
        test = db.get_perf_test(test_id)
        if not test:
            return jsonify({"error": "Test not found"}), 404
        return jsonify(test)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/perf/tests/<int:test_id>/status', methods=['GET'])
def get_perf_test_status(test_id):
    """Poll-friendly lightweight status endpoint"""
    try:
        test = db.get_perf_test(test_id)
        if not test:
            return jsonify({"error": "Test not found"}), 404
        return jsonify({
            "test_id":       test_id,
            "status":        test['status'],
            "metrics":       test.get('metrics'),
            "error_message": test.get('error_message'),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/perf/benchmarks', methods=['GET'])
def get_perf_benchmarks():
    """Historical benchmark data for a URL. ?url=<url>&limit=10"""
    try:
        url   = request.args.get('url', '').strip()
        limit = request.args.get('limit', 10, type=int)
        if not url:
            return jsonify({"error": "url parameter is required"}), 400
        return jsonify(db.get_recent_benchmarks_for_url(url, limit=limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/perf/tests/<int:test_id>', methods=['DELETE'])
def delete_perf_test(test_id):
    """Delete a performance test record and its metrics"""
    try:
        test = db.get_perf_test(test_id)
        if not test:
            return jsonify({"error": "Test not found"}), 404
        if test['status'] == 'running':
            return jsonify({"error": "Cannot delete a running test"}), 409
        if db.delete_perf_test(test_id):
            return jsonify({"message": "Test deleted"}), 200
        return jsonify({"error": "Failed to delete test"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# MAINTENANCE & NOTIFICATIONS
# ============================================================================

@app.route('/api/maintenance', methods=['GET'])
def get_maintenance():
    try:
        return jsonify(maintenance_manager.get_all_maintenance())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/maintenance', methods=['POST'])
def schedule_maintenance():
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        target_server_ids = data.get('target_server_ids')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not title or not target_server_ids or not start_time or not end_time:
            return jsonify({"error": "Missing required fields"}), 400
            
        m_id = maintenance_manager.schedule_maintenance(
            title, description, target_server_ids, start_time, end_time
        )
        if m_id:
            return jsonify({"message": "Maintenance scheduled", "id": m_id}), 201
        return jsonify({"error": "Failed to schedule maintenance"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/maintenance/<int:m_id>', methods=['DELETE'])
def delete_maintenance(m_id):
    try:
        if maintenance_manager.delete_maintenance(m_id):
            return jsonify({"message": "Deleted"}), 200
        return jsonify({"error": "Failed to delete"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    try:
        limit = request.args.get('limit', 50, type=int)
        return jsonify(notification_manager.get_notifications(limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/<int:n_id>/read', methods=['PUT'])
def mark_notification_read(n_id):
    try:
        if notification_manager.mark_as_read(n_id):
            return jsonify({"message": "Marked as read"}), 200
        return jsonify({"error": "Failed to update"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/unread_count', methods=['GET'])
def get_unread_count():
    try:
        return jsonify({"unread_count": notification_manager.get_unread_count()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PUBLIC STATUS API
# ============================================================================

@app.route('/api/public/status/<slug>', methods=['GET'])
def get_public_status_page(slug):
    """Get sanitized public status for a server by its slug"""
    conn = db.get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, last_status, last_check_time FROM servers WHERE public_slug = ? AND is_public = 1", (slug,))
        server = cursor.fetchone()
        
        if not server:
            return jsonify({"error": "Not found or not public"}), 404
            
        server_id = server['id']
        uptime_30d = db.calculate_uptime_percentage(server_id, days=30)
        active_incident = db.get_active_incident(server_id)
        
        # Don't expose sensitive info like email or URL
        return jsonify({
            "name": server['name'],
            "status": server['last_status'],
            "last_check_time": server['last_check_time'],
            "uptime_30d": uptime_30d,
            "active_incident": active_incident,
            "latency_trend": db.get_server_analytics(server_id, days=1).get("latency_trend", [])
        })
    finally:
        conn.close()

# ============================================================================
# SSE — SERVER-SENT EVENTS
# ============================================================================

sse_subscribers = []


@app.route('/api/events/publish', methods=['POST'])
def publish_event():
    """Internal endpoint for the monitoring engine to push SSE events"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        disconnected = []
        for i, q in enumerate(sse_subscribers):
            try:
                q.put_nowait(data)
            except queue.Full:
                disconnected.append(i)

        for index in sorted(disconnected, reverse=True):
            if index < len(sse_subscribers):
                sse_subscribers.pop(index)

        return jsonify({"message": "Published", "subscribers": len(sse_subscribers)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/events/stream', methods=['GET'])
def stream_events():
    """SSE streaming endpoint for real-time dashboard updates"""
    def event_generator():
        q = queue.Queue(maxsize=100)
        sse_subscribers.append(q)
        yield 'retry: 5000\ndata: {"type": "connected"}\n\n'
        try:
            while True:
                try:
                    event_data = q.get(timeout=20)
                    yield f"data: {json.dumps(event_data)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in sse_subscribers:
                sse_subscribers.remove(q)

    response = app.response_class(event_generator(), mimetype='text/event-stream')
    response.headers['Cache-Control']      = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            port = config.get("api_port", 5000)
    except Exception:
        port = 5000

    db.init_db()
    log.error(f"🚀 CheckMyServer API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

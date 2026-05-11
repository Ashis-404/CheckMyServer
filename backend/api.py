"""
Smart Server Monitoring System - REST API
Serves read-only dashboard data and allows dynamic server management
"""

import json
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import database as db

app = Flask(__name__)
CORS(app)

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def is_valid_url(url: str) -> bool:
    """Validate if URL starts with http:// or https://"""
    return url.startswith('http://') or url.startswith('https://')

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_db_connection():
    """Get a fresh DB connection for Flask requests"""
    try:
        conn = sqlite3.connect(db.DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Flask DB Connection error: {e}")
        return None

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
        
        total_servers = len(servers)
        if total_servers == 0:
            return jsonify({"status": "Unknown", "message": "No servers configured", "total": 0})
            
        down_servers = sum(1 for s in servers if s['last_status'] == 'DOWN')
        warning_servers = sum(1 for s in servers if s['last_status'] == 'WARNING')
        
        if down_servers == total_servers:
            overall_status = "Major Outage"
        elif down_servers > 0:
            overall_status = "Partial Outage"
        elif warning_servers > 0:
            overall_status = "Degraded Performance"
        else:
            overall_status = "All Systems Operational"
            
        return jsonify({
            "status": overall_status,
            "total_servers": total_servers,
            "down_servers": down_servers,
            "warning_servers": warning_servers
        })
    finally:
        conn.close()

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Returns a list of all servers with their current state & uptime"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, url, email, created_at, last_check_time, last_status FROM servers")
        servers = [dict(row) for row in cursor.fetchall()]
        
        # Hydrate with uptime
        for server in servers:
            uptime = db.calculate_uptime_percentage(server['id'], days=1)
            server['uptime_24h'] = uptime if uptime is not None else 0.0
            
        return jsonify(servers)
    finally:
        conn.close()

@app.route('/api/servers', methods=['POST'])
def add_server():
    """Create a new server to monitor"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(k in data for k in ['name', 'url', 'email']):
            return jsonify({"error": "Missing required fields: name, url, email"}), 400
        
        name = data.get('name', '').strip()
        url = data.get('url', '').strip()
        email = data.get('email', '').strip()
        
        # Validation
        if not name or len(name) < 2:
            return jsonify({"error": "Server name must be at least 2 characters"}), 400
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
            
        if not is_valid_url(url):
            return jsonify({"error": "URL must start with http:// or https://"}), 400
        
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check for duplicate URL
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM servers WHERE url = ?", (url,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": "Server with this URL already exists"}), 400
            conn.close()
        
        # Add to database
        server_id = db.add_server(name, url, email)
        if server_id:
            return jsonify({
                "message": "Server added successfully",
                "server_id": server_id
            }), 201
        else:
            return jsonify({"error": "Failed to add server (duplicate name?)"}), 409
            
    except Exception as e:
        print(f"Error adding server: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics/<int:server_id>', methods=['GET'])
def get_server_metrics(server_id):
    """Returns the last 24 hours of metrics for a server"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        # Verify server exists
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM servers WHERE id = ?", (server_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Server not found"}), 404
        
        # Get checks from the last 24 hours, ordered chronologically
        cursor.execute('''
            SELECT timestamp, status, response_time, http_status_code 
            FROM monitoring_checks 
            WHERE server_id = ? AND timestamp > datetime('now', '-1 day')
            ORDER BY timestamp ASC
        ''', (server_id,))
        
        metrics = [dict(row) for row in cursor.fetchall()]
        return jsonify(metrics)
    finally:
        conn.close()

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    """Delete a server"""
    try:
        # Verify server exists
        server = db.get_server_by_id(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
        
        # Delete
        if db.delete_server(server_id):
            return jsonify({"message": "Server deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete server"}), 500
            
    except Exception as e:
        print(f"Error deleting server: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<int:server_id>', methods=['GET'])
def get_server_history(server_id):
    """Returns monitoring history for a server"""
    try:
        # Verify server exists
        server = db.get_server_by_id(server_id)
        if not server:
            return jsonify({"error": "Server not found"}), 404
        
        # Get history
        history = db.get_check_history(server_id, limit=100)
        return jsonify({
            "server": dict(server),
            "history": history
        })
        
    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Retrieve port from config.json if available
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            port = config.get("api_port", 5000)
    except Exception:
        port = 5000
    
    print(f"🚀 Starting Dashboard REST API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

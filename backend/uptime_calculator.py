"""
Uptime Calculator module for Smart Server Monitoring System
Calculates uptime percentages and generates reports
"""

from typing import Dict, Optional
import database as db


def get_uptime_report(server_id: int) -> Dict:
    """
    Get uptime report for a server
    
    Returns dict with daily, weekly, monthly uptime percentages
    """
    
    report = {
        "server_id": server_id,
        "daily": None,
        "weekly": None,
        "monthly": None,
        "overall": None
    }
    
    # Calculate uptime for different periods
    report["daily"] = db.calculate_uptime_percentage(server_id, days=1)
    report["weekly"] = db.calculate_uptime_percentage(server_id, days=7)
    report["monthly"] = db.calculate_uptime_percentage(server_id, days=30)
    
    # Overall (all available data)
    total_checks = _get_total_checks(server_id)
    up_checks = _get_up_checks(server_id)
    
    if total_checks and total_checks > 0:
        report["overall"] = round((up_checks / total_checks) * 100, 2)
    
    return report


def format_uptime_report(server_name: str, report: Dict) -> str:
    """Format uptime report for display"""
    
    output = f"\n📊 Uptime Report: {server_name}\n"
    output += "─" * 40 + "\n"
    
    if report["daily"] is not None:
        output += f"  Daily (24h):    {report['daily']}%\n"
    
    if report["weekly"] is not None:
        output += f"  Weekly (7d):    {report['weekly']}%\n"
    
    if report["monthly"] is not None:
        output += f"  Monthly (30d):  {report['monthly']}%\n"
    
    if report["overall"] is not None:
        output += f"  Overall:        {report['overall']}%\n"
    
    output += "─" * 40
    
    return output


def _get_total_checks(server_id: int) -> int:
    """Get total number of checks for a server"""
    conn = db.get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM monitoring_checks WHERE server_id = ?", (server_id,))
        row = cursor.fetchone()
        return row['count'] if row else 0
    finally:
        conn.close()


def _get_up_checks(server_id: int) -> int:
    """Get number of UP checks for a server"""
    conn = db.get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM monitoring_checks WHERE server_id = ? AND status = 'UP'", (server_id,))
        row = cursor.fetchone()
        return row['count'] if row else 0
    finally:
        conn.close()


def print_uptime_stats(server_id: int, server_name: str):
    """Print uptime report for a server"""
    report = get_uptime_report(server_id)
    print(format_uptime_report(server_name, report))

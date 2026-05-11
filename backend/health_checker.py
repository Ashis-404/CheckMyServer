"""
Health Checker module for Smart Server Monitoring System
Performs HTTP checks and determines server status
"""

import requests
import time
from typing import Dict, Optional


def check_server_health(url: str, timeout: int = 2) -> Dict:
    """
    Check the health of a server via HTTP GET request
    """

    result = {
        "status": "DOWN",
        "response_time": None,
        "http_status_code": None,
        "error": None
    }

    # Validate URL
    if not url:
        result["error"] = "URL is empty"
        return result

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    start_time = time.time()

    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)

        response_time = time.time() - start_time
        result["response_time"] = round(response_time, 3)
        result["http_status_code"] = response.status_code

        # 🔥 UPDATED STATUS LOGIC

        # 1. Server error → DOWN
        if response.status_code >= 500:
            result["status"] = "DOWN"
            result["error"] = f"HTTP {response.status_code}"

        # 2. Slow response → WARNING
        elif response_time >= timeout:
            result["status"] = "WARNING"
            result["error"] = f"Slow response ({response_time:.3f}s)"

        # 3. Success codes → UP
        elif 200 <= response.status_code < 400:
            result["status"] = "UP"

        # 4. Other codes (like 4xx) → DOWN
        else:
            result["status"] = "DOWN"
            result["error"] = f"HTTP {response.status_code}"

        return result

    except requests.exceptions.Timeout:
        response_time = time.time() - start_time
        result["response_time"] = round(response_time, 3)
        result["status"] = "DOWN"
        result["error"] = f"Timeout after {timeout}s"
        return result

    except requests.exceptions.ConnectionError as e:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"] = "DOWN"
        result["error"] = f"Connection failed: {str(e)}"
        return result

    except requests.exceptions.RequestException as e:
        result["response_time"] = round(time.time() - start_time, 3)
        result["status"] = "DOWN"
        result["error"] = f"Request error: {str(e)}"
        return result

    except Exception as e:
        result["status"] = "DOWN"
        result["error"] = f"Unexpected error: {str(e)}"
        return result


def is_status_up(http_code: Optional[int]) -> bool:
    """Check if HTTP status code indicates UP"""
    if http_code is None:
        return False
    return 200 <= http_code < 400


def format_health_check_result(result: Dict, server_name: str) -> str:
    """Format health check result for printing"""

    # 🔥 UPDATED SYMBOL LOGIC
    if result["status"] == "UP":
        status_symbol = "🟢"
    elif result["status"] == "WARNING":
        status_symbol = "🟡"
    else:
        status_symbol = "🔴"

    output = f"{status_symbol} {server_name}: {result['status']}"

    if result["response_time"] is not None:
        output += f" ({result['response_time']:.3f}s)"

    if result["error"]:
        output += f" - {result['error']}"

    return output
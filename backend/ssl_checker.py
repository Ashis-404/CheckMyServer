import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Optional

def check_ssl(url: str) -> Dict:
    """
    Check SSL certificate for a given URL.
    Returns dict with validity, days_remaining, and issuer.
    """
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        return {"error": "Not an HTTPS URL", "valid": False}

    hostname = parsed.netloc
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    port = parsed.port or 443

    context = ssl.create_default_context()
    # Create a connection with a timeout
    try:
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                # 'notAfter' format: 'Oct 14 12:00:00 2024 GMT'
                expiry_str = cert.get('notAfter')
                if not expiry_str:
                    return {"error": "No expiry date found", "valid": False}
                    
                expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                days_remaining = (expiry_date - datetime.utcnow()).days
                
                issuer = dict(x[0] for x in cert.get('issuer', []))
                issuer_name = issuer.get('organizationName', issuer.get('commonName', 'Unknown Issuer'))
                
                status = 'Valid'
                if days_remaining <= 0:
                    status = 'Expired'
                elif days_remaining < 7:
                    status = 'Critical'
                elif days_remaining < 30:
                    status = 'Expiring Soon'
                    
                return {
                    "valid": days_remaining > 0,
                    "days_remaining": days_remaining,
                    "expiry_date": expiry_date.isoformat(),
                    "issuer": issuer_name,
                    "status": status,
                    "error": None
                }
    except ssl.SSLCertVerificationError as e:
        return {"error": f"SSL Verification Failed: {e}", "valid": False, "status": "Expired/Invalid"}
    except Exception as e:
        return {"error": str(e), "valid": False, "status": "Error"}

# If run standalone for testing
if __name__ == '__main__':
    print(check_ssl('https://google.com'))

"""
Authorization client for Smart Piggy Bank
Makes HTTP request to backend /api/access/check
"""
import socket
import json
import time


def check_authorization(backend_host, backend_port, uid, wifi_connected, timeout_s=5):
    """
    Check if RFID card is authorized via backend API
    
    Args:
        backend_host: Backend hostname/IP (e.g., "192.168.1.10")
        backend_port: Backend port (default 5000 or 5001)
        uid: RFID card UID
        wifi_connected: Boolean indicating WiFi status
        timeout_s: Socket timeout in seconds
    
    Returns:
        {
            "authorized": bool,
            "access_granted": bool,
            "reason": str,
            "error": None or str
        }
    """
    
    # Default response if backend unreachable
    default_response = {
        "authorized": False,
        "access_granted": False,
        "reason": "BACKEND_UNREACHABLE",
        "error": "Cannot reach backend"
    }
    
    if not backend_host:
        return {**default_response, "reason": "NO_BACKEND_HOST"}
    
    try:
        # Build HTTP request
        payload = json.dumps({
            "uid": uid,
            "wifi_connected": wifi_connected
        })
        
        http_request = f"""POST /api/access/check HTTP/1.1\r
Host: {backend_host}:{backend_port}\r
Content-Type: application/json\r
Content-Length: {len(payload)}\r
Connection: close\r
\r
{payload}"""
        
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_s)
        
        # Connect and send
        sock.connect((backend_host, backend_port))
        sock.sendall(http_request.encode('utf-8'))
        
        # Receive response
        response_data = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break
        
        sock.close()
        
        # Parse HTTP response
        response_str = response_data.decode('utf-8', errors='ignore')
        
        # Split headers and body
        if '\r\n\r\n' in response_str:
            body = response_str.split('\r\n\r\n', 1)[1]
        else:
            body = response_str
        
        # Parse JSON body
        result = json.loads(body)
        
        return {
            "authorized": result.get("authorized", False),
            "access_granted": result.get("access_granted", False),
            "reason": result.get("reason", "UNKNOWN"),
            "error": None
        }
        
    except Exception as e:
        print(f"[AUTH] Error: {e}")
        return {
            **default_response,
            "error": str(e)
        }


def should_unlock(result):
    """
    Determine if device should unlock based on authorization result
    
    Args:
        result: Dictionary from check_authorization()
    
    Returns:
        True if access_granted is True, False otherwise
    """
    return bool(result.get("access_granted", False))

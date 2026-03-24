import socket
import json
from machine import Pin

def start_server(get_status_callback):
    """
    Start HTTP server on port 80
    Serves dashboard and API endpoint /api/status
    """
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(addr)
    server_socket.listen(5)
    print(f"Web server running on http://0.0.0.0:80")

    # Simple HTML dashboard
    html_dashboard = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Piggy Bank</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #005C55 0%, #0F766E 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 92, 85, 0.15);
                padding: 40px;
                max-width: 600px;
                width: 100%;
            }
            h1 {
                color: #005C55;
                margin-bottom: 30px;
                text-align: center;
                font-size: 28px;
            }
            .status-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }
            .status-card {
                background: #F7FAFE;
                border-radius: 12px;
                padding: 20px;
                border-left: 4px solid #14B8A6;
            }
            .status-label {
                color: #6B7280;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                margin-bottom: 8px;
            }
            .status-value {
                color: #005C55;
                font-size: 24px;
                font-weight: 700;
            }
            .coin-breakdown {
                background: #F7FAFE;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .coin-item {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #E5E7EB;
            }
            .coin-item:last-child {
                border-bottom: none;
            }
            .coin-label { color: #6B7280; }
            .coin-count { color: #005C55; font-weight: 600; }
            .lock-indicator {
                display: inline-block;
                padding: 6px 12px;
                background: #DBEAFE;
                color: #0369A1;
                border-radius: 9999px;
                font-size: 12px;
                font-weight: 600;
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #E5E7EB;
                border-radius: 9999px;
                overflow: hidden;
                margin-top: 10px;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #14B8A6 0%, #0F766E 100%);
                border-radius: 9999px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 Smart Piggy Bank</h1>
            
            <div class="status-grid">
                <div class="status-card">
                    <div class="status-label">Total Balance</div>
                    <div class="status-value" id="total">0฿</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Coin Count</div>
                    <div class="status-value" id="coin-count">0</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Lock Status</div>
                    <div id="lock-status" class="lock-indicator">🔒 Locked</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Fill Level</div>
                    <div class="status-value" id="fill-percent">0%</div>
                </div>
            </div>

            <div class="coin-breakdown">
                <div class="status-label">Coins by Denomination</div>
                <div class="coin-item">
                    <span class="coin-label">10฿</span>
                    <span class="coin-count" id="coin-10">0</span>
                </div>
                <div class="coin-item">
                    <span class="coin-label">5฿</span>
                    <span class="coin-count" id="coin-5">0</span>
                </div>
                <div class="coin-item">
                    <span class="coin-label">2฿</span>
                    <span class="coin-count" id="coin-2">0</span>
                </div>
                <div class="coin-item">
                    <span class="coin-label">1฿</span>
                    <span class="coin-count" id="coin-1">0</span>
                </div>
            </div>

            <div class="coin-breakdown">
                <div class="status-label">System Status</div>
                <div class="coin-item">
                    <span class="coin-label">WiFi Connected</span>
                    <span class="coin-count" id="wifi-status">✓</span>
                </div>
                <div class="coin-item">
                    <span class="coin-label">Distance (cm)</span>
                    <span class="coin-count" id="distance">--</span>
                </div>
                <div class="coin-item">
                    <span class="coin-label">Capacity</span>
                    <span class="coin-count" id="capacity">0%</span>
                </div>
            </div>
        </div>

        <script>
            async function updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    // Update values
                    document.getElementById('total').textContent = data.total + '฿';
                    document.getElementById('coin-count').textContent = 
                        (data.coins['10'] + data.coins['5'] + data.coins['2'] + data.coins['1']) || 0;
                    
                    document.getElementById('coin-10').textContent = data.coins['10'] || 0;
                    document.getElementById('coin-5').textContent = data.coins['5'] || 0;
                    document.getElementById('coin-2').textContent = data.coins['2'] || 0;
                    document.getElementById('coin-1').textContent = data.coins['1'] || 0;
                    
                    document.getElementById('lock-status').textContent = 
                        data.is_locked ? '🔒 Locked' : '🔓 Unlocked';
                    
                    document.getElementById('fill-percent').textContent = 
                        Math.round(data.fill_percent || 0) + '%';
                    
                    document.getElementById('distance').textContent = 
                        data.distance_cm ? data.distance_cm.toFixed(1) : '--';
                    
                    document.getElementById('wifi-status').textContent = 
                        data.wifi_connected ? '✓ Connected' : '✗ Disconnected';
                    
                    document.getElementById('capacity').textContent = 
                        Math.round((data.fill_percent || 0) * 100) / 100 + '%';
                } catch (error) {
                    console.error('Failed to fetch status:', error);
                }
            }
            
            // Update every 2 seconds
            setInterval(updateStatus, 2000);
            updateStatus();
        </script>
    </body>
    </html>
    """

    while True:
        try:
            client_socket, client_addr = server_socket.accept()
            request = client_socket.recv(1024).decode()
            
            if 'GET /api/status' in request:
                # JSON API endpoint
                status = get_status_callback()
                response = json.dumps(status)
                http_response = f"""HTTP/1.1 200 OK\r
Content-Type: application/json\r
Content-Length: {len(response)}\r
\r
{response}"""
            elif 'GET /' in request:
                # Serve HTML dashboard
                response = html_dashboard
                http_response = f"""HTTP/1.1 200 OK\r
Content-Type: text/html; charset=utf-8\r
Content-Length: {len(response)}\r
\r
{response}"""
            else:
                # 404
                response = "Not Found"
                http_response = f"""HTTP/1.1 404 Not Found\r
Content-Type: text/plain\r
Content-Length: {len(response)}\r
\r
{response}"""
            
            client_socket.send(http_response.encode())
            client_socket.close()
        except Exception as e:
            print(f"Server error: {e}")
            break

"""Centralized runtime config for ESP32 side.

When your network host changes, update MQTT_BROKER by running:
  python tools/set_host.py --auto
or
  python tools/set_host.py <host-or-ip>
"""

# WiFi credentials: kept in esp32/wifi_secrets.py (git-ignored).
# Copy esp32/wifi_secrets.example.py to esp32/wifi_secrets.py and fill in.
try:
    from wifi_secrets import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    WIFI_SSID = ""
    WIFI_PASSWORD = ""

# MQTT config (local-first)
MQTT_BROKER = "Chanwits-MacBook-Pro.local"
MQTT_TOPIC_PUBLISH = "piggybank/data"
MQTT_TOPIC_SUBSCRIBE = "piggybank/command"

# Backend API config (for authorization checks)
BACKEND_HOST = "Chanwits-MacBook-Pro.local"  # Same host as MQTT broker
BACKEND_PORT = 5001  # ✅ Must match config.shared.py (API_PORT)

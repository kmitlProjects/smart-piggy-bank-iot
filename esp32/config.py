"""Centralized runtime config for ESP32 side.

When your network host changes, update MQTT_BROKER by running:
  python tools/set_host.py --auto
or
  python tools/set_host.py <host-or-ip>
"""

# WiFi credentials
WIFI_SSID = "Galaxy A52 5GD9C0"
WIFI_PASSWORD = "neae4850"

# MQTT config (local-first)
MQTT_BROKER = "Chanwits-MacBook-Pro.local"
MQTT_TOPIC_PUBLISH = "piggybank/data"
MQTT_TOPIC_SUBSCRIBE = "piggybank/command"

# Backend API config (for authorization checks)
BACKEND_HOST = "Chanwits-MacBook-Pro.local"  # Same host as MQTT broker
BACKEND_PORT = 5001  # ✅ Must match config.shared.py (API_PORT)

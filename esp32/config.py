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
BACKEND_PORT = 5001  # Must match backend API_PORT in docker-compose/backend config

# Closed RFID whitelist (offline fallback): only these 2 UIDs are allowed.
LOCKED_RFID_UIDS = [
  [182, 188, 21, 6, 25],
  [195, 118, 240, 6, 67],
]

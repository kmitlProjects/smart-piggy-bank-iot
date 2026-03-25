"""Centralized runtime config for ESP32 side.

When your network host changes, update MQTT_BROKER by running:
  python tools/set_host.py --auto
or
  python tools/set_host.py <host-or-ip>
"""

# WiFi credentials
WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_PASSWORD"

# MQTT config (local-first)
MQTT_BROKER = "Chanwits-MacBook-Pro.local"
MQTT_TOPIC_PUBLISH = "piggybank/data"
MQTT_TOPIC_SUBSCRIBE = "piggybank/command"

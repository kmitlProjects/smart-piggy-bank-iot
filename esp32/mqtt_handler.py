"""
Simple MQTT client for MicroPython on ESP32
Connects to HiveMQ Cloud free tier
"""
import json
from umqtt.simple import MQTTClient
import time


class MQTTHandler:
    def __init__(self, broker, topic_publish, topic_subscribe=None, client_id="piggybank"):
        self.broker = broker
        self.topic_pub = topic_publish
        self.topic_sub = topic_subscribe
        self.client_id = client_id
        self.client = None
        self.connected = False
        self.last_reconnect_ms = 0
        self.reconnect_cooldown_ms = 5000  # Wait 5s before retry

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = MQTTClient(self.client_id, self.broker)
            self.client.connect()
            self.connected = True
            self.last_reconnect_ms = time.ticks_ms()
            print(f"MQTT connected to {self.broker}")
            return True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.connected = False
            return False

    def _try_reconnect(self):
        """Attempt to reconnect if cooldown expired"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_reconnect_ms) >= self.reconnect_cooldown_ms:
            self.last_reconnect_ms = now
            return self.connect()
        return False

    def publish(self, data):
        """Publish data to broker with auto-reconnect"""
        if not self.connected:
            # Try to reconnect if disconnected
            if not self._try_reconnect():
                return False
        
        try:
            payload = json.dumps(data) if isinstance(data, dict) else str(data)
            self.client.publish(self.topic_pub, payload)
            print("MQTT: published")
            return True
        except OSError as e:
            # Connection lost (ENOTCONN = 128)
            if e.errno == 128 or "ENOTCONN" in str(e):
                print(f"MQTT connection lost (ENOTCONN), will retry...")
                self.connected = False
            else:
                print(f"MQTT publish failed: {e}")
            return False
        except Exception as e:
            print(f"MQTT publish failed: {e}")
            self.connected = False
            return False

    def check_message(self):
        """Check for incoming messages"""
        try:
            self.client.check_msg()
        except Exception as e:
            print(f"MQTT check_msg failed: {e}")

    def disconnect(self):
        """Disconnect from broker"""
        try:
            self.client.disconnect()
            self.connected = False
        except Exception:
            pass

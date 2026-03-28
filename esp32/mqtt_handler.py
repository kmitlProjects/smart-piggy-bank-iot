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
        self.last_reconnect_attempt_ms = 0
        self.reconnect_cooldown_ms = 5000  # Wait 5s before retry
        self.message_handler = None

    def set_message_handler(self, handler):
        self.message_handler = handler

    def _on_message(self, topic, msg):
        try:
            topic_text = topic.decode() if isinstance(topic, bytes) else str(topic)
            payload_text = msg.decode() if isinstance(msg, bytes) else str(msg)
            payload = json.loads(payload_text)
            if self.message_handler:
                self.message_handler(topic_text, payload)
        except Exception as e:
            print(f"MQTT callback failed: {e}")

    def _close_client(self):
        if self.client is None:
            return
        try:
            self.client.disconnect()
        except Exception:
            pass
        self.client = None

    def mark_disconnected(self, reason=None):
        if reason and (self.connected or self.client is not None):
            print(f"MQTT disconnected: {reason}")
        self.connected = False
        self._close_client()

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self._close_client()
            self.client = MQTTClient(self.client_id, self.broker)
            self.client.set_callback(self._on_message)
            self.client.connect()
            if self.topic_sub:
                self.client.subscribe(self.topic_sub)
                print(f"MQTT subscribed to {self.topic_sub}")
            self.connected = True
            print(f"MQTT connected to {self.broker}")
            return True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.connected = False
            self.client = None
            return False

    def ensure_connected(self, force=False):
        """Attempt to reconnect if cooldown expired"""
        if self.connected and self.client is not None:
            return True

        now = time.ticks_ms()
        if force or time.ticks_diff(now, self.last_reconnect_attempt_ms) >= self.reconnect_cooldown_ms:
            self.last_reconnect_attempt_ms = now
            return self.connect()
        return False

    def publish(self, data):
        """Publish data to broker with auto-reconnect"""
        if not self.connected:
            # Try to reconnect if disconnected
            if not self.ensure_connected():
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
                self.mark_disconnected("socket lost")
            else:
                print(f"MQTT publish failed: {e}")
                self.mark_disconnected(str(e))
            return False
        except Exception as e:
            print(f"MQTT publish failed: {e}")
            self.mark_disconnected(str(e))
            return False

    def check_message(self):
        """Check for incoming messages"""
        if not self.connected or self.client is None:
            return False

        try:
            self.client.check_msg()
            return True
        except Exception as e:
            print(f"MQTT check_msg failed: {e}")
            self.mark_disconnected("check_msg failed")
            return False

    def disconnect(self):
        """Disconnect from broker"""
        self.mark_disconnected("manual disconnect")

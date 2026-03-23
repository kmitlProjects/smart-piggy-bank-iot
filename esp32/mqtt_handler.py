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

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = MQTTClient(self.client_id, self.broker)
            self.client.connect()
            self.connected = True
            print(f"✓ MQTT connected to {self.broker}")
            return True
        except Exception as e:
            print(f"✗ MQTT connection failed: {e}")
            self.connected = False
            return False

    def publish(self, data):
        """Publish data to broker"""
        if not self.connected:
            return False
        
        try:
            payload = json.dumps(data) if isinstance(data, dict) else str(data)
            self.client.publish(self.topic_pub, payload)
            return True
        except Exception as e:
            print(f"✗ MQTT publish failed: {e}")
            return False

    def check_message(self):
        """Check for incoming messages"""
        try:
            self.client.check_msg()
        except Exception as e:
            print(f"✗ MQTT check_msg failed: {e}")

    def disconnect(self):
        """Disconnect from broker"""
        try:
            self.client.disconnect()
            self.connected = False
        except Exception:
            pass

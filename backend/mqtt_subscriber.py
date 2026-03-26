import json
import threading

import paho.mqtt.client as mqtt

from config import MQTT_BROKER, MQTT_CLIENT_ID, MQTT_PORT, MQTT_TOPIC_DATA
from db import (
    insert_coin_event,
    mark_device_seen,
    record_rfid_scan,
    upsert_device_runtime,
    upsert_latest_status,
)


class MQTTIngestService:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.thread = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"MQTT connected: reason_code={reason_code}")
        client.subscribe(MQTT_TOPIC_DATA)
        print(f"MQTT subscribed topic: {MQTT_TOPIC_DATA}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        print(f"MQTT disconnected: reason_code={reason_code}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if payload.get("rfid_scan_uid") is not None:
                record_rfid_scan(payload["rfid_scan_uid"], source=payload.get("rfid_scan_source", "esp32_enroll"))

            upsert_device_runtime(payload, device_id="esp32")

            if any(key in payload for key in ("coins", "total", "distance_cm", "is_locked", "fill_percent")):
                insert_coin_event(payload, source="mqtt", device_id="esp32")
                upsert_latest_status(payload, device_id="esp32")
                mark_device_seen(device_id="esp32", reason=payload.get("heartbeat_reason", "HEARTBEAT"))
            print("MQTT message stored")
        except Exception as exc:
            print(f"MQTT ingest failed: {exc}")

    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=30)
        self.thread = threading.Thread(target=self.client.loop_forever, daemon=True)
        self.thread.start()

    def stop(self):
        try:
            self.client.disconnect()
        except Exception:
            pass

import json
import time

from paho.mqtt import publish

from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_COMMAND


def publish_reset_command(device_id: str = "esp32") -> bool:
    payload = {
        "action": "reset_data",
        "device_id": device_id,
    }

    try:
        # Send a few times with QoS1 to reduce chance of losing a one-shot command.
        body = json.dumps(payload)
        for i in range(3):
            publish.single(
                MQTT_TOPIC_COMMAND,
                payload=body,
                hostname=MQTT_BROKER,
                port=MQTT_PORT,
                qos=1,
                retain=False,
            )
            if i < 2:
                time.sleep(0.2)
        return True
    except Exception as exc:
        print(f"[MQTT COMMAND] publish reset failed: {exc}")
        return False

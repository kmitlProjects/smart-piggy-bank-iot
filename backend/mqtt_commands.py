import json

from paho.mqtt import publish

from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_COMMAND


def publish_reset_command(device_id: str = "esp32") -> bool:
    payload = {
        "action": "reset_data",
        "device_id": device_id,
    }

    try:
        publish.single(
            MQTT_TOPIC_COMMAND,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            retain=False,
        )
        return True
    except Exception as exc:
        print(f"[MQTT COMMAND] publish reset failed: {exc}")
        return False

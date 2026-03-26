import json
import time

from paho.mqtt import publish

from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_COMMAND


def _publish_command(payload: dict, retries: int = 3, delay_s: float = 0.2) -> bool:
    try:
        body = json.dumps(payload)
        for i in range(retries):
            publish.single(
                MQTT_TOPIC_COMMAND,
                payload=body,
                hostname=MQTT_BROKER,
                port=MQTT_PORT,
                qos=1,
                retain=False,
            )
            if i < retries - 1:
                time.sleep(delay_s)
        return True
    except Exception as exc:
        print(f"[MQTT COMMAND] publish failed: {exc}")
        return False


def publish_reset_command(device_id: str = "esp32") -> bool:
    return _publish_command({
        "action": "reset_data",
        "device_id": device_id,
    })


def publish_unlock_command(device_id: str = "esp32", duration_ms: int = 5000) -> bool:
    if duration_ms < 1000:
        duration_ms = 1000
    if duration_ms > 15000:
        duration_ms = 15000

    return _publish_command({
        "action": "unlock_once",
        "device_id": device_id,
        "duration_ms": int(duration_ms),
    })

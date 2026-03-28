import json
import time
from uuid import uuid4

from paho.mqtt import publish

from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_COMMAND


def _publish_command(payload: dict, retries: int = 3, delay_s: float = 0.2) -> tuple[bool, str]:
    command_id = str(payload.get("command_id") or uuid4().hex)
    body = json.dumps({
        **payload,
        "command_id": command_id,
    })
    for i in range(retries):
        try:
            publish.single(
                MQTT_TOPIC_COMMAND,
                payload=body,
                hostname=MQTT_BROKER,
                port=MQTT_PORT,
                qos=1,
                retain=False,
            )
            return True, command_id
        except Exception as exc:
            if i >= retries - 1:
                print(f"[MQTT COMMAND] publish failed: {exc}")
                return False, command_id
            if delay_s > 0:
                time.sleep(delay_s)
    return False, command_id


def publish_reset_command(device_id: str = "esp32") -> tuple[bool, str]:
    return _publish_command({
        "action": "reset_data",
        "device_id": device_id,
    })


def publish_unlock_command(device_id: str = "esp32", duration_ms: int = 5000) -> tuple[bool, str]:
    if duration_ms < 1000:
        duration_ms = 1000
    if duration_ms > 15000:
        duration_ms = 15000

    return _publish_command({
        "action": "unlock_once",
        "device_id": device_id,
        "duration_ms": int(duration_ms),
    })


def publish_rfid_enroll_command(device_id: str = "esp32", enabled: bool = False) -> tuple[bool, str]:
    return _publish_command({
        "action": "rfid_enroll_mode",
        "device_id": device_id,
        "enabled": bool(enabled),
    })


def publish_dashboard_interval_command(device_id: str = "esp32", interval_sec: int = 5) -> tuple[bool, str]:
    try:
        safe_interval_sec = int(interval_sec)
    except Exception:
        safe_interval_sec = 5

    safe_interval_sec = max(1, min(10, safe_interval_sec))

    return _publish_command({
        "action": "set_dashboard_interval",
        "device_id": device_id,
        "interval_ms": safe_interval_sec * 1000,
    })

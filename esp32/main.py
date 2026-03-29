from machine import Pin
import time
import _thread
import os

from coins import CoinCounter
from display import init_display, render_status, show_boot_screen
from lock import init_lock
from rfid import init_rfid, read_card_uid
from auth import check_authorization
try:
    from rfid import recover_reader as _rfid_recover_reader
except ImportError:
    def _rfid_recover_reader(reader):
        try:
            reader.stop_crypto1()
        except Exception:
            pass
        try:
            if hasattr(reader, "hard_reset"):
                reader.hard_reset()
            if hasattr(reader, "init"):
                reader.init()
            return True
        except Exception:
            return False
from wifi import connect_wifi, reconnect_wifi, is_connected, ip_address
from mqtt_handler import MQTTHandler
from webserver import start_server
from config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    MQTT_BROKER,
    MQTT_TOPIC_PUBLISH,
    MQTT_TOPIC_SUBSCRIBE,
    BACKEND_HOST,
    BACKEND_PORT,
)

try:
    from ultrasonic import (
        UltrasonicSensor,
        is_full,
        estimate_coin_level,
        EMPTY_THRESHOLD_CM,
        FULL_THRESHOLD_CM,
    )
    HAS_ULTRASONIC = True
except ImportError:
    HAS_ULTRASONIC = False
except Exception as exc:
    print("[ULTRASONIC] module import failed:", exc)
    HAS_ULTRASONIC = False


# Timing config.
UNLOCK_TIME_MS = 5000
RFID_COOLDOWN_MS = 1200
RFID_POLL_INTERVAL_MS = 150  # poll RFID every 150ms; avoids hammering SPI bus
RFID_RECOVERY_IDLE_MS = 4000
# Keep scan mode under frontend control. Set to 0 to disable device-side auto-timeout.
RFID_ENROLL_TIMEOUT_MS = 0
DISPLAY_INTERVAL_MS = 500
DISPLAY_RECOVERY_RETRY_MS = 5000
ULTRASONIC_INTERVAL_MS = 800
DEFAULT_DASHBOARD_UPDATE_MS = 5000
WIFI_RECONNECT_INTERVAL_MS = 15000
WIFI_RECONNECT_TIMEOUT_S = 8
MQTT_RECOVERY_CHECK_MS = 1500
COIN_NOISE_GUARD_MS = 1200
COIN_ACTIVITY_RECONNECT_GRACE_MS = 2500
COMMAND_HISTORY_LIMIT = 24
BIN_EMPTY_DISTANCE_CM = 17.5
BIN_FULL_DISTANCE_CM = 4.9
BIN_MAX_COINS_EST = 400
AVG_COIN_VALUE_EST = 4.5
ULTRASONIC_EMA_ALPHA = 0.25

_last_display_recover_ms = 0

# Indicators.
LED_PIN = 18
BUZZER_PIN = 17


def pulse_output(pin, ms=40):
    pin.on()
    time.sleep_ms(ms)
    pin.off()


def deny_beep(buzzer):
    # Audible deny pattern: two longer beeps.
    for _ in range(2):
        pulse_output(buzzer, 140)
        time.sleep_ms(120)


def _recover_display():
    global _last_display_recover_ms

    now = time.ticks_ms()
    if time.ticks_diff(now, _last_display_recover_ms) < DISPLAY_RECOVERY_RETRY_MS:
        return None

    _last_display_recover_ms = now
    try:
        recovered = init_display()
        if recovered is not None:
            print("[DISPLAY] recovered")
        return recovered
    except Exception as exc:
        print("[DISPLAY RECOVERY FAILED]:", exc)
        return None


def _safe_render(oled, renderer, context):
    try:
        if oled is not None:
            renderer(oled)
            return oled
    except Exception as exc:
        print(f"[DISPLAY ERROR:{context}] {exc}")

    recovered = _recover_display()
    if recovered is None:
        return None

    try:
        renderer(recovered)
        return recovered
    except Exception as exc:
        print(f"[DISPLAY ERROR:{context}:recovered] {exc}")
        return None


def safe_show_boot_screen(oled, ip_text=None):
    def _render(target):
        try:
            show_boot_screen(target, ip_text=ip_text)
        except TypeError:
            show_boot_screen(target)

    return _safe_render(oled, _render, "boot")


def safe_render_status(oled, counts, total, is_full, estimated_total=None, fill_percent=None, ip_text=None):
    def _render(target):
        try:
            render_status(
                target,
                counts,
                total,
                is_full,
                estimated_total=estimated_total,
                fill_percent=fill_percent,
                ip_text=ip_text,
            )
        except TypeError:
            render_status(
                target,
                counts,
                total,
                is_full,
                estimated_total=estimated_total,
                fill_percent=fill_percent,
            )

    return _safe_render(oled, _render, "status")


def run():
    led = Pin(LED_PIN, Pin.OUT)
    buzzer = Pin(BUZZER_PIN, Pin.OUT)

    lock = init_lock()  # GPIO35 relay, active-low unlock via lock.py
    is_locked = True

    coins = CoinCounter(
        debounce_ms=120,
        startup_ignore_ms=2000,
    )
    reader = init_rfid()
    oled = init_display()
    device_ip = None
    enroll_mode = False
    enroll_started_ms = None
    dashboard_update_ms = DEFAULT_DASHBOARD_UPDATE_MS
    wifi_was_connected = False
    server_started = False
    recent_command_ids = []

    def has_seen_command(command_id):
        if not command_id:
            return False
        return command_id in recent_command_ids

    def remember_command(command_id):
        if not command_id:
            return
        if command_id in recent_command_ids:
            return
        recent_command_ids.append(command_id)
        if len(recent_command_ids) > COMMAND_HISTORY_LIMIT:
            recent_command_ids.pop(0)

    # ===== WEB STATUS FUNCTION =====
    def current_payload(heartbeat_reason="HEARTBEAT", rfid_scan_uid=None, rfid_scan_source=None, command_id=None):
        payload = {
            "coins": coins.snapshot(),
            "total": coins.total(),
            "distance_cm": distance_cm,
            "is_full": full_flag,
            "is_locked": is_locked,
            "wifi_connected": is_connected(wlan),
            "estimated_total": estimated_total,
            "estimated_coin_count": estimated_coin_count,
            "fill_percent": fill_percent,
            "wifi_ssid": WIFI_SSID,
            "esp32_ip": device_ip,
            "dashboard_update_ms": dashboard_update_ms,
            "heartbeat_reason": heartbeat_reason,
        }
        if rfid_scan_uid is not None:
            payload["rfid_scan_uid"] = str(rfid_scan_uid)
        if rfid_scan_source is not None:
            payload["rfid_scan_source"] = rfid_scan_source
        if command_id:
            payload["command_id"] = command_id
        return payload

    def get_status():
        return current_payload()


    oled = safe_show_boot_screen(oled, ip_text=device_ip)

    sensor = None
    distance_cm = None
    full_flag = False
    estimated_coin_count = None
    estimated_total = None
    fill_percent = None
    if HAS_ULTRASONIC:
        try:
            sensor = UltrasonicSensor()
            print("Ultrasonic: enabled")
        except Exception as exc:
            print("Ultrasonic init failed:", exc)
            sensor = None

    wlan = None
    if WIFI_SSID and WIFI_PASSWORD:
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        device_ip = ip_address(wlan)
        print("WiFi connected:", is_connected(wlan), "IP:", device_ip)
        oled = safe_show_boot_screen(oled, ip_text=device_ip)
        # start server
        _thread.start_new_thread(start_server, (get_status,))
        server_started = True
    else:
        print("WiFi: skipped (set WIFI_SSID/WIFI_PASSWORD in main.py)")

    # Initialize MQTT
    mqtt = MQTTHandler(
        broker=MQTT_BROKER,
        topic_publish=MQTT_TOPIC_PUBLISH,
        topic_subscribe=MQTT_TOPIC_SUBSCRIBE,
        client_id="piggybank_esp32"
    )

    def on_mqtt_command(topic, payload):
        nonlocal enroll_mode, enroll_started_ms, is_locked, unlock_started_ms, dashboard_update_ms
        try:
            action = None
            command_id = None
            if isinstance(payload, dict):
                action = payload.get("action") or payload.get("cmd")
                command_id = payload.get("command_id")

            if has_seen_command(command_id):
                print("[MQTT CMD] duplicate ignored:", action, command_id)
                return

            if action == "reset_data":
                coins.reset()
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                lock.lock()
                is_locked = True
                unlock_started_ms = None

                remember_command(command_id)
                mqtt.publish(current_payload(heartbeat_reason="RESET", command_id=command_id))
                print("[RESET] Data reset command applied on board")

            elif action == "unlock_once":
                now = time.ticks_ms()
                duration_ms = UNLOCK_TIME_MS
                if isinstance(payload, dict):
                    try:
                        duration_ms = int(payload.get("duration_ms", UNLOCK_TIME_MS))
                    except Exception:
                        duration_ms = UNLOCK_TIME_MS
                if duration_ms < 1000:
                    duration_ms = 1000
                if duration_ms > 15000:
                    duration_ms = 15000

                lock.unlock()
                is_locked = False
                unlock_started_ms = time.ticks_add(now, - (UNLOCK_TIME_MS - duration_ms))
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                pulse_output(led)
                pulse_output(buzzer)

                remember_command(command_id)
                mqtt.publish(current_payload(heartbeat_reason="WEB_UNLOCK", command_id=command_id))
                print("[UNLOCK] Unlock command applied from web")

            elif action == "rfid_enroll_mode":
                enabled = False
                if isinstance(payload, dict):
                    enabled = bool(payload.get("enabled", False))

                enroll_mode = enabled
                enroll_started_ms = time.ticks_ms() if enabled and RFID_ENROLL_TIMEOUT_MS > 0 else None
                lock.lock()
                is_locked = True
                unlock_started_ms = None
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                remember_command(command_id)
                mqtt.publish(current_payload(
                    heartbeat_reason="ENROLL_MODE_ON" if enabled else "ENROLL_MODE_OFF",
                    command_id=command_id,
                ))
                print("[RFID ENROLL MODE]", "enabled" if enabled else "disabled")

            elif action == "set_dashboard_interval":
                requested_ms = DEFAULT_DASHBOARD_UPDATE_MS
                if isinstance(payload, dict):
                    try:
                        requested_ms = int(payload.get("interval_ms", DEFAULT_DASHBOARD_UPDATE_MS))
                    except Exception:
                        requested_ms = DEFAULT_DASHBOARD_UPDATE_MS

                dashboard_update_ms = max(1000, min(10000, requested_ms))
                remember_command(command_id)
                mqtt.publish(current_payload(heartbeat_reason="INTERVAL_UPDATED", command_id=command_id))
                print("[DASHBOARD INTERVAL]", dashboard_update_ms, "ms")
        except Exception as exc:
            print(f"[MQTT CMD ERROR] {exc}")

    mqtt.set_message_handler(on_mqtt_command)
    mqtt.connect()


    unlock_started_ms = None
    last_card_ms = 0
    last_rfid_ms = 0
    last_rfid_ok_ms = time.ticks_ms()
    last_rfid_recover_ms = 0
    last_display_ms = 0
    last_ultrasonic_ms = 0
    last_mqtt_publish_ms = 0
    last_wifi_retry_ms = 0
    last_mqtt_recover_ms = 0

    print("System Ready")
    oled = safe_render_status(oled, coins.snapshot(), coins.total(), full_flag, ip_text=device_ip)
    


    while True:
        now = time.ticks_ms()
        wifi_status = is_connected(wlan)

        coin_busy = coins.recent_signal(COIN_ACTIVITY_RECONNECT_GRACE_MS)

        if WIFI_SSID and WIFI_PASSWORD and not wifi_status:
            mqtt.mark_disconnected("wifi offline")
            device_ip = None
            if time.ticks_diff(now, last_wifi_retry_ms) >= WIFI_RECONNECT_INTERVAL_MS:
                if coin_busy:
                    pass
                else:
                    last_wifi_retry_ms = now
                    print("[WIFI] reconnect attempt")
                    wlan = reconnect_wifi(
                        wlan,
                        WIFI_SSID,
                        WIFI_PASSWORD,
                        timeout_s=WIFI_RECONNECT_TIMEOUT_S,
                        blocking=False,
                    )
                    wifi_status = is_connected(wlan)
                    device_ip = ip_address(wlan)
                    print("[WIFI] connected:", wifi_status, "IP:", device_ip)
                    if wifi_status and not server_started:
                        _thread.start_new_thread(start_server, (get_status,))
                        server_started = True
                        print("[WEB] status server started after reconnect")

        if wifi_status and not wifi_was_connected and not coin_busy:
            print("[WIFI] link restored")
            if mqtt.ensure_connected(force=True):
                mqtt.publish(current_payload(heartbeat_reason="WIFI_RECONNECTED"))

        if wifi_status and not coin_busy and time.ticks_diff(now, last_mqtt_recover_ms) >= MQTT_RECOVERY_CHECK_MS:
            last_mqtt_recover_ms = now
            if not mqtt.connected:
                if mqtt.ensure_connected():
                    mqtt.publish(current_payload(heartbeat_reason="MQTT_RECONNECTED"))

        wifi_was_connected = wifi_status

        if time.ticks_diff(now, last_rfid_ms) >= RFID_POLL_INTERVAL_MS:
            last_rfid_ms = now
            try:
                uid = read_card_uid(reader)
                if uid is not None and time.ticks_diff(now, last_card_ms) >= RFID_COOLDOWN_MS:
                    last_card_ms = now
                    last_rfid_ok_ms = now
                    coins.suppress_for(COIN_NOISE_GUARD_MS)

                    if enroll_mode:
                        print(f"[ENROLL] Card UID captured: {uid}")
                        pulse_output(led, 80)
                        time.sleep_ms(60)
                        pulse_output(led, 80)
                        if RFID_ENROLL_TIMEOUT_MS > 0:
                            enroll_started_ms = now
                        mqtt.publish(
                            current_payload(
                                heartbeat_reason="RFID_ENROLL_SCAN",
                                rfid_scan_uid=uid,
                                rfid_scan_source="esp32_enroll",
                            )
                        )
                        continue

                    # RFID card detected - authorize first, then unlock only if allowed.
                    auth_result = {
                        "authorized": False,
                        "access_granted": False,
                        "reason": "NO_AUTH_CHECK",
                        "error": None,
                    }

                    if wifi_status:
                        auth_result = check_authorization(
                            BACKEND_HOST,
                            BACKEND_PORT,
                            uid,
                            wifi_status,
                            timeout_s=2
                        )
                    else:
                        auth_result = {
                            "authorized": False,
                            "access_granted": False,
                            "reason": "WIFI_DISCONNECTED",
                            "error": "wifi disconnected",
                        }

                    if auth_result.get("access_granted", False):
                        lock.unlock()
                        is_locked = False
                        unlock_started_ms = now
                        print(f"[UNLOCK] Card UID: {uid}")
                        pulse_output(led)
                        pulse_output(buzzer)
                    else:
                        print(f"[DENY] Card UID: {uid} reason={auth_result.get('reason')}")
                        deny_beep(buzzer)

                    print(f"[AUTH-LOG] Result: {auth_result}")
            except Exception as exc:
                print("[RFID ERROR]:", exc)
                if time.ticks_diff(now, last_rfid_recover_ms) >= 2000:
                    if _rfid_recover_reader(reader):
                        print("[RFID] recovered after error")
                    last_rfid_recover_ms = now

        if wifi_status:
            mqtt.check_message()

        if RFID_ENROLL_TIMEOUT_MS > 0 and enroll_mode and enroll_started_ms is not None:
            if time.ticks_diff(now, enroll_started_ms) >= RFID_ENROLL_TIMEOUT_MS:
                enroll_mode = False
                enroll_started_ms = None
                lock.lock()
                is_locked = True
                unlock_started_ms = None
                mqtt.publish(current_payload(heartbeat_reason="ENROLL_MODE_TIMEOUT"))
                print("[RFID ENROLL MODE] timeout -> disabled")

        if time.ticks_diff(now, last_rfid_ok_ms) >= RFID_RECOVERY_IDLE_MS:
            if time.ticks_diff(now, last_rfid_recover_ms) >= 2000:
                if _rfid_recover_reader(reader):
                    print("[RFID] periodic recovery")
                last_rfid_recover_ms = now
            last_rfid_ok_ms = now

        if not is_locked and unlock_started_ms is not None:
            elapsed = time.ticks_diff(now, unlock_started_ms)
            if elapsed >= UNLOCK_TIME_MS:
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                lock.lock()
                is_locked = True
                unlock_started_ms = None
                print("[AUTO LOCK] After", elapsed, "ms")
                pulse_output(led)

        new_events = coins.consume_new_events()
        if new_events > 0:
            counts = coins.snapshot()
            total = coins.total()
            print("Coins:", counts, "total:", total)
            pulse_output(led)
            pulse_output(buzzer)

        if sensor is not None and time.ticks_diff(now, last_ultrasonic_ms) >= ULTRASONIC_INTERVAL_MS:
            last_ultrasonic_ms = now
            raw_distance_cm = sensor.measure_distance_cm(samples=8)
            if raw_distance_cm is not None:
                if distance_cm is None:
                    distance_cm = raw_distance_cm
                else:
                    distance_cm = distance_cm + (ULTRASONIC_EMA_ALPHA * (raw_distance_cm - distance_cm))
            full_flag = is_full(distance_cm)
            estimate = estimate_coin_level(
                distance_cm,
                max_coins=BIN_MAX_COINS_EST,
                avg_coin_value=AVG_COIN_VALUE_EST,
                empty_cm=BIN_EMPTY_DISTANCE_CM,
                full_cm=BIN_FULL_DISTANCE_CM,
            )
            estimated_coin_count = estimate["estimated_coin_count"]
            estimated_total = estimate["estimated_total"]
            fill_percent = estimate["fill_percent"]

        if time.ticks_diff(now, last_display_ms) >= DISPLAY_INTERVAL_MS:
            last_display_ms = now
            oled = safe_render_status(
                oled,
                coins.snapshot(),
                coins.total(),
                full_flag,
                estimated_total=estimated_total,
                fill_percent=fill_percent,
                ip_text=device_ip,
            )

        # Check WiFi status and update device_ip
        if wlan is not None:
            device_ip = ip_address(wlan)

        # Publish to MQTT using the current dashboard update interval.
        if wifi_status and time.ticks_diff(now, last_mqtt_publish_ms) >= dashboard_update_ms:
            last_mqtt_publish_ms = now
            payload = current_payload(heartbeat_reason="PERIODIC")
            sent = mqtt.publish(payload)
            if not sent:
                print("MQTT: publish failed")

        time.sleep_ms(20)


def _safe_mode_enabled():
    try:
        return "NO_AUTORUN" in os.listdir()
    except Exception:
        return False


if _safe_mode_enabled():
    print("[SAFE MODE] NO_AUTORUN found -> skip run()")
else:
    print("[BOOT] Starting in 5s (Ctrl+C to stay in REPL)")
    try:
        for _ in range(50):
            time.sleep_ms(100)
        run()
    except KeyboardInterrupt:
        print("[BOOT] Interrupted before run()")

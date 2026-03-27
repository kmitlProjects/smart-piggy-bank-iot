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
from wifi import connect_wifi, is_connected, ip_address
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
RFID_ENROLL_TIMEOUT_MS = 30000
DISPLAY_INTERVAL_MS = 500
ULTRASONIC_INTERVAL_MS = 800
DEFAULT_DASHBOARD_UPDATE_MS = 5000
COIN_NOISE_GUARD_MS = 300
BIN_EMPTY_DISTANCE_CM = 17.5
BIN_FULL_DISTANCE_CM = 4.9
BIN_MAX_COINS_EST = 400
AVG_COIN_VALUE_EST = 4.5
ULTRASONIC_EMA_ALPHA = 0.25

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


def safe_show_boot_screen(oled, ip_text=None):
    try:
        show_boot_screen(oled, ip_text=ip_text)
    except TypeError:
        show_boot_screen(oled)


def safe_render_status(oled, counts, total, is_full, estimated_total=None, fill_percent=None, ip_text=None):
    try:
        render_status(
            oled,
            counts,
            total,
            is_full,
            estimated_total=estimated_total,
            fill_percent=fill_percent,
            ip_text=ip_text,
        )
    except TypeError:
        render_status(
            oled,
            counts,
            total,
            is_full,
            estimated_total=estimated_total,
            fill_percent=fill_percent,
        )


def run():
    led = Pin(LED_PIN, Pin.OUT)
    buzzer = Pin(BUZZER_PIN, Pin.OUT)

    lock = init_lock()  # GPIO35 relay, active-low unlock via lock.py
    is_locked = True

    coins = CoinCounter()
    reader = init_rfid()
    oled = init_display()
    device_ip = None
    enroll_mode = False
    enroll_started_ms = None
    dashboard_update_ms = DEFAULT_DASHBOARD_UPDATE_MS

    # ===== WEB STATUS FUNCTION =====
    def current_payload(heartbeat_reason="HEARTBEAT", rfid_scan_uid=None, rfid_scan_source=None):
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
        return payload

    def get_status():
        return current_payload()


    safe_show_boot_screen(oled, ip_text=device_ip)

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
        safe_show_boot_screen(oled, ip_text=device_ip)
        # start server
        _thread.start_new_thread(start_server, (get_status,))
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
            if isinstance(payload, dict):
                action = payload.get("action") or payload.get("cmd")

            if action == "reset_data":
                coins.reset()
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                lock.lock()
                is_locked = True
                unlock_started_ms = None

                mqtt.publish(current_payload(heartbeat_reason="RESET"))
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

                mqtt.publish(current_payload(heartbeat_reason="WEB_UNLOCK"))
                print("[UNLOCK] Unlock command applied from web")

            elif action == "rfid_enroll_mode":
                enabled = False
                if isinstance(payload, dict):
                    enabled = bool(payload.get("enabled", False))

                enroll_mode = enabled
                enroll_started_ms = time.ticks_ms() if enabled else None
                lock.lock()
                is_locked = True
                unlock_started_ms = None
                coins.suppress_for(COIN_NOISE_GUARD_MS)
                mqtt.publish(current_payload(heartbeat_reason="ENROLL_MODE_ON" if enabled else "ENROLL_MODE_OFF"))
                print("[RFID ENROLL MODE]", "enabled" if enabled else "disabled")

            elif action == "set_dashboard_interval":
                requested_ms = DEFAULT_DASHBOARD_UPDATE_MS
                if isinstance(payload, dict):
                    try:
                        requested_ms = int(payload.get("interval_ms", DEFAULT_DASHBOARD_UPDATE_MS))
                    except Exception:
                        requested_ms = DEFAULT_DASHBOARD_UPDATE_MS

                dashboard_update_ms = max(1000, min(10000, requested_ms))
                mqtt.publish(current_payload(heartbeat_reason="INTERVAL_UPDATED"))
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

    print("System Ready")
    safe_render_status(oled, coins.snapshot(), coins.total(), full_flag, ip_text=device_ip)
    


    while True:
        now = time.ticks_ms()

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
                        mqtt.publish(
                            current_payload(
                                heartbeat_reason="RFID_ENROLL_SCAN",
                                rfid_scan_uid=uid,
                                rfid_scan_source="esp32_enroll",
                            )
                        )
                        # Keep enroll mode one-shot on the device so a lost
                        # "disable enroll mode" command cannot leave the board
                        # stuck in scan-only behavior.
                        enroll_mode = False
                        enroll_started_ms = None
                        mqtt.publish(current_payload(heartbeat_reason="ENROLL_MODE_AUTO_OFF"))
                        continue

                    # RFID card detected - authorize first, then unlock only if allowed.
                    wifi_status = is_connected(wlan)

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

        mqtt.check_message()

        if enroll_mode and enroll_started_ms is not None:
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
            safe_render_status(
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
        if time.ticks_diff(now, last_mqtt_publish_ms) >= dashboard_update_ms:
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

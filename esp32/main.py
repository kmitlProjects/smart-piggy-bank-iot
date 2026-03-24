from machine import Pin
import time
import _thread

from coins import CoinCounter
from display import init_display, render_status, show_boot_screen
from lock import init_lock
from rfid import init_rfid, read_card_uid
from wifi import connect_wifi, is_connected, ip_address
from mqtt_handler import MQTTHandler
from webserver import start_server

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


# Optional network config.
WIFI_SSID = "Galaxy A52 5GD9C0"
WIFI_PASSWORD = "neae4850"

# MQTT Config (HiveMQ Cloud)
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC_PUBLISH = "piggybank/data"
MQTT_TOPIC_SUBSCRIBE = "piggybank/command"

# Timing config.
UNLOCK_TIME_MS = 5000
RFID_COOLDOWN_MS = 1200
RFID_POLL_INTERVAL_MS = 150  # poll RFID every 150ms; avoids hammering SPI bus
DISPLAY_INTERVAL_MS = 500
ULTRASONIC_INTERVAL_MS = 800
DASHBOARD_UPDATE_MS = 5000
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

    # ===== WEB STATUS FUNCTION =====
    def get_status():
        return {
            "coins": coins.snapshot(),
            "total": coins.total(),
            "distance_cm": distance_cm,
            "is_full": full_flag,
            "is_locked": is_locked,
            "wifi_connected": is_connected(wlan),
            "estimated_total": estimated_total,
            "estimated_coin_count": estimated_coin_count,
            "fill_percent": fill_percent,
        }


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
    mqtt.connect()


    unlock_started_ms = None
    last_card_ms = 0
    last_rfid_ms = 0
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
                    coins.suppress_for(COIN_NOISE_GUARD_MS)
                    lock.unlock()
                    is_locked = False
                    unlock_started_ms = now
                    print("[UNLOCK] Card UID:", uid)
                    pulse_output(led)
                    pulse_output(buzzer)
            except Exception as exc:
                print("[RFID ERROR]:", exc)

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

        # Publish to MQTT every DASHBOARD_UPDATE_MS
        if time.ticks_diff(now, last_mqtt_publish_ms) >= DASHBOARD_UPDATE_MS:
            last_mqtt_publish_ms = now
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
            }
            sent = mqtt.publish(payload)
            if sent:
                print("MQTT: published")
            else:
                print("MQTT: publish failed")

        time.sleep_ms(20)


run()

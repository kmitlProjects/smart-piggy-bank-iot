import network
import time


def connect_wifi(ssid, password, timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    print("Connecting to:", ssid)

    wlan.connect(ssid, password)
    start = time.ticks_ms()

    while not wlan.isconnected():
        print("Waiting...")
        if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
            print("Timeout!")
            break
        time.sleep_ms(500)

    print("Result:", wlan.ifconfig())
    return wlan


def is_connected(wlan):
    return wlan is not None and wlan.isconnected()


def ip_address(wlan):
    if not is_connected(wlan):
        return None
    return wlan.ifconfig()[0]

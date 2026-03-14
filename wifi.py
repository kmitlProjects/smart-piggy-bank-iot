import network
import time


def connect_wifi(ssid, password, timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)
    start = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
            break
        time.sleep_ms(250)

    return wlan


def is_connected(wlan):
    return wlan is not None and wlan.isconnected()


def ip_address(wlan):
    if not is_connected(wlan):
        return None
    return wlan.ifconfig()[0]

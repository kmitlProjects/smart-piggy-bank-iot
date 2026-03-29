import network
import time


def connect_wifi(ssid, password, timeout_s=15, wlan=None, blocking=True, force_restart=True):
    wlan = wlan or network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    print("Connecting to:", ssid)

    if force_restart:
        try:
            wlan.disconnect()
            time.sleep_ms(200)
        except Exception:
            pass

    try:
        wlan.connect(ssid, password)
    except Exception as exc:
        print("Connect start failed:", exc)
        return wlan

    if not blocking:
        return wlan

    start = time.ticks_ms()

    while not wlan.isconnected():
        print("Waiting...")
        if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
            print("Timeout!")
            break
        time.sleep_ms(500)

    print("Result:", wlan.ifconfig())
    return wlan


def reconnect_wifi(wlan, ssid, password, timeout_s=10, blocking=False):
    if not ssid or not password:
        return wlan
    return connect_wifi(
        ssid,
        password,
        timeout_s=timeout_s,
        wlan=wlan,
        blocking=blocking,
        force_restart=True,
    )


def is_connected(wlan):
    return wlan is not None and wlan.isconnected()


def ip_address(wlan):
    if not is_connected(wlan):
        return None
    return wlan.ifconfig()[0]

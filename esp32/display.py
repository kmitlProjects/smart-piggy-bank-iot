from machine import Pin, I2C

# Libraries are expected under /lib in MicroPython.
try:
    import ssd1306
except ImportError:
    import sys

    if "lib" not in sys.path:
        sys.path.append("lib")
    import ssd1306

SDA_PIN = 8
SCL_PIN = 9
I2C_FREQ = 400000
MAX_TEXT_CHARS = 16  # 128px / 8px default font
SCROLL_GAP = "   "

_scroll_state = {
    "text": None,
    "index": 0,
}


def init_display(width=128, height=64):
    i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=I2C_FREQ)
    addrs = i2c.scan()
    print("I2C scan:", addrs)

    if 0x3C in addrs:
        oled_addr = 0x3C
    elif 0x3D in addrs:
        oled_addr = 0x3D
    else:
        print("OLED not found at 0x3C/0x3D")
        return None

    return ssd1306.SSD1306_I2C(width, height, i2c, addr=oled_addr)


def _draw_bottom_text(oled, text, y=56):
    if text is None:
        text = ""
    text = str(text)

    if len(text) <= MAX_TEXT_CHARS:
        _scroll_state["text"] = text
        _scroll_state["index"] = 0
        oled.text(text, 0, y)
        return

    if _scroll_state["text"] != text:
        _scroll_state["text"] = text
        _scroll_state["index"] = 0

    loop_text = text + SCROLL_GAP + text
    idx = _scroll_state["index"]
    window = loop_text[idx:idx + MAX_TEXT_CHARS]
    if len(window) < MAX_TEXT_CHARS:
        window = window + loop_text[: MAX_TEXT_CHARS - len(window)]

    oled.text(window, 0, y)
    _scroll_state["index"] = (idx + 1) % (len(text) + len(SCROLL_GAP))


def render_status(oled, counts, total, is_full, estimated_total=None, fill_percent=None, ip_text=None):
    if oled is None:
        return

    c1 = counts.get("1", 0)
    c2 = counts.get("2", 0)
    c5 = counts.get("5", 0)
    c10 = counts.get("10", 0)

    oled.fill(0)
    oled.text("1=" + str(c1), 0, 0)
    oled.text("2=" + str(c2), 64, 0)
    oled.text("5=" + str(c5), 0, 16)
    oled.text("10=" + str(c10), 64, 16)
    oled.text("T=" + str(total), 0, 34)

    if fill_percent is None:
        oled.text("F=--%", 64, 34)
    else:
        oled.text("F=" + str(fill_percent) + "%", 64, 34)

    if ip_text is None or ip_text == "":
        bottom_text = "WiFi Lost"
    else:
        bottom_text = str(ip_text)

    _draw_bottom_text(oled, bottom_text, y=56)

    if is_full:
        oled.text("!", 120, 34)
    oled.show()


def show_boot_screen(oled, ip_text=None):
    if oled is None:
        return

    oled.fill(0)
    oled.text("Smart Piggy Bank", 0, 0)
    oled.text("System Ready", 0, 20)
    if ip_text is None or ip_text == "":
        bottom_text = "WiFi Lost"
    else:
        bottom_text = str(ip_text)
    _draw_bottom_text(oled, bottom_text, y=56)
    oled.show()

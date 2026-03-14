from machine import Pin, SPI

# Library loader for local VS Code + MicroPython board runtime.
def _load_mfrc522_class():
    import sys

    if "lib" not in sys.path:
        sys.path.append("lib")

    try:
        module = __import__("mfrc522")
    except ImportError:
        raise ImportError(
            "Cannot find mfrc522.py. Put it in project root or lib/mfrc522.py"
        )

    return module.MFRC522


MFRC522 = _load_mfrc522_class()

SCK_PIN = 12
MOSI_PIN = 11
MISO_PIN = 13
SS_PIN = 10
RST_PIN = 14


def init_rfid():
    spi = SPI(
        1,
        baudrate=1_000_000,
        polarity=0,
        phase=0,
        sck=Pin(SCK_PIN),
        mosi=Pin(MOSI_PIN),
        miso=Pin(MISO_PIN),
    )

    return MFRC522(
        spi,
        Pin(SS_PIN, Pin.OUT),
        Pin(RST_PIN, Pin.OUT),
    )


def is_card_present(reader):
    status, _ = reader.request(reader.REQIDL)
    return status == reader.OK


def read_card_uid(reader):
    if not is_card_present(reader):
        return None

    status, uid = reader.anticoll()
    if status != reader.OK:
        return None

    return uid

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


def recover_reader(reader):
    ok = False

    try:
        reader.stop_crypto1()
        ok = True
    except Exception:
        pass

    try:
        if hasattr(reader, "hard_reset"):
            reader.hard_reset()
        if hasattr(reader, "init"):
            reader.init()
        ok = True
    except Exception:
        pass

    return ok


def is_card_present(reader):
    # REQALL (WUPA, 0x52) wakes cards in both IDLE and HALT state.
    # REQIDL (REQA, 0x26) only wakes IDLE cards, which misses cards that
    # were already halt()-ed by a previous read.
    try:
        try:
            reader.stop_crypto1()
        except Exception:
            pass
        status, _ = reader.request(reader.REQALL)
        return status == reader.OK
    except Exception:
        return False


def read_card_uid(reader):
    if not is_card_present(reader):
        return None

    try:
        status, uid = reader.anticoll()
        if status != reader.OK:
            return None

        reader.select_tag(uid)
        # Don't halt - just stop crypto to allow next detection cycle
        reader.stop_crypto1()
        return uid
    except Exception as exc:
        print("RFID read error:", exc)
        recover_reader(reader)
        return None

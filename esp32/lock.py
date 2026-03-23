from machine import Pin
import time

# Solenoid lock is driven through a relay on GPIO35.
RELAY_PIN = 35
RELAY_UNLOCK_LEVEL = 1  # HIGH = unlock
RELAY_LOCK_LEVEL = 0    # LOW = lock


class SolenoidLock:
    def __init__(self, pin=RELAY_PIN):
        # Set output level at init to reduce startup glitches.
        self.relay = Pin(pin, Pin.OUT, value=RELAY_LOCK_LEVEL)
        self._is_locked = True

    def unlock(self):
        try:
            self.relay.value(RELAY_UNLOCK_LEVEL)
            self._is_locked = False
            print("[RELAY] Unlock signal sent (GPIO35=HIGH)")
            time.sleep_ms(50)  # Stabilize relay
        except Exception as exc:
            print("[RELAY ERROR] unlock failed:", exc)

    def lock(self):
        try:
            self.relay.value(RELAY_LOCK_LEVEL)
            self._is_locked = True
            print("[RELAY] Lock signal sent (GPIO35=LOW)")
            time.sleep_ms(50)  # Stabilize relay
        except Exception as exc:
            print("[RELAY ERROR] lock failed:", exc)

    def is_locked(self):
        return self._is_locked


def init_lock():
    return SolenoidLock()

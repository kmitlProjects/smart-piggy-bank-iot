from machine import Pin

# Solenoid lock is driven through a relay on GPIO35.
RELAY_PIN = 35
RELAY_UNLOCK_LEVEL = 1  # HIGH = unlock
RELAY_LOCK_LEVEL = 0    # LOW = lock


class SolenoidLock:
    def __init__(self, pin=RELAY_PIN):
        # Set output level at init to reduce startup glitches.
        self.relay = Pin(pin, Pin.OUT, value=RELAY_LOCK_LEVEL)

    def unlock(self):
        self.relay.value(RELAY_UNLOCK_LEVEL)

    def lock(self):
        self.relay.value(RELAY_LOCK_LEVEL)


def init_lock():
    return SolenoidLock()

from machine import Pin
import time

COIN_PINS = {
    "1": 21,
    "2": 38,
    "5": 39,
    "10": 40,
}

COIN_VALUES = {
    "1": 1,
    "2": 2,
    "5": 5,
    "10": 10,
}


class CoinCounter:
    def __init__(self, pin_map=None, debounce_ms=120):
        self.pin_map = pin_map or COIN_PINS
        self.debounce_ms = debounce_ms

        self.counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._last_ms = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._new_events = 0
        self._ignore_until_ms = 0

        self._pins = {
            k: Pin(v, Pin.IN, Pin.PULL_UP)
            for k, v in self.pin_map.items()
        }

        self._pins["1"].irq(trigger=Pin.IRQ_FALLING, handler=self._irq_1)
        self._pins["2"].irq(trigger=Pin.IRQ_FALLING, handler=self._irq_2)
        self._pins["5"].irq(trigger=Pin.IRQ_FALLING, handler=self._irq_5)
        self._pins["10"].irq(trigger=Pin.IRQ_FALLING, handler=self._irq_10)

    def _handle_coin(self, coin_key):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._ignore_until_ms) < 0:
            return

        dt = time.ticks_diff(now, self._last_ms[coin_key])
        if dt < self.debounce_ms:
            return

        self._last_ms[coin_key] = now
        self.counts[coin_key] += 1
        self._new_events += 1

    def _irq_1(self, _pin):
        self._handle_coin("1")

    def _irq_2(self, _pin):
        self._handle_coin("2")

    def _irq_5(self, _pin):
        self._handle_coin("5")

    def _irq_10(self, _pin):
        self._handle_coin("10")

    def consume_new_events(self):
        value = self._new_events
        self._new_events = 0
        return value

    def suppress_for(self, duration_ms):
        now = time.ticks_ms()
        self._ignore_until_ms = time.ticks_add(now, duration_ms)
        self._new_events = 0

    def snapshot(self):
        return {
            "1": self.counts["1"],
            "2": self.counts["2"],
            "5": self.counts["5"],
            "10": self.counts["10"],
        }

    def total(self):
        counts = self.counts
        return (
            counts["1"] * COIN_VALUES["1"]
            + counts["2"] * COIN_VALUES["2"]
            + counts["5"] * COIN_VALUES["5"]
            + counts["10"] * COIN_VALUES["10"]
        )

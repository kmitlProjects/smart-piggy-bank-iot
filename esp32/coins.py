from machine import Pin
import time
try:
    import ujson as json
except ImportError:
    import json

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
    def __init__(
        self,
        pin_map=None,
        debounce_ms=160,
        min_pulse_ms=8,
        max_pulse_ms=1200,
        startup_ignore_ms=2000,
        state_path="/coin_state.json",
    ):
        self.pin_map = pin_map or COIN_PINS
        self.debounce_ms = debounce_ms
        self.min_pulse_ms = min_pulse_ms
        self.max_pulse_ms = max_pulse_ms
        self.state_path = state_path

        self.counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._pending_counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._last_ms = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._low_started_ms = {"1": None, "2": None, "5": None, "10": None}
        self._ignore_until_ms = time.ticks_add(time.ticks_ms(), startup_ignore_ms)

        self._pins = {
            k: Pin(v, Pin.IN, Pin.PULL_UP)
            for k, v in self.pin_map.items()
        }

        edge_trigger = Pin.IRQ_FALLING | Pin.IRQ_RISING
        self._pins["1"].irq(trigger=edge_trigger, handler=self._irq_1)
        self._pins["2"].irq(trigger=edge_trigger, handler=self._irq_2)
        self._pins["5"].irq(trigger=edge_trigger, handler=self._irq_5)
        self._pins["10"].irq(trigger=edge_trigger, handler=self._irq_10)
        self._load_state()

    def _load_state(self):
        try:
            with open(self.state_path, "r") as f:
                data = json.loads(f.read())
            for k in ("1", "2", "5", "10"):
                self.counts[k] = int(data.get(k, 0))
            print("[COINS] state restored:", self.counts)
        except OSError:
            # File doesn't exist yet on first boot.
            pass
        except Exception as exc:
            print("[COINS] state load failed:", exc)

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                f.write(json.dumps(self.snapshot()))
        except Exception as exc:
            print("[COINS] state save failed:", exc)

    def _handle_coin(self, coin_key):
        now = time.ticks_ms()
        pin_value = self._pins[coin_key].value()

        if pin_value == 0:
            if time.ticks_diff(now, self._ignore_until_ms) < 0:
                self._low_started_ms[coin_key] = None
                return
            self._low_started_ms[coin_key] = now
            return

        low_started_ms = self._low_started_ms[coin_key]
        self._low_started_ms[coin_key] = None
        if low_started_ms is None:
            return

        if time.ticks_diff(now, self._ignore_until_ms) < 0:
            return

        pulse_ms = time.ticks_diff(now, low_started_ms)
        if pulse_ms < self.min_pulse_ms or pulse_ms > self.max_pulse_ms:
            return

        dt = time.ticks_diff(now, self._last_ms[coin_key])
        if dt < self.debounce_ms:
            return

        self._last_ms[coin_key] = now
        self._pending_counts[coin_key] += 1

    def _irq_1(self, _pin):
        self._handle_coin("1")

    def _irq_2(self, _pin):
        self._handle_coin("2")

    def _irq_5(self, _pin):
        self._handle_coin("5")

    def _irq_10(self, _pin):
        self._handle_coin("10")

    def consume_new_events(self):
        applied = 0
        for coin_key in ("1", "2", "5", "10"):
            pending = self._pending_counts[coin_key]
            if pending <= 0:
                continue
            self.counts[coin_key] += pending
            applied += pending
            self._pending_counts[coin_key] = 0

        if applied > 0:
            self._save_state()
        return applied

    def suppress_for(self, duration_ms):
        now = time.ticks_ms()
        self._ignore_until_ms = time.ticks_add(now, duration_ms)
        self._pending_counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._low_started_ms = {"1": None, "2": None, "5": None, "10": None}

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

    def reset(self):
        self.counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._pending_counts = {"1": 0, "2": 0, "5": 0, "10": 0}
        self._low_started_ms = {"1": None, "2": None, "5": None, "10": None}
        self._save_state()

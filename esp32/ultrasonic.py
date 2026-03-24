from machine import Pin, time_pulse_us
import time

TRIG_PIN = 41
ECHO_PIN = 42
FULL_THRESHOLD_CM = 4.9
EMPTY_THRESHOLD_CM = 17.5
EMPTY_DEADBAND_CM = 0.8
FULL_DEADBAND_CM = 0.2
FILL_CURVE_GAMMA = 1.35


class UltrasonicSensor:
    def __init__(self, trig_pin=TRIG_PIN, echo_pin=ECHO_PIN):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.trig.value(0)

    def measure_distance_cm(self, timeout_us=30000, samples=2):
        values = []
        for _ in range(samples):
            self.trig.value(0)
            time.sleep_us(2)
            self.trig.value(1)
            time.sleep_us(10)
            self.trig.value(0)

            try:
                pulse = time_pulse_us(self.echo, 1, timeout_us)
            except OSError:
                pulse = -1

            if pulse > 0:
                values.append((pulse * 0.0343) / 2)

            time.sleep_ms(30)

        if not values:
            return None

        return sum(values) / len(values)


def is_full(distance_cm, threshold_cm=FULL_THRESHOLD_CM):
    if distance_cm is None:
        return False
    return distance_cm <= threshold_cm


def _clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def estimate_fill_percent(
    distance_cm,
    empty_cm=EMPTY_THRESHOLD_CM,
    full_cm=FULL_THRESHOLD_CM,
    empty_deadband_cm=EMPTY_DEADBAND_CM,
    full_deadband_cm=FULL_DEADBAND_CM,
    gamma=FILL_CURVE_GAMMA,
):
    if distance_cm is None:
        return None

    effective_empty_cm = empty_cm - empty_deadband_cm
    effective_full_cm = full_cm + full_deadband_cm

    span = effective_empty_cm - effective_full_cm
    if span <= 0:
        return None

    if distance_cm >= effective_empty_cm:
        return 0
    if distance_cm <= effective_full_cm:
        return 100

    fill_ratio = (effective_empty_cm - distance_cm) / span
    fill_ratio = _clamp(fill_ratio, 0.0, 1.0)
    if gamma > 0:
        fill_ratio = fill_ratio ** gamma
    return int(round(fill_ratio * 100))


def estimate_coin_level(
    distance_cm,
    max_coins=400,
    avg_coin_value=4.5,
    empty_cm=EMPTY_THRESHOLD_CM,
    full_cm=FULL_THRESHOLD_CM,
):
    fill_percent = estimate_fill_percent(distance_cm, empty_cm=empty_cm, full_cm=full_cm)
    if fill_percent is None:
        return {
            "fill_percent": None,
            "estimated_coin_count": None,
            "estimated_total": None,
        }

    estimated_coin_count = int((max_coins * fill_percent) / 100)
    estimated_total = int(estimated_coin_count * avg_coin_value)
    return {
        "fill_percent": fill_percent,
        "estimated_coin_count": estimated_coin_count,
        "estimated_total": estimated_total,
    }

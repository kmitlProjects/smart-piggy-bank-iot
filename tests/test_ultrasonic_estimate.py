import time
from ultrasonic import UltrasonicSensor, estimate_coin_level

# Tune these values to match your real container.
BIN_EMPTY_DISTANCE_CM = 20.0
BIN_FULL_DISTANCE_CM = 5.0
BIN_MAX_COINS_EST = 400
AVG_COIN_VALUE_EST = 4.5

sensor = UltrasonicSensor()
print("Ultrasonic estimate test started")

while True:
    distance_cm = sensor.measure_distance_cm(samples=3)
    estimate = estimate_coin_level(
        distance_cm,
        max_coins=BIN_MAX_COINS_EST,
        avg_coin_value=AVG_COIN_VALUE_EST,
        empty_cm=BIN_EMPTY_DISTANCE_CM,
        full_cm=BIN_FULL_DISTANCE_CM,
    )
    print(
        "distance=", distance_cm,
        "fill=", estimate["fill_percent"],
        "coins~=", estimate["estimated_coin_count"],
        "value~=", estimate["estimated_total"],
    )
    time.sleep_ms(800)

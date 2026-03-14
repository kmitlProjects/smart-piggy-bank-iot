import time
from coins import CoinCounter

coins = CoinCounter()
print("Coin test started")

while True:
    if coins.consume_new_events() > 0:
        print("counts=", coins.snapshot(), "total=", coins.total())
    time.sleep_ms(100)

import time
from display import init_display, render_status

oled = init_display()
print("Display test started")

n = 0
while True:
    counts = {"1": n, "2": n // 2, "5": n // 3, "10": n // 4}
    total = counts["1"] + counts["2"] * 2 + counts["5"] * 5 + counts["10"] * 10
    render_status(oled, counts, total, is_full=(n % 10 == 0))
    n += 1
    time.sleep_ms(500)

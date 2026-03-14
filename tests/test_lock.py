import time
from lock import init_lock

lock = init_lock()
print("Lock test started")

while True:
    print("UNLOCK")
    lock.unlock()
    time.sleep(2)

    print("LOCK")
    lock.lock()
    time.sleep(2)

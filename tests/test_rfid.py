import time
from rfid import init_rfid, read_card_uid

reader = init_rfid()
print("RFID test started")

while True:
    uid = read_card_uid(reader)
    if uid is not None:
        print("UID:", uid)
        time.sleep_ms(400)
    time.sleep_ms(50)

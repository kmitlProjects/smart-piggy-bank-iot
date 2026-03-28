# MQTT Setup

เอกสารนี้อธิบายการตั้งค่า MQTT สำหรับระบบเวอร์ชันปัจจุบัน

## Current MQTT Role in This Project

MQTT ใช้เป็นช่องทางสื่อสารระหว่าง `ESP32` และ `backend`

- `ESP32 -> MQTT -> backend`
  - ส่ง coin snapshots
  - ส่ง device heartbeat / status
  - ส่ง enroll scan UID
  - ส่งผลลัพธ์ของคำสั่ง เช่น web unlock / reset

- `backend -> MQTT -> ESP32`
  - สั่ง unlock
  - สั่ง reset
  - สั่งเปิด/ปิด enroll mode
  - สั่งเปลี่ยน dashboard refresh interval

Frontend เวอร์ชันปัจจุบัน **ไม่ได้ subscribe MQTT โดยตรง**
Frontend เรียกข้อมูลผ่าน `/api/*` จาก backend

## Topics

```text
piggybank/data
piggybank/command
```

ค่า default ตอนนี้:
- `MQTT_TOPIC_PUBLISH = piggybank/data`
- `MQTT_TOPIC_SUBSCRIBE = piggybank/command`

## Current Host Strategy

โปรเจกต์นี้ใช้แนวทาง `local-first`

### ESP32 side
ดูค่าที่:
- [esp32/config.py](esp32/config.py)

ฟิลด์สำคัญ:
- `MQTT_BROKER`
- `BACKEND_HOST`

### Backend side
ดูค่าที่:
- `backend/.env`
- [backend/config.py](backend/config.py)

เมื่อรันผ่าน Docker:
- backend container จะคุยกับ MQTT broker ที่ `host.docker.internal:1883`
- frontend คุยกับ backend ผ่าน Vite proxy / Docker network

## Recommended Setup

1. เปิด MQTT broker บนเครื่อง host ที่ port `1883`
2. รันคำสั่งนี้เพื่อ sync host name ให้ตรงกัน

```bash
python3 tools/set_host.py --auto
```

คำสั่งนี้จะอัปเดต
- `esp32/config.py`
- `backend/.env`

3. เปิดระบบ

```bash
docker compose up --build
```

4. อัปโหลดไฟล์ขึ้น ESP32

```bash
./tools/sync_up.sh auto <webrepl-password> [preferred-esp32-ip]
```

## Message Direction Summary

### Periodic device payload
ESP32 ส่ง heartbeat / state snapshots เป็นระยะ เช่น
- coin counts
- total
- distance_cm
- fill_percent
- is_locked
- wifi_connected
- heartbeat_reason

### Enroll mode
- backend publish command เปิด/ปิด enroll mode
- ESP32 ส่ง `rfid_scan_uid` กลับมาเมื่ออ่านบัตรในโหมด enroll

### Access / system actions
- web unlock และ reset จะถูกบันทึกต่อเป็น activity logs ฝั่ง backend

## Notes for Report

เวอร์ชันนี้เลือกให้ MQTT ทำหน้าที่เฉพาะ device-backend messaging เท่านั้น ไม่ให้ frontend subscribe ตรง เพื่อให้
- state management ง่ายขึ้น
- logging และ authorization รวมศูนย์ที่ backend
- หน้าเว็บเรียกข้อมูลผ่าน REST API ที่ควบคุมได้ง่ายกว่า

## Common Problems

### Backend is up but ESP32 data does not arrive
- MQTT broker ไม่ได้รัน
- `MQTT_BROKER` ใน `esp32/config.py` ไม่ตรงกับ host ปัจจุบัน
- backend `.env` ไม่ตรงกับ host ปัจจุบัน

### ESP32 online but commands do not reach the board
- เช็ก topic command
- เช็กว่า ESP32 subscribe สำเร็จ
- เช็กว่า broker port `1883` reachable

### After changing networks, the system stops talking
- รันใหม่:

```bash
python3 tools/set_host.py --auto
```

- จากนั้น restart backend และ sync code ขึ้น ESP32 ใหม่


# Quick Start

เอกสารนี้เป็นทางลัดสำหรับเปิดระบบเวอร์ชันปัจจุบันให้ใช้งานได้เร็วที่สุด

## Prerequisites

- Docker Desktop
- Python 3
- Node.js / npm
- MQTT broker บนเครื่อง host ที่ port `1883`
- ESP32 ที่เชื่อม Wi-Fi วงเดียวกับเครื่องพัฒนา

## Step 1: Sync host config

อัปเดต host name / IP ที่ใช้ร่วมกันระหว่าง ESP32 และ backend

```bash
cd /Users/chanwitkamjadpai/Documents/ChanwitDoc/2568_comsci/3_2_2568/Practical\ Project/code/version-3_myproject_VSCode-MicroPico
python3 tools/set_host.py --auto
```

## Step 2: Start frontend + backend

```bash
docker compose up --build
```

เปิดใช้งานที่:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5001`

## Step 3: Upload ESP32 code

```bash
./tools/sync_up.sh auto <webrepl-password> [preferred-esp32-ip]
```

ตัวอย่าง:

```bash
./tools/sync_up.sh auto neae4850 10.164.223.245
```

จากนั้นกด `EN/RESET` ที่บอร์ด 1 ครั้ง

## Step 4: Verify the system

เช็ก flow หลักตามนี้

1. เปิดหน้า Dashboard
2. ดูว่า top bar แสดง `Connected`
3. ไปหน้า Settings
4. เปิด RFID scan mode และทดลองเพิ่มบัตร
5. ทดสอบปลดล็อกผ่านบัตรหรือ `Unlock via Web`
6. ไปหน้า Transactions เพื่อตรวจสอบ log

## Current URLs

- `http://localhost:5173/dashboard`
- `http://localhost:5173/statistics`
- `http://localhost:5173/transactions`
- `http://localhost:5173/settings`

## Current System Behavior

- RFID unlock ต้องใช้ backend online
- การหยอดเหรียญยังทำงานได้แม้ backend offline
- เมื่อระบบกลับมา online ยอดเหรียญสะสมจะถูก sync กลับมายัง backend

## If Something Fails

### Frontend opens but no live data
- เช็กว่า backend container ยัง `Up`
- เช็กว่า MQTT broker เปิดอยู่
- เช็กว่า ESP32 ต่อ Wi-Fi ได้

### RFID unlock does not work
- เช็กว่า backend online
- เช็กว่าบัตรถูก enroll แล้ว
- เช็กหน้า Transactions ว่ามี access/security log หรือไม่

### WebREPL upload fails
- เช็ก password
- เช็ก IP ของบอร์ด
- เช็กว่า ESP32 อยู่ใน network เดียวกัน

## AI note

โปรเจกต์นี้พัฒนาด้วยแนวทาง `AI-assisted development`
- visual references ของ frontend บางส่วนมาจาก Stitch AI
- การช่วย debug / refactor / implementation บางส่วนใช้ AI assistant


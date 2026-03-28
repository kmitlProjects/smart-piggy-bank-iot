
# Smart Piggy Bank

Smart Piggy Bank คือระบบกระปุกออมสินอัจฉริยะที่ออกแบบให้เชื่อมต่อ IoT, Web, และฐานข้อมูลอย่างครบวงจร เหมาะสำหรับงานส่งโปรเจกต์และสาธิตแนวคิดระบบออมเงินอัตโนมัติที่ปลอดภัยและตรวจสอบได้

## System Overview

**Component Stack:**
- **ESP32 + MicroPython**: อ่านเหรียญ, RFID, ultrasonic, lock, OLED, ส่งข้อมูลผ่าน MQTT, เชื่อมต่อ Wi-Fi
- **Flask backend + SQLite**: เก็บข้อมูล, ตรวจสิทธิ์ RFID, สร้างสถิติ, เก็บ log, ให้ API สำหรับ frontend
- **React + Vite frontend**: Dashboard, Statistics, Transactions, Settings (UI/UX ทันสมัย)
- **MQTT Broker**: สื่อสารระหว่าง ESP32 กับ backend (ใช้ Mosquitto หรืออื่นๆ)

**Data Flow:**
1. ESP32 อ่านเหรียญ/บัตร/สถานะ แล้วส่ง snapshot ผ่าน MQTT → backend
2. Backend ประมวลผล, อัปเดตฐานข้อมูล, ตอบ API ให้ frontend
3. Frontend แสดงผลแบบ real-time, สั่งงาน (unlock/reset/enroll) ผ่าน backend API

## Architecture Diagram

```mermaid
graph TD
        User[User / Web Browser]
        FE[React Frontend (Vite)]
        BE[Flask Backend + SQLite]
        MQTT[MQTT Broker]
        ESP[ESP32 (MicroPython)]
        User --> FE --> BE --> MQTT --> ESP
        ESP --> MQTT --> BE
```

## Folder Structure

```text
version-3_myproject_VSCode-MicroPico/
├── backend/        # Flask API, SQLite, MQTT ingest, business logic
├── esp32/          # MicroPython code for ESP32 (main.py, coins.py, ...)
├── frontend/       # React + Vite dashboard (src/, public/, ...)
├── tools/          # Helper scripts: sync_up.sh, set_host.py, WebREPL
├── docker-compose.yml  # Compose backend + frontend containers
├── README.md
├── QUICK_START.md
└── MQTT_SETUP.md
```

### backend/
- Flask API (app.py)
- SQLite DB (data/piggybank.db)
- Business logic: RFID, coin, statistics, logs
- MQTT subscriber/command handler
- Config: .env, config.py

### esp32/
- MicroPython firmware: main.py, coins.py, rfid.py, display.py, lock.py, wifi.py, ...
- config.py: Wi-Fi, MQTT, backend host
- lib/: driver libraries (mfrc522, ssd1306)

### frontend/
- React SPA (src/components, public/)
- Dashboard, Statistics, Transactions, Settings
- Vite config, package.json

### tools/
- sync_up.sh: อัปโหลดไฟล์ไป ESP32 ผ่าน WebREPL
- set_host.py: sync host name/IP ระหว่าง ESP32 กับ backend
- webrepl_cli.py: CLI สำหรับ WebREPL

## Deployment & Setup

### Prerequisites
- Python 3
- Node.js / npm
- Docker Desktop
- MQTT broker (เช่น Mosquitto) เปิดที่ host port 1883
- ESP32 ที่เปิด WebREPL และเชื่อม Wi-Fi วงเดียวกับเครื่องพัฒนา

### 1. Sync host name / IP (สำคัญมาก)
เมื่อเปลี่ยน network หรือเครื่อง host ให้รัน:

```bash
python3 tools/set_host.py --auto
```
จะอัปเดตทั้ง `esp32/config.py` และ `backend/.env` ให้ตรงกัน

### 2. Start backend & frontend

```bash
docker compose up --build
```
URLs:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5001

### 3. Upload code to ESP32

```bash
./tools/sync_up.sh auto <webrepl-password> [preferred-esp32-ip]
```
ตัวอย่าง:
```bash
./tools/sync_up.sh auto neae4850 10.164.223.245
```
หลังอัปโหลด กด EN/RESET ที่บอร์ด 1 ครั้ง

### 4. Verify the system
1. เปิด Dashboard ดูสถานะ
2. ทดสอบ RFID scan mode, เพิ่มบัตร, ปลดล็อก
3. ตรวจสอบ Transactions, Statistics

## Configuration Details

### ESP32 (esp32/config.py)
- WIFI_SSID, WIFI_PASSWORD: กำหนด Wi-Fi
- MQTT_BROKER: host ของ MQTT (ควร sync ด้วย set_host.py)
- BACKEND_HOST, BACKEND_PORT: สำหรับ REST API

### Backend (backend/.env, config.py)
- MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_DATA, ...
- API_HOST, API_PORT, PUBLIC_DASHBOARD_HOST
- DB: backend/data/piggybank.db (Docker volume)

### Frontend (frontend/)
- VITE_API_TARGET: proxy ไป backend
- ใช้ React + Vite, hot reload

## Data & Persistence

### SQLite
- backend/data/piggybank.db (Docker volume, ข้อมูลไม่หาย)
- ตารางหลัก: devices, latest_status, coin_events, rfid_cards, access_logs

### ESP32 Local State
- เก็บยอดเหรียญสะสมใน flash (offline ได้)
- sync snapshot กลับ backend เมื่อ online

## MQTT Communication

- ESP32 → MQTT → backend: coin snapshot, heartbeat, RFID scan, command result
- backend → MQTT → ESP32: unlock, reset, enroll mode, refresh interval
- Topics: piggybank/data, piggybank/command

## API Endpoints (สำคัญ)

- `/api/device` : ข้อมูลอุปกรณ์, สถานะ
- `/api/rfid/cards` : จัดการบัตร RFID
- `/api/rfid/enroll-mode` : เปิด/ปิด scan mode
- `/api/device/refresh-interval` : ตั้งค่า refresh interval
- `/api/statistics` : ข้อมูลสถิติ
- `/api/transactions` : ประวัติการหยอดเหรียญ, log

## Features

### Dashboard
- ยอดออมรวม, สัดส่วนเหรียญ, สถานะเชื่อมต่อ, สั่ง Unlock

### Statistics
- Savings growth, coin distribution, most frequent coin, average value, system insights

### Transactions
- Deposit events, RFID logs, system/security events, filter/search

### Settings
- ข้อมูล Wi-Fi, backend, ESP32 IP, dashboard URL
- ปรับ refresh interval, RFID enroll, จัดการบัตร, unlock/reset

## Troubleshooting

### Frontend shows no data
- ตรวจสอบ backend container ทำงานอยู่
- ตรวจสอบ ESP32 เชื่อม Wi-Fi ได้
- ตรวจสอบ MQTT broker เปิดอยู่

### RFID card does not unlock
- ตรวจสอบ backend online
- ตรวจสอบบัตรถูก enroll แล้ว
- ตรวจสอบ log ที่ Settings/Transactions

### ESP32 sync fails
- ตรวจสอบ WebREPL เปิดอยู่
- ตรวจสอบ password/IP ของบอร์ด
- ใช้ `./tools/sync_up.sh auto <password> <preferred-ip>`

## AI-Assisted Development Note

โปรเจกต์นี้ใช้ AI ช่วยออกแบบ, refactor, debug, และปรับปรุงโค้ดบางส่วน (prompt-based)
UI อ้างอิง Stitch AI, ส่วนตัดสินใจสถาปัตยกรรมและ integration เป็นของผู้พัฒนา

> The project was developed using an AI-assisted workflow. UI design references were adapted from Stitch AI, while prompt-based AI tools were used to support implementation, debugging, and iterative refinement. Final architectural decisions, integration, and validation were performed by the project developer.

## Recommended Next Steps

- วาด system architecture diagram, sequence diagram, hardware wiring diagram
- อธิบาย data flow, design rationale, และ integration flow ในรายงาน

## Current Architecture

```text
User / Web Browser
        |
        v
React Frontend (Vite)
        |
        v
Flask Backend + SQLite
        |
        v
MQTT Broker
        |
        v
ESP32 (MicroPython)
  - coin counter
  - RFID reader
  - lock/relay
  - OLED
  - ultrasonic sensor
```

## Key Design Decisions

### 1. RFID authorization uses online-only validation
- ทุกครั้งที่แตะบัตรเพื่อปลดล็อก ESP32 จะส่ง UID ไปให้ backend ตรวจสิทธิ์ก่อน
- ถ้า backend หรือ network ไม่พร้อม ระบบจะไม่ปลดล็อก
- แนวทางนี้ช่วยให้สิทธิ์ของบัตรถูกควบคุมจากจุดเดียว และเพิ่ม/ลบสิทธิ์ได้ทันที

### 2. Coin counting uses local persistence on ESP32
- การหยอดเหรียญยังทำงานได้แม้ backend offline
- ESP32 เก็บยอดสะสมเหรียญไว้ในเครื่อง และส่ง snapshot กลับไปเมื่อกลับมา online
- backend จะ derive transaction history และ statistics จาก cumulative snapshots

### 3. Transaction history is derived from timeseries snapshots
- หน้า `Transactions` และ `Statistics` ใช้ข้อมูลจาก `coin_events`
- ระบบคำนวณเหตุการณ์หยอดเหรียญจาก positive deltas ระหว่าง snapshot แต่ละช่วง
- ข้อดีคือรองรับกรณี backend offline แล้วกลับมา sync ยอดสะสมได้
- ข้อจำกัดคือ timestamp ของเหรียญแต่ละเหรียญอาจไม่ละเอียดเท่าการบันทึกแบบ per-event โดยตรง

## Current Features

### Dashboard
- แสดงยอดออมรวม
- แสดงสัดส่วนเหรียญแต่ละชนิด
- แสดงสถานะการเชื่อมต่อและสถานะ lock
- สั่ง `Unlock via Web`

### Statistics
- Savings growth over time
- Coin distribution
- Most frequent coin
- Average coin value
- System insights

### Transactions
- แสดง deposit events ที่ derive จาก timeseries
- แสดง RFID access logs
- แสดง system/security events เช่น
  - Web unlock
  - Reset
  - RFID card added / updated / removed
  - Enroll mode on / off
- ค้นหาและ filter ตามประเภท activity ได้

### Settings
- แสดงข้อมูล Wi-Fi, backend host, ESP32 IP, dashboard URL
- ปรับ dashboard refresh interval
- เปิด/ปิด RFID enroll mode
- เพิ่ม / แก้ไข / ลบ RFID cards
- สั่ง unlock และ reset ผ่านเว็บ

## Project Structure

```text
version-3_myproject_VSCode-MicroPico/
├── backend/                 # Flask API + SQLite + MQTT ingest
├── esp32/                   # MicroPython code for ESP32
├── frontend/                # React + Vite dashboard
├── tools/                   # helper scripts (sync_up, set_host, WebREPL)
├── docker-compose.yml       # backend + frontend containers
├── README.md
├── QUICK_START.md
└── MQTT_SETUP.md
```

## Running the Project

### Prerequisites
- Python 3
- Node.js / npm
- Docker Desktop
- MQTT broker ที่เปิดฟังบนเครื่อง host ที่ port `1883`
- ESP32 ที่เปิด WebREPL และเชื่อม Wi-Fi วงเดียวกับเครื่องพัฒนา

### 1. Sync host name / IP used by ESP32 and backend

ถ้า host เปลี่ยน ให้รัน:

```bash
python3 tools/set_host.py --auto
```

คำสั่งนี้จะอัปเดต
- `esp32/config.py`
- `backend/.env`

### 2. Start backend and frontend

```bash
docker compose up --build
```

URLs ปกติ:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5001`

### 3. Upload code to ESP32

ผ่าน WebREPL:

```bash
./tools/sync_up.sh auto <webrepl-password> [preferred-esp32-ip]
```

ตัวอย่าง:

```bash
./tools/sync_up.sh auto neae4850 10.164.223.245
```

### 4. Reboot the ESP32

หลังอัปไฟล์ขึ้นบอร์ด ควรกด `EN/RESET` 1 ครั้งเพื่อให้ `main.py` เวอร์ชันล่าสุดเริ่มทำงาน

## Useful Project URLs

- `/dashboard`
- `/statistics`
- `/transactions`
- `/settings`

Frontend รองรับการจำหน้าปัจจุบันและ query state บางส่วนผ่าน URL เช่นหน้า transactions

## Data and Persistence

### SQLite
backend ใช้ฐานข้อมูล:

`backend/data/piggybank.db`

โฟลเดอร์นี้ถูก mount ผ่าน Docker volume ดังนั้น restart container แล้วข้อมูลยังอยู่

### ESP32 local coin state
ESP32 เก็บยอดเหรียญสะสมในไฟล์ local state เพื่อให้ยังนับเหรียญได้แม้ backend offline

## Known Limitations

- RFID unlock ต้องมี backend online
- Coin history ระหว่าง offline ถูก recover ในรูปแบบ snapshot-derived events ไม่ใช่ per-coin realtime events แบบละเอียด 100%
- โปรเจกต์นี้ออกแบบเป็น single-device flow เป็นหลัก (`device_id = esp32`)

## AI-Assisted Development Note

โปรเจกต์นี้มีการใช้ AI ช่วยในการพัฒนาในลักษณะ `AI-assisted development`

- งานออกแบบหน้าตา frontend และ visual direction บางส่วนอ้างอิงจาก `Stitch AI`
- งานช่วยคิด flow, ปรับโครงสร้างระบบ, debugging, refactoring, และเขียน/ปรับปรุงโค้ดบางส่วน ใช้การพัฒนาแบบ prompt-based ร่วมกับ AI assistant
- การตัดสินใจด้านสถาปัตยกรรม, การเลือกแนวทางการทำงานของระบบ, การทดสอบ, และการบูรณาการเข้ากับ hardware จริง เป็นความรับผิดชอบของผู้พัฒนาโครงงาน

ถ้าจะใส่ในรายงาน สามารถอธิบายได้ว่า:

> The project was developed using an AI-assisted workflow. UI design references were adapted from Stitch AI, while prompt-based AI tools were used to support implementation, debugging, and iterative refinement. Final architectural decisions, integration, and validation were performed by the project developer.

## Recommended Submission Focus

เวอร์ชันนี้เหมาะกับการหยุดพัฒนาแล้วไปต่อในส่วนเอกสาร เช่น
- system architecture diagram
- sequence diagram
- hardware wiring diagram
- data flow and design rationale

## Troubleshooting

### Frontend shows no data
- ตรวจสอบว่า backend container ทำงานอยู่
- ตรวจสอบว่า ESP32 เชื่อม Wi-Fi ได้
- ตรวจสอบว่า MQTT broker ที่ host เปิดอยู่จริง

### RFID card does not unlock
- ตรวจสอบว่า backend online
- ตรวจสอบว่าบัตรถูก enroll ในระบบแล้ว
- ตรวจสอบหน้า `Settings` และ `Transactions` ว่ามี security/access logs หรือไม่

### ESP32 sync fails
- ตรวจสอบว่า WebREPL เปิดอยู่
- ตรวจสอบ password และ IP ของบอร์ด
- ลองใช้ `./tools/sync_up.sh auto <password> <preferred-ip>`


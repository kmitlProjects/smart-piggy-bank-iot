# 🚀 QUICK START - Smart Piggy Bank

## ด่วน! เริ่มต้นใช้งานเลย 5 นาที

### **📱 Step 1: ติดตั้ง Node.js (ถ้ายังไม่ได้ลง)**

ลง Node.js จาก: https://nodejs.org/ (เลือก LTS version)

หลังจากลงเสร็จ ตรวจสอบ:
```bash
node --version
npm --version
```

---

### **🌐 Step 2: เปิด Terminal และไป frontend folder**

```bash
# ไป folder เหล่านี้
cd /Users/chanwitkamjadpai/Documents/ChanwitDoc/2568_comsci/3_2_2568/Practical\ Project/code/version-3_myproject_VSCode-MicroPico/frontend

# หรือถ้าเปิดจาก VS Code ก็คลิกขวา > Open Integrated Terminal > cd frontend
```

---

### **📦 Step 3: ติดตั้ง Package Dependencies**

```bash
npm install
```

**รอสักครู่** ให้มันดาวน์โหลด packages ทั้งหมด... (ครั้งแรกจะช้า 1-2 นาที)

---

### **▶️ Step 4: เริ่มต้นรัน Development Server**

```bash
npm run dev
```

**ผลลัพธ์ที่คุณเห็น:**
```
VITE v5.0.8  ready in 245 ms

➜  Local:   http://localhost:5173/
➜  press h + enter to show help
```

✨ Browser จะเปิดอัตโนมัติ! (ถ้าไม่เปิด ให้คลิก: http://localhost:5173/)

---

## 📊 `http://localhost:5173/` ที่เปิดขึ้นมา เห็นอะไร?

```
Smart Piggy Bank
Waiting for data...    (จะเปลี่ยนเป็น "Connected" เมื่อบอร์ด ONLINE)

1 baht: 0
2 baht: 0
5 baht: 0
10 baht: 0

Total: 0
Estimated total: - baht
...
```

---

## ❓ อะไรจะเกิดขึ้นต่อไป?

### **1️⃣ Download MQTT Library สำหรับ ESP32**
```
⚠️ หนึ่งขั้นตอนสำคัญ: ต้องติดตั้ง umqtt.simple library

Download: https://raw.githubusercontent.com/micropython/micropython-lib/master/micropython/umqtt/simple.py
Upload ไป: esp32/lib/simple.py

(หรือติดต่อ Copilot ให้ช่วยดาวน์โหลด)
```

### **2️⃣ Config ESP32 (บอร์ด)**
```
ไฟล์: esp32/main.py

เปลี่ยนเหล่านี้:
WIFI_SSID = "ชื่อ WiFi ของคุณ"
WIFI_PASSWORD = "รหัส WiFi ของคุณ"

MQTT Config ถูกแล้ว ✓ (ใช้ HiveMQ Cloud ฟรี)
```

### **3️⃣ อัพโหลด Code ไปบอร์ด**
```
- เปิด VS Code
- ไปที่ explorer > esp32/
- คลิกขวา > "Upload project to MicroPython device"
- รออัพโหลดเสร็จ
```

### **4️⃣ รัน Code บนบอร์ด**
```
- เปิด Serial Monitor ใน VS Code
- คุณควรเห็น output เช่นนี้:
  ✓ MQTT connected to broker.hivemq.com
  MQTT: published
  MQTT: published
  ...
```

### **5️⃣ ทดสอบเชื่อมต่อ**
```
ใน Browser ที่เปิด http://localhost:5173/ 
(รอ 5-10 วินาที)
คุณควรเห็น:
- Status: Connected ✅
- ข้อมูลเหรียญเริ่มอัปเดตแบบเรียลไทม์
```

---

## 🛠️ คำสั่งที่มี

| คำสั่ง | ทำอะไร |
|-------|--------|
| `npm run dev` | เริ่มต้น Development (Hot reload) |
| `npm run build` | สร้าง Production files |
| `npm run preview` | ดู Preview ของ build |

---

## 🆘 ถ้ามีปัญหา

### ❌ "localhost:5173 ไม่เปิด"
```bash
# ลองหยุดแล้วเริ่มใหม่
# กด Ctrl+C แล้วรัน npm run dev อีกครั้ง
```

### ❌ "Cannot find module 'react'"
```bash
# ลบ node_modules แล้วลง packages ใหม่
rm -rf node_modules
npm install
npm run dev
```

### ❌ "Port 5173 already in use"
```bash
# ใช้ port ตัวอื่น
npx vite --port 3000
```

### ❌ Dashboard ว่างเปล่า (ยังไม่เห็นข้อมูล)
- ✅ ตรวจสอบว่า API endpoint ถูกต้อง (App.jsx บรรทัด 8)
- ✅ ตรวจสอบว่า ESP32 ออนไลน์ (ดู Serial Monitor)
- ✅ ตรวจสอบ WiFi connected (ดู ESP32 terminal)

---

## ✅ ถ้าทุกอย่างทำงาน

🎉 **Congratulations!** คุณได้:
- ✅ React Dashboard รันอยู่
- ✅ ESP32 ส่งข้อมูลมา
- ✅ อัพเดตแบบเรียลไทม์

---

## 📝 ขั้นตอนการเพิ่มเติม

### **เพิ่ม Features ใหม่ (เช่น เปิด/ปิดล็อค)**

1. **Edit React** (`frontend/src/App.jsx`):
```jsx
const [locked, setLocked] = useState(true);

<button onClick={() => {
  fetch(API_URL + '/unlock', {method: 'POST'});
  setLocked(false);
}}>Unlock Piggy Bank</button>
```

2. **Edit ESP32** (`esp32/webserver.py`):
```python
@app.route('/unlock', methods=['POST'])
def unlock():
    lock_pin.on()  # Unlock
    return {'status': 'unlocked'}
```

### **เปลี่ยนสีและ Design**
- Edit `frontend/src/App.css` สำหรับ styling
- Edit `frontend/src/index.css` สำหรับ global styles

---

## 🎯 สรุป

**คุณได้ทำเสร็จแล้ว!**

```
┌─────────────────────────────────────┐
│  ESP32 (MicroPython)               │
│  - นับเหรียญ                       │
│  - ส่งข้อมูล API                    │
└──────────────┬──────────────────────┘
               │ (API)
               ▼
┌─────────────────────────────────────┐
│  React Dashboard                    │
│  - localhost:5173                   │
│  - แสดงข้อมูล เรียลไทม์             │
└─────────────────────────────────────┘
```

---

**Happy coding!** 🚀

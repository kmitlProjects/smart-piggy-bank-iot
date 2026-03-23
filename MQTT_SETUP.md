# 🔗 MQTT Setup Guide - HiveMQ Cloud

## 📝 สรุป

เปลี่ยนจาก **HTTP API** เป็น **MQTT** แล้ว

**ข้อดี:**
- ✅ ส่งข้อมูลได้เร็ว (real-time)
- ✅ ประหยัด bandwidth
- ✅ ไม่ต้องเปิด/ปิด connection บ่อยๆ
- ✅ ใช้ HiveMQ Cloud ฟรี

---

## 🛠️ ไฟล์ที่เปลี่ยน

### **ESP32 (MicroPython)**
- ✅ `esp32/main.py` - ลบ HTTP, เพิ่ม MQTT publish
- ✅ `esp32/mqtt_handler.py` - ไฟล์ helper สำหรับ MQTT client

### **React Frontend**
- ✅ `frontend/src/App.jsx` - ลบ HTTP fetch, เพิ่ม MQTT subscribe
- ✅ `frontend/package.json` - เพิ่ม mqtt.js library

---

## 📡 MQTT Broker Settings

```
Broker: broker.hivemq.com
Protocol: MQTT over WebSocket
URL: wss://broker.hivemq.com:8884/mqtt

Topics:
├── piggybank/data (ESP32 → React)
│   └── ข้อมูลเหรียญ, สถานะ, ระยะทาง
└── piggybank/command (React → ESP32, อนาคต)
    └── สั่งการ (เปิด/ปิด ล็อค)
```

---

## 🚀 ขั้นตอนการใช้

### **ขั้นตอนที่ 1: ติดตั้ง Dependencies**

**ESP32:**
ต้องติดตั้ง `umqtt.simple` library บน MicroPython

```bash
# Upload library ผ่าน MicroPython IDE
# หรือ download จาก: https://github.com/micropython/micropython-lib
# Copy: umqtt/simple.py ไปยัง ESP32 lib/ folder
```

**React:**
```bash
cd frontend
npm install
```

---

### **ขั้นตอนที่ 2: ตั้งค่า ESP32**

แก้ไฟล์ `esp32/main.py`:

```python
# WiFi Config
WIFI_SSID = "ชื่อ WiFi ของคุณ"
WIFI_PASSWORD = "รหัส WiFi"

# MQTT Config (default HiveMQ ไม่ต้องเปลี่ยน)
MQTT_BROKER = "broker.hivemq.com"  # ✓ ถูกแล้ว
MQTT_TOPIC_PUBLISH = "piggybank/data"
MQTT_TOPIC_SUBSCRIBE = "piggybank/command"
```

---

### **ขั้นตอนที่ 3: อัพโหลด Code ไป ESP32**

1. **เปิด VS Code**
2. **ไปที่ `esp32/` folder**
3. **คลิกขวา → Upload project to MicroPython device**
4. **รออัพโหลดเสร็จ**

---

### **ขั้นตอนที่ 4: รัน React Dashboard**

```bash
cd frontend
npm run dev
```

Browser จะเปิด `http://localhost:5173/`

**ที่ Status ประมาณ 5-10 วินาที จะเปลี่ยนเป็น "Connected"**

---

## 🧪 ทดสอบ

### **ตรวจสอบ ESP32 Serial Monitor:**
```
✓ MQTT connected to broker.hivemq.com
MQTT: published
MQTT: published
...
```

### **ตรวจสอบ React Browser Console (F12):**
```
✓ MQTT connected
Subscribed to piggybank/data
Received: {coins: {...}, total: 10, ...}
```

---

## 🔧 ปัญหากับวิธีแก้

### ❌ "Cannot import umqtt"
```
แก้ไข: ต้องติดตั้ง umqtt library ใน ESP32
- Download: https://raw.githubusercontent.com/micropython/micropython-lib/master/micropython/umqtt/simple.py
- Upload ไป: esp32/lib/simple.py
```

### ❌ "MQTT: publish failed"
```
เหตุ: WiFi ไม่เชื่อมต่อ
แก้ไข:
- ตรวจสอบ WIFI_SSID และ WIFI_PASSWORD ถูกต้อง
- ดู Serial Monitor ว่า WiFi connected หรือไม่
```

### ❌ "Status: Connection error"
```
เหตุ: React ไม่เชื่อมต่อ MQTT Broker
แก้ไข:
- ตรวจสอบว่ามี internet
- ลอง refresh browser (Ctrl+R)
- ตรวจ Browser Console (F12) → Network → ดูว่า wss connection ได้หรือไม่
```

### ❌ "Status: Offline - reconnecting"
```
เหตุ: Network ติดขัด
แก้ไข:
- รอนิด แล้ว MQTT จะ reconnect อัตโนมัติ
- ถ้านาน ให้ restart browser
```

---

## 📊 MQTT Message Format

**ตัวอย่างข้อมูลที่ส่งมา (piggybank/data):**
```json
{
  "coins": {"1": 5, "2": 3, "5": 2, "10": 1},
  "total": 26,
  "distance_cm": 8.5,
  "is_full": false,
  "is_locked": true,
  "wifi_connected": true,
  "estimated_total": 130,
  "estimated_coin_count": 29,
  "fill_percent": 57.5
}
```

---

## 🎯 ขั้นตอนต่อไป

1. ✅ ตั้งค่า WiFi SSID/Password
2. ✅ ติดตั้ง umqtt library บน ESP32
3. ✅ อัพโหลด code ไป ESP32
4. ✅ รัน `npm run dev` ใน React
5. ⏳รอให้ Status เปลี่ยนเป็น "Connected"
6. 🎉 ดูข้อมูลไหลเข้ามา!

---

## 📞 ประิ่ศนธารณ์

**ยังไงะหงใจเลือกใช้ HiveMQ Cloud:**
- ไม่ต้องตั้งค่า server เอง
- ไม่ต้องให้ server รันตลอด
- เชื่อมต่อจากไหนได้เพราะผ่าน Internet

**ถ้าต้องใช้ Local Mosquitto:**
- ติดต่อมาแล้ว ขอเปลี่ยนคำแนะนำ

---

✅ **Ready to go!** 🚀

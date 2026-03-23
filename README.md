# Smart Piggy Bank - Complete Project

โครงการ Smart Piggy Bank ที่รวมทั้ง MicroPython Code สำหรับ ESP32 และ React Web Dashboard

## 📁 โครงสร้างโปรเจค

```
version-3_myproject_VSCode-MicroPico/
├── esp32/                    # 🎯 โฟลเดอร์หลักสำหรับอัพโหลดลงบอร์ด
│   ├── main.py              # ไฟล์หลักสำหรับเรียกใช้บน ESP32
│   ├── coins.py             # โมดูลนับเหรียญ
│   ├── dashboard.py         # โมดูลส่งข้อมูลขึ้นเซิร์ฟเวอร์
│   ├── display.py           # โมดูลจอแสดงผล OLED
│   ├── lock.py              # โมดูลควบคุมล็อค
│   ├── rfid.py              # โมดูลอ่าน RFID
│   ├── ultrasonic.py        # โมดูลวัดระยะทาง
│   ├── webserver.py         # โมดูลเซิร์ฟเวอร์ API
│   ├── wifi.py              # โมดูลเชื่อมต่อ WiFi
│   └── lib/                 # ไลบรารี่ที่ต้องการ
│       ├── mfrc522.py       # ไลบรารี่ RFID
│       └── ssd1306.py       # ไลบรารี่ OLED Display
│
├── frontend/                 # 🌐 React Web Dashboard
│   ├── src/
│   │   ├── main.jsx         # React entry point
│   │   ├── App.jsx          # Main component
│   │   ├── App.css          # Styling
│   │   └── index.css        # Global styles
│   ├── public/
│   │   └── index.html       # HTML template
│   ├── package.json         # Dependencies
│   ├── vite.config.js       # Vite configuration
│   └── .gitignore
│
└── README.md                # ไฟล์นี้
```

## 🚀 วิธีการใช้งาน

### **ส่วนที่ 1: อัพโหลด Code ลงบอร์ด ESP32**

1. **เปิด Visual Studio Code**
2. **เลือก Explorer > version-3_myproject_VSCode-MicroPico > esp32**
3. **คลิกขวาที่โฟลเดอร์ `esp32`** 
4. **เลือก "Upload project to MicroPython device"** (หรือใช้ Micro Pico extension)
5. **เสร็จ!** - Code จะเข้าไปในบอร์ด

### **ส่วนที่ 2: รัน React Web Dashboard**

#### **ติดตั้ง Dependencies:**
```bash
cd frontend
npm install
```

#### **เริ่มต้นการพัฒนา (Development):**
```bash
npm run dev
```
- จะเปิด browser ที่ `http://localhost:5173` โดยอัตโนมัติ

#### **สร้าง Production Build:**
```bash
npm run build
```
- ไฟล์สำเร็จจะอยู่ใน `frontend/dist/` 

---

## 📋 คำแนะนำขั้นตอนต่อไป

### **ขั้นตอน 1: ตั้งค่า ESP32**
- [ ] ตรวจสอบว่า WiFi SSID และ Password ถูกต้องใน `esp32/main.py` (บรรทัด WIFI_SSID, WIFI_PASSWORD)
- [ ] ตรวจสอบ pins ถูกต้องตามการต่อวงจร
- [ ] อัพโหลด libraries ไปบอร์ด (mfrc522.py, ssd1306.py)

### **ขั้นตอน 2: เรียกใช้ Code บน ESP32**
- [ ] Upload main project แล้วรัน main.py
- [ ] ตรวจสอบ Serial Monitor ที่ VS Code เพื่อดูว่ามีข้อมูลเข้ามาหรือไม่

### **ขั้นตอน 3: เชื่อมต่อ Frontend กับ Backend**
- [ ] ตรวจสอบ API endpoint ใน `frontend/src/App.jsx` (บรรทัด API_URL)
- [ ] ตรวจสอบว่า ESP32 สามารถส่งข้อมูลมาได้
- [ ] รัน `npm run dev` เพื่อดู dashboard

### **ขั้นตอน 4: ปรับแต่งตามต้องการ**
- [ ] ปรับ Colors ใน `frontend/src/App.css` และ `index.css`
- [ ] เพิ่ม Features ใหม่ใน React
- [ ] ปรับ Timing/Configuration ใน `esp32/main.py`

---

## 🔧 Pin Mapping (ตำแหน่งเสียบสายต่าง ๆ)

- Coins: `1=GPIO21`, `2=GPIO38`, `5=GPIO39`, `10=GPIO40`
- RFID SPI: `SCK=12`, `MOSI=11`, `MISO=13`, `SS=10`, `RST=14`
- OLED I2C: `SDA=8`, `SCL=9`
- Ultrasonic: `TRIG=41`, `ECHO=42`
- Solenoid relay: `GPIO35` (`HIGH=unlock`, `LOW=lock`)
- Indicators: `LED=18`, `BUZZER=17`

---

## 💡 Tips

- **ง่ายในการอัพโหลด**: ทั้งหมดใน `esp32/` folder - แค่คลิกเดียว ✨
- **React ใช้ Vite**: เร็วมาก, hot reload ดี
- **Auto-update**: Frontend ดึงข้อมูลทุก 2 วินาที

---

## 📞 ติดต่อสอบถาม

หากมีปัญหา:
1. ตรวจสอบ Serial Monitor สำหรับข้อมูลจาก ESP32
2. ตรวจสอบ Browser Console (F12) สำหรับข้อมูลจาก React
3. ตรวจสอบว่า WiFi และ API Connection ทำงานถูกต้อง

---

✅ **Ready to go!** ลองรัน `npm run dev` ได้เลยครับ

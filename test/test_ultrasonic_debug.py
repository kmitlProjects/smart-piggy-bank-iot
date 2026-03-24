"""
Test script to check actual ultrasonic distance readings
Run this to find the real distance values
"""
from ultrasonic import UltrasonicSensor
import time

sensor = UltrasonicSensor()

print("===== ULTRASONIC DEBUG TEST =====")
print("ให้ลบเหรียญออกหมด แล้วรอสักครู่...")
time.sleep(2)

print("\n--- ตรวจสอบค่า 10 ครั้ง ---")
values = []
for i in range(10):
    distance = sensor.measure_distance_cm(samples=3)
    values.append(distance)
    print(f"Time {i+1}: {distance:.1f} cm")
    time.sleep(0.5)

avg = sum(values) / len(values)
print(f"\n✓ ค่าเฉลี่ย (EMPTY): {avg:.1f} cm")
print(f"✓ นี่คือค่าที่ต้องใช้ในไฟล์ ultrasonic.py")
print(f"   EMPTY_THRESHOLD_CM = {avg:.1f}")

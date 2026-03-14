# Copilot Prompt Steps for This Project

Use these prompts in order for consistent code generation.

## Step 1: Hardware module implementation

"Create or improve one module only (`coins.py` or `rfid.py` or `lock.py` or `ultrasonic.py` or `display.py`) for ESP32-S3 MicroPython. Keep pin mapping exactly as documented in README. Return full file code."

## Step 2: Main loop integration

"Update `main.py` to integrate all modules with a non-blocking loop. Keep RFID scan, coin counting, OLED updates, lock timeout, and periodic dashboard sending. Return full `main.py`."

## Step 3: Networking and dashboard

"Implement `wifi.py` and `dashboard.py` for robust WiFi connect and periodic JSON POST. Avoid blocking calls inside every loop iteration. Return both full files."

## Step 4: Testing scripts

"Create `tests/` scripts to test each sensor independently on MicroPython board. Keep each test file minimal and runnable directly."

## Step 5: Review and hardening

"Review all project files for pin consistency, relay logic (`LOW unlock`, `HIGH lock`), and library imports from `lib/`. List issues by severity and provide corrected code if needed."

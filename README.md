# Smart Piggy Bank (ESP32-S3 + MicroPython)

## Project structure

- `main.py`: Main application loop
- `coins.py`: Interrupt-driven coin counting
- `rfid.py`: MFRC522 setup and card read
- `lock.py`: Solenoid relay lock control
- `ultrasonic.py`: HC-SR04 distance/full check
- `display.py`: OLED SSD1306 display rendering
- `wifi.py`: WiFi connect helpers
- `dashboard.py`: JSON POST to web dashboard
- `lib/`: Third-party libraries (`mfrc522.py`, `ssd1306.py`)
- `tests/`: Per-device test scripts
- `www/`: Optional web dashboard files

## Pin mapping

- Coins: `1=GPIO21`, `2=GPIO38`, `5=GPIO39`, `10=GPIO40`
- RFID SPI: `SCK=12`, `MOSI=11`, `MISO=13`, `SS=10`, `RST=14`
- OLED I2C: `SDA=8`, `SCL=9`
- Ultrasonic: `TRIG=41`, `ECHO=42`
- Solenoid relay: `GPIO35` (`HIGH=unlock`, `LOW=lock`)
- Indicators: `LED=18`, `BUZZER=17`

## Run

1. Put `mfrc522.py` and `ssd1306.py` inside `lib/`.
2. Set `WIFI_SSID`, `WIFI_PASSWORD`, and `DASHBOARD_URL` in `main.py`.
3. Upload project files to ESP32-S3.
4. Run `main.py`.

## Notes

- Dashboard sending is periodic (`DASHBOARD_UPDATE_MS`) and not called every loop cycle.
- Coin counting uses interrupt callbacks with debounce.
- Ultrasonic now estimates coin level (`fill_percent`, `estimated_coin_count`, `estimated_total`) from measured distance.

## Ultrasonic estimate calibration

Tune these values in `main.py` for your real container:

- `BIN_EMPTY_DISTANCE_CM`: distance when coin bin is empty
- `BIN_FULL_DISTANCE_CM`: distance when bin is nearly full
- `BIN_MAX_COINS_EST`: rough max number of coins when full
- `AVG_COIN_VALUE_EST`: average value per coin for estimated total

Run `tests/test_ultrasonic_estimate.py` on board to observe live distance and estimated values while calibrating.

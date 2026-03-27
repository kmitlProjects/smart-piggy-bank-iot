#!/usr/bin/env python3
"""Sync shared host config for ESP32 + backend + dashboard access.

Examples:
  python tools/set_host.py 192.168.1.50
  python tools/set_host.py --auto
"""

from pathlib import Path
import argparse
import re
import socket
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ESP32_CONFIG = ROOT / "esp32" / "config.py"
BACKEND_ENV = ROOT / "backend" / ".env"


def _replace_line(text: str, key: str, value: str, quoted: bool) -> str:
    pattern = re.compile(rf"^{re.escape(key)}\s*=\s*.*$", re.MULTILINE)
    replacement = f'{key} = "{value}"' if quoted else f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(replacement, text)
    if not text.endswith("\n"):
        text += "\n"
    return text + replacement + "\n"


def _discover_local_host() -> str:
    # macOS-friendly local mDNS name.
    try:
        result = subprocess.run(
            ["scutil", "--get", "LocalHostName"],
            check=True,
            capture_output=True,
            text=True,
        )
        name = result.stdout.strip()
        if name:
            return f"{name}.local"
    except Exception:
        pass

    fallback = socket.gethostname().split(".")[0].strip()
    return f"{fallback}.local" if fallback else "localhost.local"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync MQTT host across configs")
    parser.add_argument("host", nargs="?", help="Host/IP for MQTT broker")
    parser.add_argument("--auto", action="store_true", help="Use current machine mDNS host (*.local)")
    args = parser.parse_args()

    if not ESP32_CONFIG.exists() or not BACKEND_ENV.exists():
        print("Required files not found: esp32/config.py or backend/.env")
        return 1

    host = _discover_local_host() if args.auto else (args.host or "").strip()
    if not host:
        print("Provide host or use --auto")
        return 1

    esp32_text = ESP32_CONFIG.read_text(encoding="utf-8")
    backend_text = BACKEND_ENV.read_text(encoding="utf-8")

    esp32_text = _replace_line(esp32_text, "MQTT_BROKER", host, quoted=True)
    backend_text = _replace_line(backend_text, "MQTT_BROKER", host, quoted=False)
    backend_text = _replace_line(backend_text, "PUBLIC_DASHBOARD_HOST", host, quoted=False)

    ESP32_CONFIG.write_text(esp32_text, encoding="utf-8")
    BACKEND_ENV.write_text(backend_text, encoding="utf-8")

    print(f"MQTT host set to: {host}")
    print("Updated:")
    print("- esp32/config.py")
    print("- backend/.env")
    print("  - MQTT_BROKER")
    print("  - PUBLIC_DASHBOARD_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

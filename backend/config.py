import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "piggybank.db")


def _load_env_file(file_path):
	if not os.path.exists(file_path):
		return

	with open(file_path, "r", encoding="utf-8") as f:
		for raw_line in f:
			line = raw_line.strip()
			if not line or line.startswith("#"):
				continue
			if "=" not in line:
				continue

			key, value = line.split("=", 1)
			key = key.strip()
			value = value.strip().strip('"').strip("'")
			if key and key not in os.environ:
				os.environ[key] = value


_load_env_file(os.path.join(BASE_DIR, ".env"))

# ===== HARDCODED RFID LOCK SYSTEM =====
# System uses a closed/locked list of authorized RFID UIDs.
# Dynamic enrollment has been disabled. ONLY these 2 UIDs are permitted:
LOCKED_RFID_UIDS = [
    [182, 188, 21, 6, 25],      # UID #1 - Only authorized card
    [195, 118, 240, 6, 67],     # UID #2 - Only authorized card
]
# Note: All other UIDs (including [AA-BB-CC], etc.) are DENIED.

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_DATA = os.getenv("MQTT_TOPIC_DATA", "piggybank/data")
MQTT_TOPIC_COMMAND = os.getenv("MQTT_TOPIC_COMMAND", "piggybank/command")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "piggybank_backend_sub")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "5001"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
CONNECTIVITY_TIMEOUT_SEC = int(os.getenv("CONNECTIVITY_TIMEOUT_SEC", "10"))
PUBLIC_DASHBOARD_HOST = os.getenv("PUBLIC_DASHBOARD_HOST", "").strip()
PUBLIC_DASHBOARD_PORT = int(os.getenv("PUBLIC_DASHBOARD_PORT", str(FRONTEND_PORT)))

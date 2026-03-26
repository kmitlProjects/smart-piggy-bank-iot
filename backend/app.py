from flask import Flask, jsonify, request
import os
import socket
import threading
import time

from config import API_HOST, API_PORT, CONNECTIVITY_TIMEOUT_SEC, FRONTEND_PORT
from db import (
    add_rfid_card,
    check_access,
    clear_pending_rfid_scan,
    deactivate_rfid_card_by_id,
    get_access_history,
    get_coin_history,
    get_coin_summary,
    get_connectivity_history,
    get_connectivity_latest,
    get_device_runtime,
    get_latest_status,
    get_rfid_enrollment_state,
    init_db,
    list_rfid_cards,
    process_connectivity_timeout,
    reset_database,
    set_rfid_enrollment_state,
    update_rfid_card,
)
from mqtt_commands import (
    publish_reset_command,
    publish_rfid_enroll_command,
    publish_unlock_command,
)
from mqtt_subscriber import MQTTIngestService


mqtt_service = MQTTIngestService()
ALLOWED_ORIGINS = {
    f"http://127.0.0.1:{FRONTEND_PORT}",
    f"http://localhost:{FRONTEND_PORT}",
}


def _instance_info() -> dict:
    return {
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "in_docker": os.path.exists("/.dockerenv"),
    }


def _best_effort_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _bool_arg(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            response = app.make_response(("", 204))
            origin = request.headers.get("Origin", "")
            if origin in ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response

    @app.after_request
    def add_cors_headers(response):
        if request.path.startswith("/api/"):
            response.headers["X-Backend-Host"] = socket.gethostname()
            response.headers["X-Backend-Pid"] = str(os.getpid())
            origin = request.headers.get("Origin", "")
            if origin in ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "instance": _instance_info()})

    @app.get("/api/status")
    def status():
        process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")
        data = get_latest_status() or {}
        runtime = get_device_runtime()
        connectivity = get_connectivity_latest(device_id="esp32")
        data["wifi_connected"] = bool(connectivity.get("is_connected", False))
        data["connection_state"] = connectivity.get("current_state")
        data["last_seen_at"] = connectivity.get("last_seen_at")
        if runtime.get("wifi_ssid"):
            data["wifi_ssid"] = runtime["wifi_ssid"]
        if runtime.get("esp32_ip"):
            data["esp32_ip"] = runtime["esp32_ip"]
        return jsonify({"status": data})

    @app.get("/api/device")
    def device_info():
        process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")
        runtime = get_device_runtime()
        latest_status = get_latest_status() or {}
        connectivity = get_connectivity_latest(device_id="esp32")

        return jsonify({
            "device_id": latest_status.get("device_id") or runtime.get("device_id") or "esp32",
            "wifi_ssid": runtime.get("wifi_ssid") or os.getenv("WIFI_SSID", "Unknown"),
            "local_ip": _best_effort_local_ip(),
            "esp32_ip": runtime.get("esp32_ip") or latest_status.get("esp32_ip") or "Unknown",
            "connection_status": connectivity.get("current_state", "UNKNOWN"),
            "wifi_connected": bool(connectivity.get("is_connected", False)),
            "last_seen_at": connectivity.get("last_seen_at"),
            "backend_host": socket.gethostname(),
        })

    @app.get("/api/connectivity/latest")
    def connectivity_latest():
        process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")
        latest = get_connectivity_latest(device_id="esp32")
        latest["timeout_seconds"] = CONNECTIVITY_TIMEOUT_SEC
        return jsonify({"connectivity": latest})

    @app.get("/api/connectivity/history")
    def connectivity_history():
        limit = int(request.args.get("limit", 100))
        return jsonify({"history": get_connectivity_history(limit=limit, device_id="esp32")})

    @app.get("/api/coins/summary")
    def coins_summary():
        return jsonify({"summary": get_coin_summary()})

    @app.get("/api/coins/history")
    def coins_history():
        limit = int(request.args.get("limit", 100))
        return jsonify({"history": get_coin_history(limit=limit)})

    @app.get("/api/access/history")
    def access_history():
        limit = int(request.args.get("limit", 100))
        return jsonify({"history": get_access_history(limit=limit)})

    @app.get("/api/rfid/cards")
    def rfid_cards():
        active_only = _bool_arg(request.args.get("active_only"), default=False)
        return jsonify({"cards": list_rfid_cards(active_only=active_only)})

    @app.post("/api/rfid/cards")
    def create_rfid_card():
        payload = request.get_json(silent=True) or {}
        uid = payload.get("uid")
        owner_name = payload.get("owner_name")
        if not uid:
            enroll_state = get_rfid_enrollment_state()
            uid = enroll_state.get("pending_uid")

        if not uid:
            return jsonify({"error": "uid is required"}), 400

        try:
            card = add_rfid_card(uid=uid, owner_name=owner_name)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        clear_pending_rfid_scan()
        publish_rfid_enroll_command(device_id="esp32", enabled=False)
        set_rfid_enrollment_state(active=False, pending_uid=None)
        return jsonify({"card": card})

    @app.put("/api/rfid/cards/<int:card_id>")
    def update_rfid_card_route(card_id: int):
        payload = request.get_json(silent=True) or {}
        uid = payload.get("uid")
        owner_name = payload.get("owner_name")
        is_active = payload.get("is_active")

        if not uid:
            return jsonify({"error": "uid is required"}), 400

        try:
            card = update_rfid_card(card_id, uid=uid, owner_name=owner_name, is_active=is_active)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                return jsonify({"error": "uid already exists"}), 409
            raise

        if card is None:
            return jsonify({"error": "card not found"}), 404

        return jsonify({"card": card})

    @app.delete("/api/rfid/cards/<int:card_id>")
    def delete_rfid_card_route(card_id: int):
        deleted = deactivate_rfid_card_by_id(card_id)
        if not deleted:
            return jsonify({"error": "card not found"}), 404
        return jsonify({"deleted": True, "card_id": card_id})

    @app.get("/api/rfid/enroll-mode")
    def get_rfid_enroll_mode():
        return jsonify({"enrollment": get_rfid_enrollment_state()})

    @app.post("/api/rfid/enroll-mode")
    def set_rfid_enroll_mode():
        payload = request.get_json(silent=True) or {}
        active = _bool_arg(payload.get("active"), default=False)
        sent = publish_rfid_enroll_command(device_id=payload.get("device_id", "esp32"), enabled=active)
        if not sent:
            return jsonify({"error": "failed to send enroll command to device"}), 503

        if active:
            state = set_rfid_enrollment_state(active=True, pending_uid=None)
        else:
            clear_pending_rfid_scan()
            state = set_rfid_enrollment_state(active=False, pending_uid=None)

        return jsonify({"enrollment": state, "command_sent": True})

    @app.post("/api/access/check")
    def access_check():
        payload = request.get_json(force=True)
        uid_raw = payload.get("uid")
        uid = uid_raw.strip() if isinstance(uid_raw, str) else uid_raw
        wifi_connected = bool(payload.get("wifi_connected", False))
        if not uid:
            return jsonify({"error": "uid is required"}), 400

        result = check_access(uid=uid, wifi_connected=wifi_connected)
        return jsonify(result)

    @app.post("/api/reset")
    def reset():
        payload = request.get_json(silent=True) or {}
        device_id = payload.get("device_id", "esp32")
        sent = publish_reset_command(device_id=device_id)
        if not sent:
            return jsonify({
                "error": "failed to send reset command to device",
                "instance": _instance_info(),
            }), 503

        result = reset_database(clear_cards=False)
        return jsonify({
            "reset": result,
            "command_sent": True,
            "device_id": device_id,
            "instance": _instance_info(),
        })

    @app.post("/api/unlock")
    def unlock():
        payload = request.get_json(silent=True) or {}
        device_id = payload.get("device_id", "esp32")
        duration_ms = int(payload.get("duration_ms", 5000))

        sent = publish_unlock_command(device_id=device_id, duration_ms=duration_ms)
        if not sent:
            return jsonify({
                "error": "failed to send unlock command to device",
                "instance": _instance_info(),
            }), 503

        return jsonify({
            "unlock": "requested",
            "command_sent": True,
            "device_id": device_id,
            "duration_ms": duration_ms,
            "instance": _instance_info(),
        })

    return app


def initialize_app():
    def timeout_watcher():
        while True:
            try:
                changed = process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")
                if changed:
                    print("Connectivity changed: DISCONNECTED (timeout)")
            except Exception as exc:
                print(f"Connectivity watcher error: {exc}")
            time.sleep(2)

    init_db()
    mqtt_service.start()
    threading.Thread(target=timeout_watcher, daemon=True).start()
    return create_app()


app = initialize_app()


def main():
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    main()

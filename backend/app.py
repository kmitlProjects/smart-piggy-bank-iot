from flask import Flask, jsonify, request
import threading
import time

from config import API_HOST, API_PORT, CONNECTIVITY_TIMEOUT_SEC
from db import (
    add_rfid_card,
    check_access,
    get_connectivity_history,
    get_connectivity_latest,
    get_access_history,
    get_coin_history,
    get_coin_summary,
    get_latest_status,
    init_db,
    list_rfid_cards,
    process_connectivity_timeout,
    deactivate_rfid_card,
    reset_database,
)
from mqtt_subscriber import MQTTIngestService


mqtt_service = MQTTIngestService()
ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}


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
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response

    @app.after_request
    def add_cors_headers(response):
        if request.path.startswith("/api/"):
            origin = request.headers.get("Origin", "")
            if origin in ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/status")
    def status():
        process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")
        data = get_latest_status() or {}
        connectivity = get_connectivity_latest(device_id="esp32")
        data["wifi_connected"] = bool(connectivity.get("is_connected", False))
        data["connection_state"] = connectivity.get("current_state")
        data["last_seen_at"] = connectivity.get("last_seen_at")
        return jsonify({"status": data})

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
        return jsonify({"cards": list_rfid_cards()})

    @app.post("/api/rfid/cards")
    def add_card():
        payload = request.get_json(force=True)
        uid = (payload.get("uid") or "").strip()
        owner_name = payload.get("owner_name")
        if not uid:
            return jsonify({"error": "uid is required"}), 400
        card = add_rfid_card(uid=uid, owner_name=owner_name)
        return jsonify({"card": card})

    @app.delete("/api/rfid/cards/<uid>")
    def remove_card(uid):
        ok = deactivate_rfid_card(uid)
        if not ok:
            return jsonify({"error": "uid not found"}), 404
        return jsonify({"deleted": True, "uid": uid})

    @app.post("/api/access/check")
    def access_check():
        payload = request.get_json(force=True)
        uid = (payload.get("uid") or "").strip()
        wifi_connected = bool(payload.get("wifi_connected", False))
        if not uid:
            return jsonify({"error": "uid is required"}), 400

        result = check_access(uid=uid, wifi_connected=wifi_connected)
        return jsonify(result)

    @app.post("/api/reset")
    def reset():
        payload = request.get_json(silent=True) or {}
        clear_cards = bool(payload.get("clear_cards", False))
        result = reset_database(clear_cards=clear_cards)
        return jsonify({"reset": result, "clear_cards": clear_cards})

    return app


def main():
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
    app = create_app()
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    main()

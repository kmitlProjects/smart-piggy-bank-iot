from flask import Flask, jsonify, request

from config import API_HOST, API_PORT
from db import (
    add_rfid_card,
    check_access,
    get_access_history,
    get_coin_history,
    get_coin_summary,
    get_latest_status,
    init_db,
    list_rfid_cards,
    deactivate_rfid_card,
    reset_database,
)
from mqtt_subscriber import MQTTIngestService


mqtt_service = MQTTIngestService()


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/status")
    def status():
        data = get_latest_status()
        return jsonify({"status": data})

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
    init_db()
    mqtt_service.start()
    app = create_app()
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == "__main__":
    main()

from flask import Flask, jsonify, request
from datetime import datetime, timedelta, timezone
import os
import socket
import threading
import time

from config import (
    API_HOST,
    API_PORT,
    CONNECTIVITY_TIMEOUT_SEC,
    FRONTEND_PORT,
    PUBLIC_DASHBOARD_HOST,
    PUBLIC_DASHBOARD_PORT,
)
from db import (
    add_rfid_card,
    check_access,
    clear_pending_rfid_scan,
    deactivate_rfid_card_by_id,
    get_activity_history,
    get_access_history,
    get_coin_events_for_statistics,
    get_coin_history,
    get_coin_summary,
    get_connectivity_history,
    get_connectivity_latest,
    get_device_runtime,
    get_device_settings,
    get_latest_status,
    get_rfid_enrollment_state,
    init_db,
    log_activity_event,
    list_rfid_cards,
    process_connectivity_timeout,
    reset_database,
    set_device_refresh_interval,
    set_rfid_enrollment_state,
    update_rfid_card,
)
from mqtt_commands import (
    publish_dashboard_interval_command,
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
COIN_DENOMINATIONS = (1, 2, 5, 10)


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


def _public_http_url(host: str, port: int) -> str | None:
    host_text = (host or "").strip()
    if not host_text:
        return None
    return f"http://{host_text}:{int(port)}"


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _parse_iso_datetime(value) -> datetime | None:
    if not value:
        return None

    try:
        text = value if isinstance(value, str) else str(value)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _coin_counts_from_row(row: dict) -> dict[int, int]:
    return {
        denomination: max(0, _safe_int(row.get(f"coin_{denomination}"), 0))
        for denomination in COIN_DENOMINATIONS
    }


def _coin_value_from_counts(counts: dict[int, int]) -> int:
    return sum(denomination * count for denomination, count in counts.items())


def _build_derived_coin_events(rows: list[dict]) -> list[dict]:
    derived_events: list[dict] = []
    previous_counts: dict[int, int] | None = None

    for row in rows:
        timestamp = _parse_iso_datetime(row.get("created_at"))
        if timestamp is None:
            continue

        current_counts = _coin_counts_from_row(row)

        if previous_counts is None:
            if any(current_counts.values()):
                derived_events.append({
                    "created_at": row.get("created_at"),
                    "timestamp": timestamp,
                    "counts": current_counts,
                    "coin_count": sum(current_counts.values()),
                    "value": _coin_value_from_counts(current_counts),
                    "seeded": True,
                })
            previous_counts = current_counts
            continue

        delta_counts = {
            denomination: current_counts[denomination] - previous_counts[denomination]
            for denomination in COIN_DENOMINATIONS
        }

        # Counter resets produce negative deltas; treat them as a new baseline instead of a loss.
        if any(delta < 0 for delta in delta_counts.values()):
            previous_counts = current_counts
            continue

        if any(delta > 0 for delta in delta_counts.values()):
            derived_events.append({
                "created_at": row.get("created_at"),
                "timestamp": timestamp,
                "counts": delta_counts,
                "coin_count": sum(delta_counts.values()),
                "value": _coin_value_from_counts(delta_counts),
                "seeded": False,
            })

        previous_counts = current_counts

    return derived_events


def _period_totals(events: list[dict], start_dt: datetime, end_dt: datetime) -> tuple[int, int]:
    total_value = 0
    total_coins = 0
    for event in events:
        timestamp = event["timestamp"]
        if start_dt <= timestamp <= end_dt:
            total_value += event["value"]
            total_coins += event["coin_count"]
    return total_value, total_coins


def _percent_change(current_value: float, previous_value: float) -> float:
    if previous_value <= 0:
        if current_value <= 0:
            return 0.0
        return 100.0
    return ((current_value - previous_value) / previous_value) * 100.0


def _build_savings_growth_series(events: list[dict], days: int, now_dt: datetime | None = None) -> list[dict]:
    now_dt = now_dt or datetime.now(timezone.utc)
    end_date = now_dt.date()
    start_date = end_date - timedelta(days=days - 1)
    baseline_value = 0
    daily_value_map: dict = {}
    daily_coin_map: dict = {}

    for event in events:
        event_date = event["timestamp"].date()
        if event_date < start_date:
            baseline_value += event["value"]
            continue
        if event_date > end_date:
            continue

        daily_value_map[event_date] = daily_value_map.get(event_date, 0) + event["value"]
        daily_coin_map[event_date] = daily_coin_map.get(event_date, 0) + event["coin_count"]

    running_total = baseline_value
    series = []
    for offset in range(days):
        bucket_date = start_date + timedelta(days=offset)
        running_total += daily_value_map.get(bucket_date, 0)
        series.append({
            "date": bucket_date.isoformat(),
            "label": bucket_date.strftime("%a") if days <= 7 else bucket_date.strftime("%d %b"),
            "value": running_total,
            "daily_value": daily_value_map.get(bucket_date, 0),
            "coin_count": daily_coin_map.get(bucket_date, 0),
        })

    return series


def _collect_timeseries_context() -> dict:
    process_connectivity_timeout(CONNECTIVITY_TIMEOUT_SEC, device_id="esp32")

    snapshot_rows = get_coin_events_for_statistics()
    latest_status = get_latest_status() or {}
    connectivity = get_connectivity_latest(device_id="esp32")
    runtime = get_device_runtime()
    derived_events = _build_derived_coin_events(snapshot_rows)
    now_dt = datetime.now(timezone.utc)

    return {
        "snapshot_rows": snapshot_rows,
        "latest_status": latest_status,
        "connectivity": connectivity,
        "runtime": runtime,
        "derived_events": derived_events,
        "now_dt": now_dt,
    }


def _format_activity_timestamp(created_at: str | None) -> tuple[str, str, str]:
    timestamp = _parse_iso_datetime(created_at) or datetime.now(timezone.utc)
    return (
        timestamp.strftime("%b %d, %Y"),
        timestamp.strftime("%H:%M:%S"),
        timestamp.strftime("%H:%M"),
    )


def _status_meta(status_code: str) -> tuple[str, str]:
    status_key = (status_code or "").strip().lower()
    mapping = {
        "verified": ("Verified", "verified"),
        "seeded": ("Seeded", "seeded"),
        "granted": ("Granted", "granted"),
        "denied": ("Denied", "denied"),
        "offline": ("Offline", "offline"),
        "requested": ("Requested", "requested"),
        "applied": ("Applied", "granted"),
    }
    return mapping.get(status_key, (status_code or "Unknown", "neutral"))


def _action_meta(action_code: str) -> tuple[str, str]:
    action_key = (action_code or "").strip().lower()
    mapping = {
        "coin_deposit": ("Coin Deposit", "deposit"),
        "baseline_snapshot": ("Baseline Snapshot", "baseline"),
        "rfid_unlock": ("RFID Unlock", "unlock"),
        "web_unlock": ("Web Unlock", "unlock"),
        "reset_data": ("Reset Data", "system"),
        "rfid_card_added": ("RFID Card Added", "security"),
        "rfid_card_updated": ("RFID Card Updated", "security"),
        "rfid_card_removed": ("RFID Card Removed", "security"),
        "rfid_enroll_mode_on": ("Enroll Mode On", "security"),
        "rfid_enroll_mode_off": ("Enroll Mode Off", "security"),
    }
    return mapping.get(action_key, (action_code.replace("_", " ").title() if action_code else "Activity", "system"))


def _reason_label(reason_code: str | None) -> str | None:
    if not reason_code:
        return None

    reason_key = str(reason_code).strip().upper()
    mapping = {
        "ALLOW": "Card accepted",
        "UID_NOT_AUTHORIZED": "Card not enrolled",
        "WIFI_DISCONNECTED": "Device offline",
        "WEB_UNLOCK": "Unlock applied on device",
        "RESET": "Reset applied on device",
        "CARD_ADDED": "Authorized card added",
        "CARD_UPDATED": "Authorized card updated",
        "CARD_REMOVED": "Authorized card removed",
        "ENROLL_MODE_ON": "Scan mode enabled",
        "ENROLL_MODE_OFF": "Scan mode disabled",
    }
    return mapping.get(reason_key, reason_key.replace("_", " ").title())


def _find_card_by_id(card_id: int) -> dict | None:
    for card in list_rfid_cards(active_only=False):
        if int(card.get("id", 0)) == int(card_id):
            return card
    return None


def _card_label(card: dict | None) -> str:
    if not card:
        return "Unknown card"

    owner_name = (card.get("owner_name") or "").strip() if isinstance(card.get("owner_name"), str) else card.get("owner_name")
    uid = card.get("uid") or "unknown uid"
    if owner_name:
        return f"{owner_name} ({uid})"
    return str(uid)


def _build_transaction_rows(derived_events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    row_id = 1

    for event in reversed(derived_events):
        timestamp = event["timestamp"]
        for denomination in sorted(COIN_DENOMINATIONS, reverse=True):
            count = int(event["counts"].get(denomination, 0))
            if count <= 0:
                continue

            seeded = bool(event.get("seeded"))
            status, status_code = _status_meta("seeded" if seeded else "verified")
            action, action_code = _action_meta("baseline_snapshot" if seeded else "coin_deposit")
            rows.append({
                "id": f"deposit-{row_id}",
                "entry_type": "deposit",
                "created_at": event["created_at"],
                "date_label": timestamp.strftime("%b %d, %Y"),
                "time_label": timestamp.strftime("%H:%M:%S"),
                "hour_label": timestamp.strftime("%H:%M"),
                "coin_value": denomination,
                "coin_label": f"{denomination} Baht Coin",
                "count": count,
                "value": denomination * count,
                "status": status,
                "status_code": status_code,
                "action": action,
                "action_code": action_code,
                "detail": (
                    "Imported from the first cumulative snapshot."
                    if seeded else
                    f"{count} coin{'s' if count > 1 else ''} detected in this deposit event."
                ),
                "seeded": seeded,
            })
            row_id += 1

    return rows


def _build_access_transaction_rows(access_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for row in access_rows:
        if row.get("access_granted"):
            status, status_code = _status_meta("granted")
        elif str(row.get("reason") or "").upper() == "WIFI_DISCONNECTED":
            status, status_code = _status_meta("offline")
        else:
            status, status_code = _status_meta("denied")

        action, action_code = _action_meta("rfid_unlock")
        date_label, time_label, hour_label = _format_activity_timestamp(row.get("created_at"))
        uid_text = row.get("uid") or "Unknown UID"

        rows.append({
            "id": f"access-{row.get('id')}",
            "entry_type": "access",
            "created_at": row.get("created_at"),
            "date_label": date_label,
            "time_label": time_label,
            "hour_label": hour_label,
            "coin_value": None,
            "coin_label": "RFID Card",
            "count": None,
            "value": None,
            "status": status,
            "status_code": status_code,
            "action": action,
            "action_code": action_code,
            "detail": uid_text,
            "reason": row.get("reason"),
            "reason_label": _reason_label(row.get("reason")),
        })

    return rows


def _build_activity_transaction_rows(activity_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for row in activity_rows:
        action, action_code = _action_meta(row.get("action", ""))
        status, status_code = _status_meta(row.get("status", ""))
        date_label, time_label, hour_label = _format_activity_timestamp(row.get("created_at"))

        if action_code == "unlock":
            coin_label = "Web Dashboard"
        elif action_code == "security":
            coin_label = "RFID Access List"
        else:
            coin_label = "System Event"

        rows.append({
            "id": f"activity-{row.get('id')}",
            "entry_type": "activity",
            "created_at": row.get("created_at"),
            "date_label": date_label,
            "time_label": time_label,
            "hour_label": hour_label,
            "coin_value": None,
            "coin_label": coin_label,
            "count": None,
            "value": None,
            "status": status,
            "status_code": status_code,
            "action": action,
            "action_code": action_code,
            "detail": row.get("details") or row.get("reason") or row.get("source") or "Activity logged",
            "reason": row.get("reason"),
            "reason_label": _reason_label(row.get("reason")),
        })

    return rows


def _sort_transaction_rows(rows: list[dict]) -> list[dict]:
    def sort_key(row: dict) -> tuple[datetime, int, int]:
        timestamp = _parse_iso_datetime(row.get("created_at")) or datetime.fromtimestamp(0, tz=timezone.utc)
        if row.get("entry_type") == "deposit":
            priority = 0
        elif row.get("entry_type") == "access":
            priority = 1
        else:
            priority = 2
        coin_value = _safe_int(row.get("coin_value"), 0)
        return (timestamp, priority, coin_value)

    return sorted(rows, key=sort_key, reverse=True)


def _derive_peak_deposit_time(derived_events: list[dict]) -> str | None:
    if not derived_events:
        return None

    buckets: dict[str, int] = {}
    for event in derived_events:
        label = event["timestamp"].strftime("%H:%M")
        buckets[label] = buckets.get(label, 0) + 1

    return max(buckets.items(), key=lambda item: (item[1], item[0]))[0]


def _build_statistics_payload() -> dict:
    context = _collect_timeseries_context()
    snapshot_rows = context["snapshot_rows"]
    latest_status = context["latest_status"]
    connectivity = context["connectivity"]
    runtime = context["runtime"]
    derived_events = context["derived_events"]
    now_dt = context["now_dt"]

    distribution_counts = {denomination: 0 for denomination in COIN_DENOMINATIONS}
    total_value = 0
    total_coins = 0
    for event in derived_events:
        total_value += event["value"]
        total_coins += event["coin_count"]
        for denomination in COIN_DENOMINATIONS:
            distribution_counts[denomination] += event["counts"][denomination]

    most_frequent_value = None
    most_frequent_count = 0
    if total_coins > 0:
        most_frequent_value, most_frequent_count = max(
            distribution_counts.items(),
            key=lambda item: (item[1], item[0]),
        )

    avg_coin_value = (total_value / total_coins) if total_coins else 0.0
    last_30_start = now_dt - timedelta(days=29)
    prev_30_start = last_30_start - timedelta(days=30)
    prev_30_end = last_30_start - timedelta(seconds=1)
    recent_30_value, recent_30_coins = _period_totals(derived_events, last_30_start, now_dt)
    previous_30_value, previous_30_coins = _period_totals(derived_events, prev_30_start, prev_30_end)

    last_7_start = now_dt - timedelta(days=6)
    prev_7_start = last_7_start - timedelta(days=7)
    prev_7_end = last_7_start - timedelta(seconds=1)
    recent_7_value, recent_7_coins = _period_totals(derived_events, last_7_start, now_dt)
    previous_7_value, previous_7_coins = _period_totals(derived_events, prev_7_start, prev_7_end)

    current_balance = _safe_int(latest_status.get("total"), total_value)
    fill_percent = max(0.0, min(100.0, _safe_float(latest_status.get("fill_percent"), 0.0)))
    is_locked = True if latest_status.get("is_locked") is None else bool(latest_status.get("is_locked"))
    wifi_connected = bool(connectivity.get("is_connected", latest_status.get("wifi_connected", False)))

    return {
        "summary": {
            "total_coins_counted": total_coins,
            "total_value": total_value,
            "average_coin_value": round(avg_coin_value, 2),
            "most_frequent_coin": {
                "value": most_frequent_value,
                "count": most_frequent_count,
            },
            "coins_vs_previous_30d_percent": round(_percent_change(recent_30_coins, previous_30_coins), 1),
            "coins_last_30d": recent_30_coins,
            "coins_previous_30d": previous_30_coins,
        },
        "savings_growth": {
            "7d": _build_savings_growth_series(derived_events, days=7, now_dt=now_dt),
            "30d": _build_savings_growth_series(derived_events, days=30, now_dt=now_dt),
        },
        "coin_distribution": {
            "counts": {str(denomination): distribution_counts[denomination] for denomination in COIN_DENOMINATIONS},
            "values": {
                str(denomination): distribution_counts[denomination] * denomination
                for denomination in COIN_DENOMINATIONS
            },
            "total_count": total_coins,
            "total_value": total_value,
        },
        "insights": {
            "growth_velocity_percent": round(_percent_change(recent_7_value, previous_7_value), 1),
            "avg_coin_value": round(avg_coin_value, 2),
            "vault_capacity_percent": round(fill_percent),
            "security_status": "Secure" if is_locked else "Unlocked",
            "lock_status": "Locked" if is_locked else "Unlocked",
            "current_balance": current_balance,
            "recent_7d_value": recent_7_value,
            "recent_7d_coins": recent_7_coins,
        },
        "device": {
            "wifi_connected": wifi_connected,
            "is_locked": is_locked,
            "last_seen_at": connectivity.get("last_seen_at") or latest_status.get("last_seen_at"),
            "wifi_ssid": runtime.get("wifi_ssid"),
            "esp32_ip": runtime.get("esp32_ip"),
        },
        "meta": {
            "recorded_snapshots": len(snapshot_rows),
            "derived_deposit_events": len(derived_events),
            "has_coin_data": total_coins > 0,
            "generated_at": now_dt.isoformat().replace("+00:00", "Z"),
        },
    }


def _build_transactions_payload() -> dict:
    context = _collect_timeseries_context()
    snapshot_rows = context["snapshot_rows"]
    derived_events = context["derived_events"]
    now_dt = context["now_dt"]
    statistics = _build_statistics_payload()
    access_rows = _build_access_transaction_rows(get_access_history(limit=250))
    activity_rows = _build_activity_transaction_rows(get_activity_history(limit=250))
    transaction_rows = _sort_transaction_rows(
        _build_transaction_rows(derived_events) + access_rows + activity_rows
    )

    month_value = 0
    for event in derived_events:
        timestamp = event["timestamp"]
        if timestamp.year == now_dt.year and timestamp.month == now_dt.month:
            month_value += event["value"]

    return {
        "hero": {
            "total_secured_savings": statistics["summary"]["total_value"],
            "this_month_value": month_value,
            "verified_deposits": len(derived_events),
            "coins_counted": statistics["summary"]["total_coins_counted"],
            "peak_deposit_time": _derive_peak_deposit_time(derived_events),
        },
        "transactions": transaction_rows,
        "device": statistics["device"],
        "meta": {
            "total_entries": len(transaction_rows),
            "recorded_snapshots": len(snapshot_rows),
            "has_transactions": len(transaction_rows) > 0,
            "generated_at": now_dt.isoformat().replace("+00:00", "Z"),
        },
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
        device_settings = get_device_settings()
        latest_status = get_latest_status() or {}
        connectivity = get_connectivity_latest(device_id="esp32")
        refresh_interval_ms = int(device_settings.get("dashboard_update_ms") or 5000)
        dashboard_url = _public_http_url(PUBLIC_DASHBOARD_HOST, PUBLIC_DASHBOARD_PORT)
        api_url = _public_http_url(PUBLIC_DASHBOARD_HOST, API_PORT)

        return jsonify({
            "device_id": latest_status.get("device_id") or runtime.get("device_id") or "esp32",
            "wifi_ssid": runtime.get("wifi_ssid") or os.getenv("WIFI_SSID", "Unknown"),
            "local_ip": _best_effort_local_ip(),
            "backend_container_ip": _best_effort_local_ip(),
            "esp32_ip": runtime.get("esp32_ip") or latest_status.get("esp32_ip") or "Unknown",
            "connection_status": connectivity.get("current_state", "UNKNOWN"),
            "wifi_connected": bool(connectivity.get("is_connected", False)),
            "last_seen_at": connectivity.get("last_seen_at"),
            "dashboard_refresh_sec": max(1, min(10, refresh_interval_ms // 1000)),
            "dashboard_host": PUBLIC_DASHBOARD_HOST or None,
            "dashboard_url": dashboard_url,
            "api_url": api_url,
            "backend_host": socket.gethostname(),
        })

    @app.post("/api/device/refresh-interval")
    def update_refresh_interval():
        payload = request.get_json(silent=True) or {}
        device_id = payload.get("device_id", "esp32")

        try:
            refresh_interval_sec = int(payload.get("interval_sec", 5))
        except Exception:
            refresh_interval_sec = 5

        refresh_interval_sec = max(1, min(10, refresh_interval_sec))
        sent = publish_dashboard_interval_command(device_id=device_id, interval_sec=refresh_interval_sec)
        if not sent:
            return jsonify({
                "error": "failed to send refresh interval command to device",
                "instance": _instance_info(),
            }), 503

        state = set_device_refresh_interval(device_id=device_id, dashboard_update_ms=refresh_interval_sec * 1000)
        return jsonify({
            "command_sent": True,
            "device_id": device_id,
            "dashboard_refresh_sec": refresh_interval_sec,
            "dashboard_update_ms": state.get("dashboard_update_ms", refresh_interval_sec * 1000),
            "updated_at": state.get("updated_at"),
            "instance": _instance_info(),
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

    @app.get("/api/statistics")
    def statistics():
        return jsonify(_build_statistics_payload())

    @app.get("/api/transactions")
    def transactions():
        return jsonify(_build_transactions_payload())

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

        log_activity_event(
            event_type="security",
            action="RFID_CARD_ADDED",
            status="APPLIED",
            source="web",
            uid=card.get("uid"),
            reason="CARD_ADDED",
            details=f"Authorized RFID card added: {_card_label(card)}",
        )
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

        existing_card = _find_card_by_id(card_id)

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

        previous_label = _card_label(existing_card)
        next_label = _card_label(card)
        log_activity_event(
            event_type="security",
            action="RFID_CARD_UPDATED",
            status="APPLIED",
            source="web",
            uid=card.get("uid"),
            reason="CARD_UPDATED",
            details=f"Authorized RFID card updated: {previous_label} -> {next_label}",
        )
        return jsonify({"card": card})

    @app.delete("/api/rfid/cards/<int:card_id>")
    def delete_rfid_card_route(card_id: int):
        existing_card = _find_card_by_id(card_id)
        deleted = deactivate_rfid_card_by_id(card_id)
        if not deleted:
            return jsonify({"error": "card not found"}), 404

        log_activity_event(
            event_type="security",
            action="RFID_CARD_REMOVED",
            status="APPLIED",
            source="web",
            uid=(existing_card or {}).get("uid"),
            reason="CARD_REMOVED",
            details=f"Authorized RFID card removed: {_card_label(existing_card)}",
        )
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

        log_activity_event(
            event_type="security",
            action="RFID_ENROLL_MODE_ON" if active else "RFID_ENROLL_MODE_OFF",
            status="APPLIED",
            source="web",
            reason="ENROLL_MODE_ON" if active else "ENROLL_MODE_OFF",
            details=(
                "RFID scan mode enabled from Settings."
                if active else
                "RFID scan mode disabled from Settings."
            ),
        )

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

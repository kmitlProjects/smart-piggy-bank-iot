import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import DB_PATH, DATA_DIR


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS latest_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    device_id TEXT,
    wifi_connected INTEGER NOT NULL DEFAULT 0,
    is_locked INTEGER NOT NULL DEFAULT 1,
    distance_cm REAL,
    is_full INTEGER,
    estimated_total REAL,
    estimated_coin_count INTEGER,
    fill_percent REAL,
    total INTEGER,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coin_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    coin_1 INTEGER NOT NULL DEFAULT 0,
    coin_2 INTEGER NOT NULL DEFAULT 0,
    coin_5 INTEGER NOT NULL DEFAULT 0,
    coin_10 INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    distance_cm REAL,
    is_full INTEGER,
    estimated_total REAL,
    estimated_coin_count INTEGER,
    fill_percent REAL,
    wifi_connected INTEGER,
    is_locked INTEGER,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rfid_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL UNIQUE,
    owner_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT,
    wifi_connected INTEGER NOT NULL DEFAULT 0,
    authorized INTEGER NOT NULL DEFAULT 0,
    access_granted INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    uid TEXT,
    reason TEXT,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connectivity_state (
    device_id TEXT PRIMARY KEY,
    current_state TEXT NOT NULL,
    last_seen_at TEXT,
    changed_at TEXT NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS connectivity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    event TEXT NOT NULL,
    reason TEXT NOT NULL,
    last_seen_at TEXT,
    timeout_seconds INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_runtime (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    device_id TEXT,
    wifi_ssid TEXT,
    esp32_ip TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    device_id TEXT,
    dashboard_update_ms INTEGER NOT NULL DEFAULT 5000,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rfid_enrollment_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    active INTEGER NOT NULL DEFAULT 0,
    pending_uid TEXT,
    last_scanned_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rfid_scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = value if isinstance(value, str) else str(value)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _insert_connectivity_event(
    conn: sqlite3.Connection,
    device_id: str,
    event: str,
    reason: str,
    last_seen_at: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO connectivity_events (device_id, event, reason, last_seen_at, timeout_seconds, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (device_id, event, reason, last_seen_at, timeout_seconds, _now_iso()),
    )


def mark_device_seen(device_id: str, reason: str = "HEARTBEAT") -> None:
    now = _now_iso()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT device_id, current_state, last_seen_at FROM connectivity_state WHERE device_id = ?",
            (device_id,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO connectivity_state (device_id, current_state, last_seen_at, changed_at, reason)
                VALUES (?, 'CONNECTED', ?, ?, ?)
                """,
                (device_id, now, now, reason),
            )
            _insert_connectivity_event(conn, device_id, "CONNECTED", reason, last_seen_at=now)
        elif row["current_state"] == "DISCONNECTED":
            conn.execute(
                """
                UPDATE connectivity_state
                SET current_state = 'CONNECTED', last_seen_at = ?, changed_at = ?, reason = ?
                WHERE device_id = ?
                """,
                (now, now, reason, device_id),
            )
            _insert_connectivity_event(conn, device_id, "RECONNECTED", reason, last_seen_at=now)
        else:
            conn.execute(
                "UPDATE connectivity_state SET last_seen_at = ? WHERE device_id = ?",
                (now, device_id),
            )

        conn.commit()
    finally:
        conn.close()


def process_connectivity_timeout(timeout_seconds: int, device_id: str = "esp32") -> bool:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT device_id, current_state, last_seen_at FROM connectivity_state WHERE device_id = ?",
            (device_id,),
        ).fetchone()

        if row is None or row["current_state"] != "CONNECTED":
            return False

        last_seen = _parse_iso(row["last_seen_at"])
        if last_seen is None:
            return False

        now_dt = _utc_now()
        delta = (now_dt - last_seen).total_seconds()
        if delta <= timeout_seconds:
            return False

        now_iso = _now_iso()
        conn.execute(
            """
            UPDATE connectivity_state
            SET current_state = 'DISCONNECTED', changed_at = ?, reason = ?
            WHERE device_id = ?
            """,
            (now_iso, "TIMEOUT", device_id),
        )
        _insert_connectivity_event(
            conn,
            device_id,
            "DISCONNECTED",
            "TIMEOUT",
            last_seen_at=row["last_seen_at"],
            timeout_seconds=timeout_seconds,
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_connectivity_latest(device_id: str = "esp32") -> Dict[str, Any]:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT device_id, current_state, last_seen_at, changed_at, reason FROM connectivity_state WHERE device_id = ?",
            (device_id,),
        ).fetchone()

        if row is None:
            return {
                "device_id": device_id,
                "current_state": "UNKNOWN",
                "is_connected": False,
                "last_seen_at": None,
                "changed_at": None,
                "reason": "NO_HEARTBEAT",
                "seconds_since_last_seen": None,
            }

        data = _to_dict(row)
        data["is_connected"] = data["current_state"] == "CONNECTED"

        last_seen = _parse_iso(data.get("last_seen_at"))
        if last_seen is None:
            data["seconds_since_last_seen"] = None
        else:
            now_dt = _utc_now()
            data["seconds_since_last_seen"] = int((now_dt - last_seen).total_seconds())
        return data
    finally:
        conn.close()


def get_connectivity_history(limit: int = 100, device_id: str = "esp32") -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, device_id, event, reason, last_seen_at, timeout_seconds, created_at
            FROM connectivity_events
            WHERE device_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def _uid_to_text(uid: Any) -> str:
    if isinstance(uid, list):
        return str(uid)

    if uid is None:
        return ""

    return str(uid).strip()


def _sanitize_dashboard_update_ms(value: Any, default: int = 5000) -> int:
    try:
        numeric_value = int(value)
    except Exception:
        numeric_value = default

    return max(1000, min(10000, numeric_value))


def upsert_device_runtime(payload: Dict[str, Any], device_id: str) -> None:
    wifi_ssid = payload.get("wifi_ssid")
    esp32_ip = payload.get("esp32_ip")
    dashboard_update_ms = payload.get("dashboard_update_ms")

    if wifi_ssid is not None or esp32_ip is not None:
        conn = _conn()
        try:
            conn.execute(
                """
                INSERT INTO device_runtime (id, device_id, wifi_ssid, esp32_ip, updated_at)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    device_id = excluded.device_id,
                    wifi_ssid = COALESCE(excluded.wifi_ssid, device_runtime.wifi_ssid),
                    esp32_ip = COALESCE(excluded.esp32_ip, device_runtime.esp32_ip),
                    updated_at = excluded.updated_at
                """,
                (device_id, wifi_ssid, esp32_ip, _now_iso()),
            )
            conn.commit()
        finally:
            conn.close()

    if dashboard_update_ms is not None:
        set_device_refresh_interval(
            device_id=device_id,
            dashboard_update_ms=_sanitize_dashboard_update_ms(dashboard_update_ms),
        )


def get_device_runtime() -> Dict[str, Any]:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT device_id, wifi_ssid, esp32_ip, updated_at FROM device_runtime WHERE id = 1"
        ).fetchone()
        return _to_dict(row) if row else {}
    finally:
        conn.close()


def set_device_refresh_interval(device_id: str, dashboard_update_ms: int) -> Dict[str, Any]:
    now = _now_iso()
    safe_value = _sanitize_dashboard_update_ms(dashboard_update_ms)
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO device_settings (id, device_id, dashboard_update_ms, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                device_id = excluded.device_id,
                dashboard_update_ms = excluded.dashboard_update_ms,
                updated_at = excluded.updated_at
            """,
            (device_id, safe_value, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT device_id, dashboard_update_ms, updated_at FROM device_settings WHERE id = 1"
        ).fetchone()
        return _to_dict(row) if row else {}
    finally:
        conn.close()


def get_device_settings() -> Dict[str, Any]:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT device_id, dashboard_update_ms, updated_at FROM device_settings WHERE id = 1"
        ).fetchone()
        return _to_dict(row) if row else {}
    finally:
        conn.close()


def set_rfid_enrollment_state(active: bool, pending_uid: Optional[str] = None) -> Dict[str, Any]:
    now = _now_iso()
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO rfid_enrollment_state (id, active, pending_uid, last_scanned_at, updated_at)
            VALUES (1, ?, ?, NULL, ?)
            ON CONFLICT(id) DO UPDATE SET
                active = excluded.active,
                pending_uid = excluded.pending_uid,
                last_scanned_at = CASE
                    WHEN excluded.pending_uid IS NULL THEN NULL
                    ELSE rfid_enrollment_state.last_scanned_at
                END,
                updated_at = excluded.updated_at
            """,
            (int(bool(active)), pending_uid, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT active, pending_uid, last_scanned_at, updated_at FROM rfid_enrollment_state WHERE id = 1"
        ).fetchone()
        data = _to_dict(row)
        data["active"] = bool(data.get("active"))
        return data
    finally:
        conn.close()


def record_rfid_scan(uid: Any, source: str = "esp32_enroll") -> Dict[str, Any]:
    uid_text = _uid_to_text(uid)
    now = _now_iso()
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO rfid_scan_events (uid, source, created_at)
            VALUES (?, ?, ?)
            """,
            (uid_text, source, now),
        )
        conn.execute(
            """
            INSERT INTO rfid_enrollment_state (id, active, pending_uid, last_scanned_at, updated_at)
            VALUES (1, 1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                pending_uid = excluded.pending_uid,
                last_scanned_at = excluded.last_scanned_at,
                updated_at = excluded.updated_at
            """,
            (uid_text, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT active, pending_uid, last_scanned_at, updated_at FROM rfid_enrollment_state WHERE id = 1"
        ).fetchone()
        data = _to_dict(row)
        data["active"] = bool(data.get("active"))
        return data
    finally:
        conn.close()


def clear_pending_rfid_scan() -> Dict[str, Any]:
    now = _now_iso()
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO rfid_enrollment_state (id, active, pending_uid, last_scanned_at, updated_at)
            VALUES (1, 0, NULL, NULL, ?)
            ON CONFLICT(id) DO UPDATE SET
                pending_uid = NULL,
                last_scanned_at = NULL,
                updated_at = excluded.updated_at
            """,
            (now,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT active, pending_uid, last_scanned_at, updated_at FROM rfid_enrollment_state WHERE id = 1"
        ).fetchone()
        data = _to_dict(row)
        data["active"] = bool(data.get("active"))
        return data
    finally:
        conn.close()


def get_rfid_enrollment_state() -> Dict[str, Any]:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT active, pending_uid, last_scanned_at, updated_at FROM rfid_enrollment_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return {
                "active": False,
                "pending_uid": None,
                "last_scanned_at": None,
                "updated_at": None,
            }
        data = _to_dict(row)
        data["active"] = bool(data.get("active"))
        return data
    finally:
        conn.close()


def add_rfid_card(uid: str, owner_name: Optional[str] = None) -> Dict[str, Any]:
    uid_text = _uid_to_text(uid)
    if not uid_text:
        raise ValueError("uid is required")

    now = _now_iso()
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO rfid_cards (uid, owner_name, is_active, created_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(uid) DO UPDATE SET
                owner_name = excluded.owner_name,
                is_active = 1
            """,
            (uid_text, owner_name, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM rfid_cards WHERE uid = ?", (uid_text,)).fetchone()
        return _to_dict(row)
    finally:
        conn.close()


def update_rfid_card(card_id: int, uid: str, owner_name: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    uid_text = _uid_to_text(uid)
    if not uid_text:
        raise ValueError("uid is required")

    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM rfid_cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            return None

        active_value = row["is_active"] if is_active is None else int(bool(is_active))
        conn.execute(
            """
            UPDATE rfid_cards
            SET uid = ?, owner_name = ?, is_active = ?
            WHERE id = ?
            """,
            (uid_text, owner_name, active_value, card_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM rfid_cards WHERE id = ?", (card_id,)).fetchone()
        return _to_dict(updated) if updated else None
    finally:
        conn.close()


def deactivate_rfid_card(uid: str) -> bool:
    uid_text = _uid_to_text(uid)
    conn = _conn()
    try:
        cur = conn.execute("UPDATE rfid_cards SET is_active = 0 WHERE uid = ?", (uid_text,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def deactivate_rfid_card_by_id(card_id: int) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("UPDATE rfid_cards SET is_active = 0 WHERE id = ?", (card_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_rfid_cards(active_only: bool = False) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        if active_only:
            rows = conn.execute(
                """
                SELECT id, uid, owner_name, is_active, created_at
                FROM rfid_cards
                WHERE is_active = 1
                ORDER BY id DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, uid, owner_name, is_active, created_at FROM rfid_cards ORDER BY id DESC"
            ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def is_card_authorized(uid: Any) -> bool:
    uid_text = _uid_to_text(uid)
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM rfid_cards WHERE uid = ? AND is_active = 1 LIMIT 1",
            (uid_text,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def log_access(uid: Any, wifi_connected: bool, authorized: bool, access_granted: bool, reason: str) -> None:
    conn = _conn()
    try:
        uid_text = _uid_to_text(uid)
        conn.execute(
            """
            INSERT INTO access_logs (uid, wifi_connected, authorized, access_granted, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uid_text, int(bool(wifi_connected)), int(bool(authorized)), int(bool(access_granted)), reason, _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def check_access(uid: Any, wifi_connected: bool) -> Dict[str, Any]:
    authorized = is_card_authorized(uid)
    granted = bool(wifi_connected) and authorized

    if granted:
        reason = "ALLOW"
    elif not wifi_connected:
        reason = "WIFI_DISCONNECTED"
    else:
        reason = "UID_NOT_AUTHORIZED"

    log_access(uid=uid, wifi_connected=wifi_connected, authorized=authorized, access_granted=granted, reason=reason)

    return {
        "uid": uid,
        "wifi_connected": bool(wifi_connected),
        "authorized": authorized,
        "access_granted": granted,
        "reason": reason,
    }


def upsert_latest_status(payload: Dict[str, Any], device_id: str) -> None:
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO latest_status (
                id, device_id, wifi_connected, is_locked, distance_cm, is_full,
                estimated_total, estimated_coin_count, fill_percent, total, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                device_id = excluded.device_id,
                wifi_connected = excluded.wifi_connected,
                is_locked = excluded.is_locked,
                distance_cm = excluded.distance_cm,
                is_full = excluded.is_full,
                estimated_total = excluded.estimated_total,
                estimated_coin_count = excluded.estimated_coin_count,
                fill_percent = excluded.fill_percent,
                total = excluded.total,
                updated_at = excluded.updated_at
            """,
            (
                device_id,
                int(bool(payload.get("wifi_connected", False))),
                int(bool(payload.get("is_locked", True))),
                payload.get("distance_cm"),
                None if payload.get("is_full") is None else int(bool(payload.get("is_full"))),
                payload.get("estimated_total"),
                payload.get("estimated_coin_count"),
                payload.get("fill_percent"),
                payload.get("total", 0),
                _now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_coin_event(payload: Dict[str, Any], source: str = "mqtt", device_id: str = "esp32") -> None:
    coins = payload.get("coins") or {}
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO coin_events (
                device_id, coin_1, coin_2, coin_5, coin_10, total,
                distance_cm, is_full, estimated_total, estimated_coin_count,
                fill_percent, wifi_connected, is_locked, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                int(coins.get("1", 0)),
                int(coins.get("2", 0)),
                int(coins.get("5", 0)),
                int(coins.get("10", 0)),
                int(payload.get("total", 0)),
                payload.get("distance_cm"),
                None if payload.get("is_full") is None else int(bool(payload.get("is_full"))),
                payload.get("estimated_total"),
                payload.get("estimated_coin_count"),
                payload.get("fill_percent"),
                int(bool(payload.get("wifi_connected", False))),
                int(bool(payload.get("is_locked", True))),
                source,
                _now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_status() -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM latest_status WHERE id = 1").fetchone()
        return _to_dict(row) if row else None
    finally:
        conn.close()


def get_coin_summary() -> Dict[str, Any]:
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT
                coin_1,
                coin_2,
                coin_5,
                coin_10,
                total
            FROM coin_events
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if row:
            data = _to_dict(row)
            data["events"] = conn.execute("SELECT COUNT(*) AS c FROM coin_events").fetchone()["c"]
            return data

        return {
            "coin_1": 0,
            "coin_2": 0,
            "coin_5": 0,
            "coin_10": 0,
            "total": 0,
            "events": 0,
        }
    finally:
        conn.close()


def get_coin_history(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, device_id, coin_1, coin_2, coin_5, coin_10, total,
                   distance_cm, is_full, estimated_total, estimated_coin_count,
                   fill_percent, wifi_connected, is_locked, source, created_at
            FROM coin_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_coin_events_for_statistics() -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, device_id, coin_1, coin_2, coin_5, coin_10, total,
                   distance_cm, is_full, estimated_total, estimated_coin_count,
                   fill_percent, wifi_connected, is_locked, source, created_at
            FROM coin_events
            ORDER BY id ASC
            """
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_access_history(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, uid, wifi_connected, authorized, access_granted, reason, created_at FROM access_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def log_activity_event(
    event_type: str,
    action: str,
    status: str,
    source: str,
    uid: Any = None,
    reason: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    uid_text = _uid_to_text(uid) if uid is not None else None
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO activity_events (event_type, action, status, source, uid, reason, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_type, action, status, source, uid_text, reason, details, _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def get_activity_history(limit: int = 100) -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, event_type, action, status, source, uid, reason, details, created_at
            FROM activity_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def reset_database(clear_cards: bool = False) -> Dict[str, int]:
    conn = _conn()
    try:
        deleted_coin_events = conn.execute("DELETE FROM coin_events").rowcount
        deleted_access_logs = conn.execute("DELETE FROM access_logs").rowcount
        deleted_activity_events = conn.execute("DELETE FROM activity_events").rowcount
        deleted_status = conn.execute("DELETE FROM latest_status").rowcount
        deleted_device_runtime = conn.execute("DELETE FROM device_runtime").rowcount
        deleted_device_settings = conn.execute("DELETE FROM device_settings").rowcount
        deleted_enrollment_state = conn.execute("DELETE FROM rfid_enrollment_state").rowcount
        deleted_scan_events = conn.execute("DELETE FROM rfid_scan_events").rowcount
        deleted_connectivity_state = conn.execute("DELETE FROM connectivity_state").rowcount
        deleted_connectivity_events = conn.execute("DELETE FROM connectivity_events").rowcount
        deleted_cards = 0
        if clear_cards:
            deleted_cards = conn.execute("DELETE FROM rfid_cards").rowcount
        conn.commit()
        return {
            "coin_events": deleted_coin_events,
            "access_logs": deleted_access_logs,
            "activity_events": deleted_activity_events,
            "latest_status": deleted_status,
            "device_runtime": deleted_device_runtime,
            "device_settings": deleted_device_settings,
            "rfid_enrollment_state": deleted_enrollment_state,
            "rfid_scan_events": deleted_scan_events,
            "connectivity_state": deleted_connectivity_state,
            "connectivity_events": deleted_connectivity_events,
            "rfid_cards": deleted_cards,
        }
    finally:
        conn.close()

import os
import sqlite3
from datetime import datetime
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


def add_rfid_card(uid: str, owner_name: Optional[str] = None) -> Dict[str, Any]:
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
            (uid, owner_name, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM rfid_cards WHERE uid = ?", (uid,)).fetchone()
        return _to_dict(row)
    finally:
        conn.close()


def deactivate_rfid_card(uid: str) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("UPDATE rfid_cards SET is_active = 0 WHERE uid = ?", (uid,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_rfid_cards() -> List[Dict[str, Any]]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, uid, owner_name, is_active, created_at FROM rfid_cards ORDER BY id DESC"
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def is_card_authorized(uid: str) -> bool:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM rfid_cards WHERE uid = ? AND is_active = 1 LIMIT 1", (uid,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def log_access(uid: str, wifi_connected: bool, authorized: bool, access_granted: bool, reason: str) -> None:
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO access_logs (uid, wifi_connected, authorized, access_granted, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uid, int(bool(wifi_connected)), int(bool(authorized)), int(bool(access_granted)), reason, _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def check_access(uid: str, wifi_connected: bool) -> Dict[str, Any]:
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
                COALESCE(MAX(coin_1), 0) AS coin_1,
                COALESCE(MAX(coin_2), 0) AS coin_2,
                COALESCE(MAX(coin_5), 0) AS coin_5,
                COALESCE(MAX(coin_10), 0) AS coin_10,
                COALESCE(MAX(total), 0) AS total,
                COALESCE(COUNT(*), 0) AS events
            FROM coin_events
            """
        ).fetchone()
        return _to_dict(row)
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


def reset_database(clear_cards: bool = False) -> Dict[str, int]:
    conn = _conn()
    try:
        deleted_coin_events = conn.execute("DELETE FROM coin_events").rowcount
        deleted_access_logs = conn.execute("DELETE FROM access_logs").rowcount
        deleted_status = conn.execute("DELETE FROM latest_status").rowcount
        deleted_cards = 0
        if clear_cards:
            deleted_cards = conn.execute("DELETE FROM rfid_cards").rowcount
        conn.commit()
        return {
            "coin_events": deleted_coin_events,
            "access_logs": deleted_access_logs,
            "latest_status": deleted_status,
            "rfid_cards": deleted_cards,
        }
    finally:
        conn.close()

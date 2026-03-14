import time

try:
    import ujson as json
except ImportError:
    import json

try:
    import urequests
except ImportError:
    urequests = None


class DashboardClient:
    def __init__(self, url, interval_ms=5000):
        self.url = url
        self.interval_ms = interval_ms
        self._last_sent_ms = 0

    def ready(self, now_ms):
        return time.ticks_diff(now_ms, self._last_sent_ms) >= self.interval_ms

    def send(self, payload, now_ms):
        if not self.url or urequests is None:
            self._last_sent_ms = now_ms
            return False

        response = None
        try:
            response = urequests.post(
                self.url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            self._last_sent_ms = now_ms
            return 200 <= response.status_code < 300
        except Exception as exc:
            print("Dashboard POST failed:", exc)
            self._last_sent_ms = now_ms
            return False
        finally:
            if response is not None:
                response.close()

    def send_if_due(self, payload, now_ms):
        if not self.ready(now_ms):
            return None
        return self.send(payload, now_ms)


def build_payload(
    total,
    counts,
    distance_cm,
    is_full_flag,
    is_locked,
    wifi_ok,
    estimated_coin_count=None,
    estimated_total=None,
    fill_percent=None,
):
    return {
        "total": total,
        "coins": {
            "1": counts.get("1", 0),
            "2": counts.get("2", 0),
            "5": counts.get("5", 0),
            "10": counts.get("10", 0),
        },
        "distance_cm": distance_cm,
        "fill_percent": fill_percent,
        "estimated_coin_count": estimated_coin_count,
        "estimated_total": estimated_total,
        "is_full": is_full_flag,
        "is_locked": is_locked,
        "wifi_connected": wifi_ok,
    }

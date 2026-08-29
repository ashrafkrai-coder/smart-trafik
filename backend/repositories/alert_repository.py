"""Akses Firestore bagi amaran kesesakan dan kamera."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from .common import require_db, server_timestamp, snapshot_to_dict


def create_alert(alert: dict[str, Any]) -> str:
    payload = {**alert, "is_resolved": False, "created_at": server_timestamp(), "resolved_at": None}
    _, reference = require_db().collection("traffic_alerts").add(payload)
    return reference.id


def get_active_alert(camera_id: str, alert_type: str) -> dict[str, Any] | None:
    # Sepadan dengan indeks camera_id/is_resolved/created_at. Penapisan jenis
    # dibuat pada set kecil dan terhad supaya tiada bacaan seluruh collection.
    query = (require_db().collection("traffic_alerts")
             .where(filter=FieldFilter("camera_id", "==", camera_id))
             .where(filter=FieldFilter("is_resolved", "==", False))
             .order_by("created_at", direction="DESCENDING").limit(20))
    return next((item for item in (snapshot_to_dict(value) for value in query.stream())
                 if item.get("alert_type") == alert_type), None)


def resolve_alert(alert_id: str) -> bool:
    reference = require_db().collection("traffic_alerts").document(alert_id)
    if not reference.get().exists:
        return False
    reference.set({"is_resolved": True, "resolved_at": server_timestamp()}, merge=True)
    return True


def get_recent_alerts(limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = min(max(int(limit), 1), 100)
    query = require_db().collection("traffic_alerts").order_by("created_at", direction="DESCENDING").limit(safe_limit)
    return [snapshot_to_dict(item) for item in query.stream()]

"""Akses terhad kepada keadaan trafik terkini dan sejarah."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from ..firebase_client import mark_firebase_failure
from .common import require_db, server_timestamp, snapshot_to_dict


def save_latest_traffic(data: dict[str, Any]) -> None:
    payload = dict(data)
    camera_id = str(payload["camera_id"])
    payload["updated_at"] = server_timestamp()
    try:
        require_db().collection("traffic_latest").document(camera_id).set(payload, merge=True)
    except Exception as exc:
        mark_firebase_failure(exc)
        raise


def save_traffic_record(data: dict[str, Any]) -> str:
    payload = dict(data)
    counts = payload.pop("counts", {})
    payload.update(car_count=int(counts.get("car", 0)), motorcycle_count=int(counts.get("motorcycle", 0)),
                   bus_count=int(counts.get("bus", 0)), truck_count=int(counts.get("truck", 0)),
                   recorded_at=server_timestamp())
    for key in ("updated_at", "connection_status", "fps"):
        payload.pop(key, None)
    try:
        _, reference = require_db().collection("traffic_records").add(payload)
        return reference.id
    except Exception as exc:
        mark_firebase_failure(exc)
        raise


def save_traffic_summary(data: dict[str, Any]) -> str:
    """Tulis latest dan satu rekod sejarah secara atomik dalam satu batch."""
    payload = dict(data)
    camera_id = str(payload["camera_id"])
    latest = {**payload, "updated_at": server_timestamp()}
    counts = payload.pop("counts", {})
    record = {
        **payload,
        "car_count": int(counts.get("car", 0)),
        "motorcycle_count": int(counts.get("motorcycle", 0)),
        "bus_count": int(counts.get("bus", 0)),
        "truck_count": int(counts.get("truck", 0)),
        "recorded_at": server_timestamp(),
    }
    for key in ("updated_at", "connection_status", "fps"):
        record.pop(key, None)
    try:
        db = require_db()
        latest_ref = db.collection("traffic_latest").document(camera_id)
        record_ref = db.collection("traffic_records").document()
        batch = db.batch()
        batch.set(latest_ref, latest, merge=True)
        batch.set(record_ref, record)
        batch.commit()
        return record_ref.id
    except Exception as exc:
        mark_firebase_failure(exc)
        raise


def get_latest_traffic(camera_id: str) -> dict[str, Any] | None:
    snapshot = require_db().collection("traffic_latest").document(camera_id).get()
    return snapshot_to_dict(snapshot) if snapshot.exists else None


def get_traffic_history(camera_id: str, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = min(max(int(limit), 1), 200)
    query = (require_db().collection("traffic_records").where(filter=FieldFilter("camera_id", "==", camera_id))
             .order_by("recorded_at", direction="DESCENDING").limit(safe_limit))
    return [snapshot_to_dict(item) for item in query.stream()]

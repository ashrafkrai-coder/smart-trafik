"""Akses Firestore bagi metadata kamera."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from .common import require_db, server_timestamp, snapshot_to_dict


def upsert_camera(camera: dict[str, Any]) -> None:
    payload = dict(camera)
    camera_id = str(payload.pop("camera_id"))
    payload["updated_at"] = server_timestamp()
    reference = require_db().collection("cameras").document(camera_id)
    if not reference.get().exists:
        payload["created_at"] = server_timestamp()
    reference.set(payload, merge=True)


def get_camera(camera_id: str) -> dict[str, Any] | None:
    snapshot = require_db().collection("cameras").document(camera_id).get()
    return snapshot_to_dict(snapshot) if snapshot.exists else None


def get_active_cameras(limit: int = 100) -> list[dict[str, Any]]:
    query = require_db().collection("cameras").where(
        filter=FieldFilter("is_active", "==", True)
    ).limit(min(max(limit, 1), 100))
    return [snapshot_to_dict(item) for item in query.stream()]

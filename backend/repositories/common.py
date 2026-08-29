"""Utiliti serialization dan akses Firestore yang dikongsi repository."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..firebase_client import get_firestore_client


class FirebaseUnavailableError(RuntimeError):
    pass


def require_db() -> Any:
    db = get_firestore_client()
    if db is None:
        raise FirebaseUnavailableError("Firebase Cloud Firestore tidak tersedia.")
    return db


def serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


def snapshot_to_dict(snapshot: Any) -> dict[str, Any]:
    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    return serialize_value(data)


def server_timestamp() -> Any:
    from firebase_admin import firestore
    return firestore.SERVER_TIMESTAMP

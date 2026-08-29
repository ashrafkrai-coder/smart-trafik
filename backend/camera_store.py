"""Stor JSON kecil dan thread-safe untuk metadata kamera yang boleh diedit."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

from . import config


class CameraRecord(TypedDict):
    camera_id: str
    camera_name: str
    location: str
    mode: str


DATA_FILE = config.PROJECT_ROOT / "data" / "cameras.json"
DEFAULT_CAMERAS: list[CameraRecord] = [
    {"camera_id": "CAM01", "camera_name": "Jalan Templer", "location": "Petaling Jaya", "mode": "live"},
    {"camera_id": "CAM02", "camera_name": "Lebuhraya Persekutuan", "location": "KM 12.4", "mode": "demo"},
    {"camera_id": "CAM03", "camera_name": "Persiaran Barat", "location": "Seksyen 52", "mode": "demo"},
    {"camera_id": "CAM04", "camera_name": "Jalan Utara", "location": "Pintu A", "mode": "demo"},
]

_lock = threading.RLock()
_cameras: list[CameraRecord] | None = None


def _load() -> list[CameraRecord]:
    """Muat data sah; gunakan default jika fail rosak atau tiada."""
    try:
        raw_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError("Data kamera bukan senarai")
        records: list[CameraRecord] = []
        for item in raw_data:
            records.append(
                {
                    "camera_id": str(item["camera_id"]),
                    "camera_name": str(item["camera_name"]),
                    "location": str(item["location"]),
                    "mode": str(item["mode"]),
                }
            )
        if not any(record["camera_id"] == "CAM01" for record in records):
            raise ValueError("CAM01 wajib tersedia")
        return records
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return deepcopy(DEFAULT_CAMERAS)


def list_cameras() -> list[CameraRecord]:
    global _cameras
    with _lock:
        if _cameras is None:
            _cameras = _load()
        return deepcopy(_cameras)


def get_camera(camera_id: str) -> CameraRecord | None:
    return next((camera for camera in list_cameras() if camera["camera_id"] == camera_id), None)


def update_camera(camera_id: str, camera_name: str, location: str) -> CameraRecord:
    """Kemas kini metadata dan tulis secara atomik agar fail tidak separuh siap."""
    global _cameras
    with _lock:
        if _cameras is None:
            _cameras = _load()
        camera = next((item for item in _cameras if item["camera_id"] == camera_id), None)
        if camera is None:
            raise KeyError(camera_id)
        camera["camera_name"] = camera_name
        camera["location"] = location
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = DATA_FILE.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(_cameras, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_file.replace(DATA_FILE)
        return deepcopy(camera)

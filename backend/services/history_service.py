"""Simpan ringkasan/heartbeat dan cipta amaran di luar thread inferens."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from .. import config
from ..firebase_client import get_firestore_client, initialize_firebase, is_firebase_connected, mark_firebase_failure
from ..repositories import alert_repository, camera_repository, traffic_repository
from ..repositories.common import server_timestamp

LOGGER = logging.getLogger(__name__)


class AlertCoordinator:
    """Deduplicate amaran menggunakan transition, cooldown tempatan dan semakan aktif."""

    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._last_created: dict[tuple[str, str], float] = {}

    def create_once(self, alert: dict[str, Any]) -> bool:
        key = (str(alert["camera_id"]), str(alert["alert_type"]))
        now = self._now()
        if now - self._last_created.get(key, -config.ALERT_COOLDOWN_SECONDS) < config.ALERT_COOLDOWN_SECONDS:
            return False
        if alert_repository.get_active_alert(*key) is not None:
            return False
        alert_repository.create_alert(alert)
        self._last_created[key] = now
        return True


class HistoryService:
    def __init__(self, video_processor: Any) -> None:
        self.video_processor = video_processor
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._alerts = AlertCoordinator()
        self._previous_traffic_status: str | None = None
        self._previous_connection = "offline"
        self._last_frame_at = time.monotonic()
        self._stale_alerted = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="smart-trafik-firestore", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        last_save = time.monotonic()
        last_heartbeat = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if config.FIREBASE_ENABLED and not is_firebase_connected():
                initialize_firebase()
            snapshot = self.video_processor.get_snapshot()
            if snapshot is not None:
                self._last_frame_at = now
                self._stale_alerted = False
                self._handle_snapshot_alerts(snapshot)
                self._previous_connection = "online"
                if is_firebase_connected() and now - last_save >= config.TRAFFIC_SAVE_INTERVAL_SECONDS:
                    try:
                        traffic_repository.save_traffic_summary(snapshot)
                        last_save = now
                    except Exception:
                        LOGGER.warning("Ringkasan trafik gagal disimpan; rekod kegagalan tidak dibuang secara senyap.")
            else:
                self._handle_offline_alert(now)
            if is_firebase_connected() and now - last_heartbeat >= config.SYSTEM_HEARTBEAT_INTERVAL_SECONDS:
                self._save_heartbeat()
                last_heartbeat = now
            self._stop.wait(1.0)

    def _handle_snapshot_alerts(self, snapshot: dict[str, Any]) -> None:
        current = str(snapshot.get("traffic_status"))
        if current == "Sangat Sesak" and self._previous_traffic_status != current:
            self._try_alert({
                "camera_id": snapshot["camera_id"], "alert_type": "severe_congestion", "severity": "high",
                "message": f"Trafik sangat sesak dikesan di {snapshot['camera_name']}",
                "traffic_status": current, "vehicle_count": snapshot["vehicle_count"],
            })
        self._previous_traffic_status = current

    def _handle_offline_alert(self, now: float) -> None:
        if self._previous_connection == "online":
            self._try_alert({
                "camera_id": config.CAMERA_ID, "alert_type": "camera_offline", "severity": "high",
                "message": f"Kamera {config.CAMERA_NAME} telah bertukar ke luar talian",
                "traffic_status": "Tidak tersedia", "vehicle_count": 0,
            })
            self._previous_connection = "offline"
        if not self._stale_alerted and now - self._last_frame_at >= config.FRAME_STALE_ALERT_SECONDS:
            self._try_alert({
                "camera_id": config.CAMERA_ID, "alert_type": "no_frames", "severity": "high",
                "message": f"Kamera {config.CAMERA_NAME} tidak menghantar frame",
                "traffic_status": "Tidak tersedia", "vehicle_count": 0,
            })
            self._stale_alerted = True

    def _try_alert(self, data: dict[str, Any]) -> None:
        if not is_firebase_connected():
            return
        try:
            self._alerts.create_once(data)
        except Exception as exc:
            mark_firebase_failure(exc)

    def _save_heartbeat(self) -> None:
        try:
            db = get_firestore_client()
            if db is None:
                return
            db.collection("system_status").document("backend").set({
                "status": "online",
                "firebase_connected": True,
                "model_loaded": self.video_processor.detector.loaded,
                "video_source_available": self.video_processor.video_available,
                "last_heartbeat": server_timestamp(),
            }, merge=True)
        except Exception as exc:
            mark_firebase_failure(exc)


def seed_cameras_if_empty() -> None:
    """Seed sekali sahaja apabila query kamera aktif benar-benar kosong."""
    if not config.SEED_DEMO_CAMERA or not is_firebase_connected():
        return
    if camera_repository.get_active_cameras(limit=1):
        return
    from .. import camera_store
    for camera in camera_store.list_cameras():
        is_primary = camera["camera_id"] == config.CAMERA_ID
        camera_repository.upsert_camera({
            "camera_id": camera["camera_id"], "name": camera["camera_name"], "location": camera["location"],
            "source_type": "video" if is_primary else "demo",
            "source_name": config.resolve_video_source().name if is_primary else "",
            "is_active": True,
        })

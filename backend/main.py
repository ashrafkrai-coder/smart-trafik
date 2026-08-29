"""Aplikasi FastAPI Smart Trafik."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from . import camera_store, config
from .detector import VehicleDetector
from .firebase_client import initialize_firebase, is_firebase_connected
from .repositories import alert_repository, camera_repository, traffic_repository
from .repositories.common import FirebaseUnavailableError
from .services.history_service import HistoryService, seed_cameras_if_empty
from .video_stream import VideoProcessor

LOGGER = logging.getLogger(__name__)
detector = VehicleDetector()
video_processor = VideoProcessor(detector)
history_service = HistoryService(video_processor)

saved_primary_camera = camera_store.get_camera(config.CAMERA_ID)
if saved_primary_camera:
    config.CAMERA_NAME = saved_primary_camera["camera_name"]
    config.CAMERA_LOCATION = saved_primary_camera["location"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_firebase(force=True)
    if is_firebase_connected():
        try:
            seed_cameras_if_empty()
        except Exception as exc:
            LOGGER.warning("Kamera demo Firestore tidak dapat disediakan: %s", type(exc).__name__)
    detector.load()
    video_processor.start()
    history_service.start()
    yield
    history_service.stop()
    video_processor.stop()


app = FastAPI(title="Smart Trafik API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class SourceRequest(BaseModel):
    source: str = Field(min_length=1, max_length=255, examples=["trafik.mp4"])


class SettingsRequest(BaseModel):
    confidence_threshold: float = Field(ge=0.05, le=0.95, examples=[0.35])


class CameraUpdateRequest(BaseModel):
    camera_name: str = Field(min_length=2, max_length=80)
    location: str = Field(min_length=2, max_length=120)

    @field_validator("camera_name", "location")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or not all(character.isprintable() for character in cleaned):
            raise ValueError("Teks mesti sekurang-kurangnya 2 aksara dan tiada aksara kawalan.")
        return cleaned


def _firebase_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail={
        "code": "firebase_unavailable",
        "message": "Firebase Cloud Firestore tidak tersedia. Data live masih beroperasi.",
    })


@app.get("/health")
def health() -> dict[str, bool | str]:
    model_loaded = detector.loaded
    video_available = video_processor.video_available
    return {
        "status": "ok" if model_loaded and video_available else "degraded",
        "model_loaded": model_loaded,
        "video_source_available": video_available,
        "firebase_enabled": config.FIREBASE_ENABLED,
        "firebase_connected": is_firebase_connected(),
    }


@app.get("/api/traffic")
def traffic() -> dict[str, Any]:
    """Live shared state sahaja; endpoint ini tidak membaca Firestore."""
    snapshot = video_processor.get_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=503, detail={
            "connection_status": "offline",
            "message": video_processor.error or "Data trafik belum tersedia.",
        })
    return snapshot


@app.get("/api/traffic/history")
def traffic_history(
    camera_id: str = Query(default=config.CAMERA_ID, min_length=1, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    try:
        return traffic_repository.get_traffic_history(camera_id.strip().upper(), limit)
    except FirebaseUnavailableError:
        raise _firebase_unavailable() from None
    except Exception:
        LOGGER.exception("Sejarah trafik gagal dibaca.")
        raise HTTPException(status_code=503, detail="Sejarah trafik tidak dapat dibaca sekarang.") from None


@app.get("/video-feed")
def video_feed() -> StreamingResponse:
    if not video_processor.video_available:
        raise HTTPException(status_code=503, detail=video_processor.error or "Siaran video tidak tersedia.")
    return StreamingResponse(video_processor.mjpeg_frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


def _local_camera_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for camera in camera_store.list_cameras():
        record = dict(camera)
        record["connection_status"] = (
            "online" if camera["camera_id"] == config.CAMERA_ID and video_processor.video_available else "offline"
        )
        records.append(record)
    return records


@app.get("/api/cameras")
def cameras() -> list[dict[str, Any]]:
    if not is_firebase_connected():
        return _local_camera_records()
    try:
        stored = camera_repository.get_active_cameras(limit=100)
        if not stored and config.SEED_DEMO_CAMERA:
            seed_cameras_if_empty()
            stored = camera_repository.get_active_cameras(limit=100)
        return [{
            "camera_id": item["id"],
            "camera_name": item.get("name", item["id"]),
            "location": item.get("location", "Tidak dinyatakan"),
            "mode": "live" if item["id"] == config.CAMERA_ID else item.get("source_type", "demo"),
            "connection_status": "online" if item["id"] == config.CAMERA_ID and video_processor.video_available else "offline",
        } for item in stored]
    except Exception as exc:
        LOGGER.warning("Senarai kamera Firestore gagal; fallback tempatan digunakan: %s", type(exc).__name__)
        return _local_camera_records()


@app.put("/api/cameras/{camera_id}")
def update_camera(camera_id: str, request: CameraUpdateRequest) -> dict[str, Any]:
    normalized_id = camera_id.strip().upper()
    try:
        updated = camera_store.update_camera(normalized_id, request.camera_name, request.location)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Kamera tidak dijumpai: {normalized_id}") from None
    if normalized_id == config.CAMERA_ID:
        config.CAMERA_NAME = updated["camera_name"]
        config.CAMERA_LOCATION = updated["location"]
    if is_firebase_connected():
        try:
            camera_repository.upsert_camera({
                "camera_id": normalized_id, "name": request.camera_name, "location": request.location,
                "source_type": "video" if normalized_id == config.CAMERA_ID else updated["mode"],
                "source_name": video_processor.source_path.name if normalized_id == config.CAMERA_ID else "",
                "is_active": True,
            })
        except Exception as exc:
            LOGGER.warning("Kamera disimpan secara tempatan tetapi sync Firestore gagal: %s", type(exc).__name__)
    return {**updated, "message": "Nama dan lokasi kamera telah disimpan."}


@app.get("/api/alerts")
def alerts(limit: int = Query(default=50, ge=1, le=100)) -> list[dict[str, Any]]:
    try:
        return alert_repository.get_recent_alerts(limit)
    except FirebaseUnavailableError:
        raise _firebase_unavailable() from None
    except Exception:
        LOGGER.exception("Amaran trafik gagal dibaca.")
        raise HTTPException(status_code=503, detail="Amaran trafik tidak dapat dibaca sekarang.") from None


@app.patch("/api/alerts/{alert_id}/resolve")
def resolve_traffic_alert(alert_id: str) -> dict[str, str]:
    try:
        if not alert_repository.resolve_alert(alert_id):
            raise HTTPException(status_code=404, detail="Amaran tidak dijumpai.")
        return {"status": "resolved", "alert_id": alert_id}
    except FirebaseUnavailableError:
        raise _firebase_unavailable() from None


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return {
        "source": video_processor.source_path.name,
        "confidence_threshold": config.CONFIDENCE_THRESHOLD,
        "image_size": config.IMAGE_SIZE,
        "processing_fps": config.PROCESSING_FPS,
        "model_name": detector.model_name or config.MODEL_NAME,
        "model_loaded": detector.loaded,
        "video_source_available": video_processor.video_available,
        "firebase_enabled": config.FIREBASE_ENABLED,
        "firebase_connected": is_firebase_connected(),
    }


@app.post("/api/settings")
def update_settings(request: SettingsRequest) -> dict[str, str | float]:
    config.CONFIDENCE_THRESHOLD = request.confidence_threshold
    return {"status": "updated", "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "message": "Confidence YOLO telah dikemas kini untuk analisis seterusnya."}


@app.post("/api/source")
def change_source(request: SourceRequest) -> dict[str, str]:
    filename = request.source
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Gunakan nama fail sahaja; path tidak dibenarkan.")
    if Path(filename).suffix.lower() not in config.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format video mesti MP4, AVI, MOV atau MKV.")
    source_path = (config.VIDEO_DIR / filename).resolve()
    if source_path.parent != config.VIDEO_DIR.resolve():
        raise HTTPException(status_code=400, detail="Sumber mesti berada dalam folder videos.")
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail=f"Video tidak dijumpai: {filename}")
    video_processor.set_source(source_path)
    return {"status": "accepted", "source": filename, "message": "Sumber video sedang disambungkan."}

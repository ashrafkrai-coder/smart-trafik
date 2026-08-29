"""Konfigurasi pusat Smart Trafik yang bebas daripada current working directory."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Load .env if exists (local dev), in Cloud Run env vars are set directly
load_dotenv(PROJECT_ROOT / ".env", override=False)
VIDEO_DIR = PROJECT_ROOT / "videos"
MODEL_DIR = PROJECT_ROOT / "models"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ULTRALYTICS_CONFIG_DIR = PROJECT_ROOT / ".ultralytics"
ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


# In Cloud Run, VIDEO_SOURCE may not exist locally. Default to empty - video processor handles missing.
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", os.getenv("SMART_TRAFIK_VIDEO", ""))
MODEL_NAME = os.getenv("MODEL_NAME", os.getenv("SMART_TRAFIK_MODEL", "yolo26n.pt"))
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL_NAME", os.getenv("SMART_TRAFIK_FALLBACK_MODEL", "yolo11n.pt"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", os.getenv("SMART_TRAFIK_CONFIDENCE", "0.35")))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", os.getenv("SMART_TRAFIK_IMAGE_SIZE", "640")))
PROCESSING_FPS = float(os.getenv("PROCESSING_FPS", os.getenv("SMART_TRAFIK_FPS", "12")))
MAX_FRAME_WIDTH = int(os.getenv("MAX_FRAME_WIDTH", "1280"))
TRAFFIC_SMOOTH_FRAMES = max(10, int(os.getenv("TRAFFIC_SMOOTH_FRAMES", "10")))

CAMERA_ID = os.getenv("CAMERA_ID", "CAM01")
CAMERA_NAME = os.getenv("CAMERA_NAME", "Jalan Templer")
CAMERA_LOCATION = os.getenv("CAMERA_LOCATION", "Petaling Jaya")

FIREBASE_ENABLED = _as_bool("FIREBASE_ENABLED", True)
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "").strip() or None
SEED_DEMO_CAMERA = _as_bool("SEED_DEMO_CAMERA", True)
TRAFFIC_SAVE_INTERVAL_SECONDS = max(10, int(os.getenv("TRAFFIC_SAVE_INTERVAL_SECONDS", "60")))
SYSTEM_HEARTBEAT_INTERVAL_SECONDS = max(30, int(os.getenv("SYSTEM_HEARTBEAT_INTERVAL_SECONDS", "60")))
FIREBASE_RETRY_INTERVAL_SECONDS = max(30, int(os.getenv("FIREBASE_RETRY_INTERVAL_SECONDS", "60")))
ALERT_COOLDOWN_SECONDS = max(60, int(os.getenv("ALERT_COOLDOWN_SECONDS", "600")))
FRAME_STALE_ALERT_SECONDS = max(10, int(os.getenv("FRAME_STALE_ALERT_SECONDS", "30")))

TRAFFIC_SMOOTH_THRESHOLD = 10
TRAFFIC_CONGESTED_THRESHOLD = 25
MAX_CONSECUTIVE_READ_FAILURES = 5
RECONNECT_DELAY_SECONDS = 2.0
STALE_DATA_SECONDS = max(5.0, 3.0 / max(PROCESSING_FPS, 0.1))
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
DEFAULT_CORS_ORIGINS = ["http://127.0.0.1:5500", "http://localhost:5500"]
configured_origins = os.getenv("ALLOWED_ORIGINS", os.getenv("SMART_TRAFIK_CORS_ORIGINS", ""))
CORS_ORIGINS = list(dict.fromkeys(
    DEFAULT_CORS_ORIGINS + [item.strip() for item in configured_origins.split(",") if item.strip()]
))


def resolve_video_source(source: str | None = None) -> Path | None:
    """Pulangkan sumber video tempatan relatif kepada root projek. Returns None if not found."""
    src = source or VIDEO_SOURCE
    if not src:
        return None
    candidate = Path(src)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve() if candidate.is_file() else None

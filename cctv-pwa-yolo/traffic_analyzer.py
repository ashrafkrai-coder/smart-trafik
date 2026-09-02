#!/usr/bin/env python3
"""
Analisis trafik CCTV dengan YOLOv8 (nano) — CPU-friendly.

Mengambil snapshot dari go2rtc, mengira kenderaan (kereta, motosikal,
bas, lori), menilai kepadatan, dan menulis traffic_data.json setiap 3 saat.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_JSON = BASE_DIR / "traffic_data.json"
MODEL_PATH = BASE_DIR / "yolov8n.pt"

GO2RTC_SNAPSHOT_URL = os.environ.get(
    "GO2RTC_SNAPSHOT_URL",
    "http://localhost:1984/api/stream.mp4?src=pintu_depan",
)
CAMERA_ID = os.environ.get("TRAFFIC_CAMERA_ID", "pintu_depan")
POLL_INTERVAL_SEC = float(os.environ.get("TRAFFIC_POLL_INTERVAL", "3"))
YOLO_CONF = float(os.environ.get("YOLO_CONF", "0.35"))

# COCO class ID → kategori kenderaan
VEHICLE_CLASSES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

LABEL_MS: dict[str, str] = {
    "car": "Kereta",
    "motorcycle": "Motosikal",
    "bus": "Bas",
    "truck": "Lori",
}


def density_from_total(total: int) -> tuple[str, str]:
    if total < 3:
        return "Rendah", "low"
    if total <= 7:
        return "Sederhana", "medium"
    return "Tinggi", "high"


def empty_counts() -> dict[str, int]:
    return {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "total": 0}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(prefix="traffic_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def fetch_snapshot(url: str, timeout: float = 8.0) -> np.ndarray:
    # Use OpenCV to read frame from MJPEG or MP4 stream
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise ValueError("Gagal baca frame dari stream")
    return frame


def count_vehicles(model: YOLO, frame: np.ndarray) -> dict[str, int]:
    counts = empty_counts()
    results = model.predict(
        source=frame,
        conf=YOLO_CONF,
        verbose=False,
        imgsz=640,
        device="cpu",
    )
    if not results:
        return counts

    boxes = results[0].boxes
    if boxes is None or boxes.cls is None:
        return counts

    for class_id in boxes.cls.int().tolist():
        key = VEHICLE_CLASSES.get(int(class_id))
        if key:
            counts[key] += 1
            counts["total"] += 1
    return counts


def build_payload(
    counts: dict[str, int],
    status: str,
    message: str = "",
) -> dict[str, Any]:
    now = datetime.now()
    density, density_level = density_from_total(counts["total"])
    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "updated_at": now.strftime("%H:%M:%S"),
        "camera": CAMERA_ID,
        "status": status,
        "message": message,
        "counts": counts,
        "labels": LABEL_MS,
        "density": density,
        "density_level": density_level,
        "badge": f"🚗 {counts['total']} Kenderaan | Kepadatan: {density}",
    }


def load_model() -> YOLO:
    print(f"[YOLO] Memuatkan model: {MODEL_PATH.name}", flush=True)
    model = YOLO(str(MODEL_PATH) if MODEL_PATH.exists() else "yolov8n.pt")
    # Warm-up supaya latensi kitaran pertama lebih stabil
    dummy = np.zeros((320, 320, 3), dtype=np.uint8)
    model.predict(dummy, verbose=False, imgsz=320, device="cpu")
    print("[YOLO] Model sedia (CPU).", flush=True)
    return model


def main() -> int:
    print("=" * 56, flush=True)
    print(" CCTV Traffic Analyzer — YOLOv8n", flush=True)
    print(f" Snapshot : {GO2RTC_SNAPSHOT_URL}", flush=True)
    print(f" Output   : {OUTPUT_JSON}", flush=True)
    print(f" Interval : {POLL_INTERVAL_SEC}s", flush=True)
    print("=" * 56, flush=True)

    try:
        model = load_model()
    except Exception as exc:
        print(f"[RALAT] Gagal memuatkan YOLO: {exc}", file=sys.stderr, flush=True)
        return 1

    while True:
        cycle_start = time.monotonic()
        try:
            frame = fetch_snapshot(GO2RTC_SNAPSHOT_URL)
            counts = count_vehicles(model, frame)
            payload = build_payload(counts, status="ok")
            write_json_atomic(OUTPUT_JSON, payload)
            print(
                f"[{payload['updated_at']}] {payload['badge']} "
                f"(kereta={counts['car']} moto={counts['motorcycle']} "
                f"bas={counts['bus']} lori={counts['truck']})",
                flush=True,
            )
        except (TimeoutError, ValueError, OSError) as exc:
            payload = build_payload(
                empty_counts(),
                status="error",
                message=str(exc),
            )
            try:
                write_json_atomic(OUTPUT_JSON, payload)
            except OSError:
                pass
            print(f"[AMARAN] {exc}", file=sys.stderr, flush=True)
        except KeyboardInterrupt:
            print("\n[INFO] Dihentikan oleh pengguna.", flush=True)
            return 0

        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0.2, POLL_INTERVAL_SEC - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    sys.exit(main())

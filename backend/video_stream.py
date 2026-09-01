"""Thread pemprosesan video dan shared state selamat untuk endpoint FastAPI."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import cv2

from . import config
from .detector import VehicleDetector, draw_summary
from .traffic_analyzer import (
    average_confidence,
    classify_traffic,
    count_by_vehicle_type,
    estimate_flow_speed,
    estimate_travel_time,
)

LOGGER = logging.getLogger(__name__)


def calculate_frame_skip(source_fps: float, cycle_seconds: float) -> int:
    """Kira frame yang perlu dibuang agar fail bergerak hampir pada masa sebenar."""
    if source_fps <= 0 or cycle_seconds <= 0:
        return 0
    return max(0, int(source_fps * cycle_seconds) - 1)


class VideoProcessor:
    """Baca video dalam satu thread; API hanya membaca snapshot terkini."""

    def __init__(self, detector: VehicleDetector) -> None:
        self.detector = detector
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._source_changed = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: cv2.VideoCapture | None = None
        self._source = config.resolve_video_source()
        self._counts_window: deque[int] = deque(maxlen=config.TRAFFIC_SMOOTH_FRAMES)
        self._latest_jpeg: bytes | None = None
        self._snapshot: dict[str, Any] | None = None
        self._error: str | None = "Pemproses video belum dimulakan."
        self._video_available = False

    @property
    def source_path(self) -> Path | None:
        with self._lock:
            return self._source if isinstance(self._source, Path) else None

    @property
    def source_label(self) -> str:
        with self._lock:
            return config.video_source_label(self._source)

    @property
    def video_available(self) -> bool:
        with self._lock:
            return self._video_available

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="smart-trafik-video", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._source_changed.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._release_capture()

    def set_source(self, source_path: Path) -> None:
        with self._lock:
            self._source = source_path
            self._snapshot = None
            self._latest_jpeg = None
            self._counts_window.clear()
            self._video_available = False
            self._error = "Sumber video sedang ditukar."
        self._source_changed.set()

    def get_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            if self._snapshot is None:
                return None
            age = time.monotonic() - float(self._snapshot["_monotonic_time"])
            if age > config.STALE_DATA_SECONDS:
                self._video_available = False
                self._error = "Data video tidak lagi dikemas kini."
                return None
            return {key: value for key, value in self._snapshot.items() if not key.startswith("_")}

    def mjpeg_frames(self) -> Iterator[bytes]:
        """Kongsi JPEG yang telah dianotasi; tiada inferens dibuat di sini."""
        last_frame: bytes | None = None
        while not self._stop_event.is_set():
            with self._lock:
                frame = self._latest_jpeg
            if frame and frame is not last_frame:
                last_frame = frame
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            else:
                time.sleep(0.05)

    def _run(self) -> None:
        frame_interval = 1.0 / max(config.PROCESSING_FPS, 0.1)
        while not self._stop_event.is_set():
            if not self.detector.loaded:
                self._set_offline(self.detector.load_error or "Model YOLO tidak tersedia.")
                self._stop_event.wait(config.RECONNECT_DELAY_SECONDS)
                continue

            with self._lock:
                source = self._source
            if source is None or (isinstance(source, Path) and not source.is_file()):
                self._set_offline("Sumber video belum dikonfigurasi atau tidak dijumpai.")
                self._stop_event.wait(config.RECONNECT_DELAY_SECONDS)
                continue

            capture = self._open_capture(source)
            self._capture = capture
            if not capture.isOpened():
                self._set_offline(f"Video tidak dapat dibuka: {config.video_source_label(source)}")
                self._release_capture()
                self._wait_for_retry()
                continue

            with self._lock:
                self._video_available = True
                self._error = None
            source_fps = capture.get(cv2.CAP_PROP_FPS)
            is_local_video = isinstance(source, Path) and source.suffix.lower() in config.ALLOWED_VIDEO_EXTENSIONS
            failures = 0
            while not self._stop_event.is_set() and not self._source_changed.is_set():
                started_at = time.monotonic()
                ok, frame = capture.read()
                if not ok:
                    failures += 1
                    # Fail MP4 diulang untuk demo. Sumber lain disambung semula selepas beberapa kegagalan.
                    if is_local_video:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = capture.read()
                    if not ok:
                        if failures >= config.MAX_CONSECUTIVE_READ_FAILURES:
                            self._set_offline("Frame video gagal dibaca berulang kali.")
                            break
                        self._stop_event.wait(0.2)
                        continue
                failures = 0
                try:
                    frame = self._resize_frame(frame)
                    detections, annotated = self.detector.detect(frame)
                    self._publish(detections, annotated, started_at)
                except Exception as exc:  # pragma: no cover - inferens peranti/model
                    LOGGER.exception("Inferens YOLO gagal")
                    self._set_offline(f"Analisis video gagal: {exc}")
                    break
                elapsed = time.monotonic() - started_at
                cycle_seconds = max(frame_interval, elapsed)
                if is_local_video:
                    self._skip_frames(capture, calculate_frame_skip(source_fps, cycle_seconds))
                self._stop_event.wait(max(0.0, frame_interval - elapsed))

            self._release_capture()
            if not self._stop_event.is_set():
                if self._source_changed.is_set():
                    self._source_changed.clear()
                else:
                    self._wait_for_retry()

    def _publish(self, detections: list[dict[str, Any]], annotated: Any, started_at: float) -> None:
        counts = count_by_vehicle_type(detections)
        vehicle_count = sum(counts.values())
        self._counts_window.append(vehicle_count)
        smoothed_count = round(sum(self._counts_window) / len(self._counts_window), 1)
        traffic_status = classify_traffic(round(smoothed_count))
        annotated = draw_summary(annotated, vehicle_count, traffic_status)
        encoded, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if not encoded:
            raise RuntimeError("Frame tidak dapat ditukar kepada JPEG")
        elapsed = max(time.monotonic() - started_at, 0.0001)
        snapshot = {
            "camera_id": config.CAMERA_ID,
            "camera_name": config.CAMERA_NAME,
            "location": config.CAMERA_LOCATION,
            "connection_status": "online",
            "traffic_status": traffic_status,
            "vehicle_count": vehicle_count,
            "smoothed_vehicle_count": smoothed_count,
            "counts": counts,
            "estimated_flow_speed": estimate_flow_speed(traffic_status),
            "estimated_travel_time": estimate_travel_time(traffic_status),
            "confidence": average_confidence(detections),
            "fps": round(1.0 / elapsed, 1),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "_monotonic_time": time.monotonic(),
        }
        with self._lock:
            self._snapshot = snapshot
            self._latest_jpeg = jpeg.tobytes()
            self._video_available = True
            self._error = None

    def _set_offline(self, message: str) -> None:
        with self._lock:
            self._video_available = False
            self._error = message
            self._snapshot = None
            self._latest_jpeg = None

    @staticmethod
    def _open_capture(source: Path | str | int) -> cv2.VideoCapture:
        if isinstance(source, int):
            return cv2.VideoCapture(source, cv2.CAP_DSHOW)
        if isinstance(source, Path):
            return cv2.VideoCapture(str(source))
        # CAP_FFMPEG memberi RTSP over TCP yang lebih stabil untuk CCTV berwayar.
        return cv2.VideoCapture(source, cv2.CAP_FFMPEG)

    @staticmethod
    def _resize_frame(frame: Any) -> Any:
        """Kurangkan kos inferens/JPEG untuk video 4K sambil mengekalkan nisbah aspek."""
        height, width = frame.shape[:2]
        if config.MAX_FRAME_WIDTH <= 0 or width <= config.MAX_FRAME_WIDTH:
            return frame
        scale = config.MAX_FRAME_WIDTH / width
        target_size = (config.MAX_FRAME_WIDTH, max(1, round(height * scale)))
        return cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

    @staticmethod
    def _skip_frames(capture: cv2.VideoCapture, frame_count: int) -> None:
        """Buang frame tanpa penukaran warna; ulang fail jika penghujung dicapai."""
        for _ in range(frame_count):
            if not capture.grab():
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                break

    def _wait_for_retry(self) -> None:
        self._source_changed.wait(config.RECONNECT_DELAY_SECONDS)
        self._source_changed.clear()

    def _release_capture(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()

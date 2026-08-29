"""Pemuatan model YOLO tunggal dan anotasi pengesanan kenderaan."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from . import config

LOGGER = logging.getLogger(__name__)
COCO_VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
BOX_COLORS = {
    "car": (46, 204, 113),
    "motorcycle": (241, 196, 15),
    "bus": (52, 152, 219),
    "truck": (231, 76, 60),
}


class VehicleDetector:
    """Mengekalkan satu instance model untuk semua frame dan request."""

    def __init__(self) -> None:
        self.model: Any | None = None
        self.model_name: str | None = None
        self.load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def load(self) -> bool:
        """Muat model utama sekali, kemudian cuba model nano fallback rasmi."""
        if self.loaded:
            return True
        try:
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - bergantung persekitaran
            self.load_error = f"Ultralytics tidak tersedia: {exc}"
            LOGGER.exception(self.load_error)
            return False

        errors: list[str] = []
        for model_name in dict.fromkeys((config.MODEL_NAME, config.FALLBACK_MODEL_NAME)):
            local_model = config.MODEL_DIR / model_name
            model_reference = str(local_model) if local_model.exists() else model_name
            try:
                self.model = YOLO(model_reference)
                self.model_name = model_name
                self.load_error = None
                LOGGER.info("Model YOLO dimuatkan: %s", model_name)
                return True
            except Exception as exc:  # pragma: no cover - muat turun/model luaran
                errors.append(f"{model_name}: {exc}")
                LOGGER.warning("Model %s gagal dimuatkan", model_name, exc_info=True)

        self.load_error = "Model YOLO gagal dimuatkan. " + " | ".join(errors)
        return False

    def detect(self, frame: np.ndarray) -> tuple[list[dict[str, Any]], np.ndarray]:
        """Jalankan inferens tepat sekali dan pulangkan frame beranotasi."""
        if self.model is None:
            raise RuntimeError(self.load_error or "Model YOLO belum dimuatkan")

        results = self.model.predict(
            source=frame,
            classes=list(COCO_VEHICLE_CLASSES),
            conf=config.CONFIDENCE_THRESHOLD,
            imgsz=config.IMAGE_SIZE,
            verbose=False,
        )
        detections: list[dict[str, Any]] = []
        annotated_frame = frame.copy()
        if not results:
            return detections, annotated_frame

        boxes = results[0].boxes
        if boxes is None:
            return detections, annotated_frame

        for box in boxes:
            class_id = int(box.cls[0].item())
            class_name = COCO_VEHICLE_CLASSES.get(class_id)
            if class_name is None:
                continue
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            detection = {
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence,
                "box": [x1, y1, x2, y2],
            }
            detections.append(detection)
            color = BOX_COLORS[class_name]
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name} {confidence:.2f}"
            cv2.putText(
                annotated_frame,
                label,
                (x1, max(22, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
        return detections, annotated_frame


def draw_summary(frame: np.ndarray, vehicle_count: int, traffic_status: str) -> np.ndarray:
    """Tambah ringkasan yang sama pada frame yang sudah menjalani inferens."""
    label = f"Jumlah: {vehicle_count} | Trafik: {traffic_status}"
    cv2.rectangle(frame, (8, 8), (min(frame.shape[1] - 8, 430), 48), (11, 73, 61), -1)
    cv2.putText(frame, label, (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame


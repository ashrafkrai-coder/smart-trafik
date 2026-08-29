"""Fungsi tulen untuk menukar output pengesanan kepada metrik trafik."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import fmean
from typing import Any

from . import config

VEHICLE_NAMES = ("car", "motorcycle", "bus", "truck")


def classify_traffic(vehicle_count: int) -> str:
    """Kelaskan trafik menggunakan ambang yang boleh dikonfigurasi."""
    if vehicle_count <= config.TRAFFIC_SMOOTH_THRESHOLD:
        return "Lancar"
    if vehicle_count <= config.TRAFFIC_CONGESTED_THRESHOLD:
        return "Sesak"
    return "Sangat Sesak"


def count_by_vehicle_type(detections: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Kira hanya empat kelas kenderaan yang disokong."""
    counts = {name: 0 for name in VEHICLE_NAMES}
    for detection in detections:
        class_name = str(detection.get("class_name", ""))
        if class_name in counts:
            counts[class_name] += 1
    return counts


def average_confidence(detections: Iterable[Mapping[str, Any]]) -> float:
    """Pulangkan purata confidence atau sifar bagi senarai kosong."""
    values = [float(item.get("confidence", 0.0)) for item in detections]
    return round(fmean(values), 4) if values else 0.0


def estimate_flow_speed(traffic_status: str) -> int:
    """Anggaran demonstrasi; bukan ukuran kelajuan dunia sebenar."""
    return {"Lancar": 60, "Sesak": 25, "Sangat Sesak": 8}.get(traffic_status, 0)


def estimate_travel_time(traffic_status: str) -> int:
    """Anggaran masa perjalanan demonstrasi sehingga kamera dikalibrasi."""
    return {"Lancar": 10, "Sesak": 18, "Sangat Sesak": 32}.get(traffic_status, 0)


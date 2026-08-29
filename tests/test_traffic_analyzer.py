"""Ujian unit bagi fungsi analisis trafik yang tidak bergantung pada YOLO."""

import pytest

from backend.traffic_analyzer import average_confidence, classify_traffic, count_by_vehicle_type


@pytest.mark.parametrize(
    ("vehicle_count", "expected"),
    [(0, "Lancar"), (10, "Lancar"), (11, "Sesak"), (25, "Sesak"), (26, "Sangat Sesak")],
)
def test_classify_traffic_boundaries(vehicle_count: int, expected: str) -> None:
    assert classify_traffic(vehicle_count) == expected


def test_count_by_vehicle_type() -> None:
    detections = [
        {"class_name": "car"}, {"class_name": "car"}, {"class_name": "motorcycle"},
        {"class_name": "bus"}, {"class_name": "truck"}, {"class_name": "person"},
    ]
    assert count_by_vehicle_type(detections) == {"car": 2, "motorcycle": 1, "bus": 1, "truck": 1}


def test_average_confidence_empty() -> None:
    assert average_confidence([]) == 0.0


def test_average_confidence_multiple_detections() -> None:
    detections = [{"confidence": 0.8}, {"confidence": 0.9}, {"confidence": 1.0}]
    assert average_confidence(detections) == pytest.approx(0.9)


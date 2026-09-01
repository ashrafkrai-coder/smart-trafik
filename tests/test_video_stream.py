"""Ujian utiliti pacing video tempatan."""

import pytest

from backend import config
from backend.video_stream import calculate_frame_skip


@pytest.mark.parametrize(
    ("source_fps", "cycle_seconds", "expected"),
    [
        (50.0, 0.2, 9),
        (50.0, 1 / 12, 3),
        (25.0, 1 / 25, 0),
        (0.0, 0.2, 0),
        (50.0, 0.0, 0),
    ],
)
def test_calculate_frame_skip(source_fps: float, cycle_seconds: float, expected: int) -> None:
    assert calculate_frame_skip(source_fps, cycle_seconds) == expected


def test_resolve_rtsp_source_adds_encoded_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CCTV_USERNAME", "admin@example")
    monkeypatch.setattr(config, "CCTV_PASSWORD", "p@ss word")

    source = config.resolve_video_source("rtsp://192.168.1.64:554/Streaming/Channels/101")

    assert source == "rtsp://admin%40example:p%40ss%20word@192.168.1.64:554/Streaming/Channels/101"
    assert config.video_source_label(source) == "RTSP 192.168.1.64:554/Streaming/Channels/101"


def test_resolve_usb_camera_index() -> None:
    assert config.resolve_video_source("0") == 0
    assert config.video_source_label(0) == "Kamera USB 0"

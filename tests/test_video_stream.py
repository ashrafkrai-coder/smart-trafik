"""Ujian utiliti pacing video tempatan."""

import pytest

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

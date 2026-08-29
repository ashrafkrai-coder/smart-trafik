"""Ujian bagi tetapan runtime backend."""

import pytest
from pydantic import ValidationError

from backend import config
from backend.main import SettingsRequest, get_settings, update_settings


def test_update_confidence_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CONFIDENCE_THRESHOLD", 0.35)
    result = update_settings(SettingsRequest(confidence_threshold=0.6))
    assert result["status"] == "updated"
    assert result["confidence_threshold"] == 0.6
    assert get_settings()["confidence_threshold"] == 0.6


@pytest.mark.parametrize("value", [0.01, 0.99])
def test_confidence_threshold_rejects_unsafe_range(value: float) -> None:
    with pytest.raises(ValidationError):
        SettingsRequest(confidence_threshold=value)

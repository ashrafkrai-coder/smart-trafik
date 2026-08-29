"""Ujian persistence dan validasi metadata kamera."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend import camera_store
from backend import config
from backend.main import CameraUpdateRequest, update_camera


def test_camera_update_is_persisted(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_file = tmp_path / "cameras.json"
    monkeypatch.setattr(camera_store, "DATA_FILE", data_file)
    monkeypatch.setattr(camera_store, "_cameras", deepcopy(camera_store.DEFAULT_CAMERAS))

    updated = camera_store.update_camera("CAM02", "Kamera Ujian", "Lokasi Baharu")
    assert updated["camera_name"] == "Kamera Ujian"
    assert data_file.exists()

    monkeypatch.setattr(camera_store, "_cameras", None)
    reloaded = camera_store.get_camera("CAM02")
    assert reloaded is not None
    assert reloaded["location"] == "Lokasi Baharu"


def test_unknown_camera_is_rejected(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(camera_store, "DATA_FILE", tmp_path / "cameras.json")
    monkeypatch.setattr(camera_store, "_cameras", deepcopy(camera_store.DEFAULT_CAMERAS))
    with pytest.raises(KeyError):
        camera_store.update_camera("CAM99", "Tidak Wujud", "Tiada Lokasi")


def test_primary_camera_update_syncs_traffic_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = {"camera_id": "CAM01", "camera_name": "Nama Baharu", "location": "Lokasi Baharu", "mode": "live"}
    monkeypatch.setattr(camera_store, "update_camera", lambda *_: saved)
    monkeypatch.setattr(config, "CAMERA_NAME", "Jalan Templer")
    monkeypatch.setattr(config, "CAMERA_LOCATION", "Petaling Jaya")

    response = update_camera("cam01", CameraUpdateRequest(camera_name="Nama Baharu", location="Lokasi Baharu"))

    assert response["camera_id"] == "CAM01"
    assert config.CAMERA_NAME == "Nama Baharu"
    assert config.CAMERA_LOCATION == "Lokasi Baharu"


@pytest.mark.parametrize(
    "payload",
    [
        {"camera_name": " ", "location": "Petaling Jaya"},
        {"camera_name": "Kamera", "location": "\n\t"},
        {"camera_name": "A" * 81, "location": "Petaling Jaya"},
    ],
)
def test_camera_metadata_validation(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CameraUpdateRequest(**payload)

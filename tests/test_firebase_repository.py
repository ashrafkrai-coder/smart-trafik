"""Ujian Firestore menggunakan mock sahaja; tiada projek sebenar disentuh."""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend import config, firebase_client
from backend.main import traffic
from backend.repositories import traffic_repository
from backend.services.history_service import AlertCoordinator


def test_firebase_initialization_succeeds_with_mock_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    fake_admin = types.ModuleType("firebase_admin")
    fake_admin.get_app = MagicMock(side_effect=ValueError("belum initialize"))  # type: ignore[attr-defined]
    fake_admin.initialize_app = MagicMock(return_value="app")  # type: ignore[attr-defined]
    fake_firestore = types.SimpleNamespace(client=MagicMock(return_value=client))
    fake_credentials = types.SimpleNamespace(Certificate=MagicMock())
    fake_admin.firestore = fake_firestore  # type: ignore[attr-defined]
    fake_admin.credentials = fake_credentials  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "firebase_admin", fake_admin)
    monkeypatch.setitem(sys.modules, "firebase_admin.firestore", fake_firestore)
    monkeypatch.setitem(sys.modules, "firebase_admin.credentials", fake_credentials)
    monkeypatch.setattr(config, "FIREBASE_ENABLED", True)
    firebase_client.reset_for_tests()

    assert firebase_client.initialize_firebase(force=True) is client
    assert firebase_client.is_firebase_connected() is True
    fake_admin.initialize_app.assert_called_once()


def test_application_survives_when_firebase_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_admin = types.ModuleType("firebase_admin")
    fake_admin.get_app = MagicMock(side_effect=ValueError("belum initialize"))  # type: ignore[attr-defined]
    fake_admin.initialize_app = MagicMock(side_effect=RuntimeError("credentials unavailable"))  # type: ignore[attr-defined]
    fake_admin.firestore = types.SimpleNamespace()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "firebase_admin", fake_admin)
    monkeypatch.setattr(config, "FIREBASE_ENABLED", True)
    firebase_client.reset_for_tests()

    assert firebase_client.initialize_firebase(force=True) is None
    assert firebase_client.is_firebase_connected() is False


def test_save_latest_uses_camera_document_id(monkeypatch: pytest.MonkeyPatch) -> None:
    db, collection, document = MagicMock(), MagicMock(), MagicMock()
    db.collection.return_value = collection
    collection.document.return_value = document
    monkeypatch.setattr(traffic_repository, "require_db", lambda: db)
    monkeypatch.setattr(traffic_repository, "server_timestamp", lambda: "SERVER_TIME")

    traffic_repository.save_latest_traffic({"camera_id": "CAM01", "vehicle_count": 3})

    db.collection.assert_called_once_with("traffic_latest")
    collection.document.assert_called_once_with("CAM01")
    document.set.assert_called_once_with(
        {"camera_id": "CAM01", "vehicle_count": 3, "updated_at": "SERVER_TIME"}, merge=True
    )


def test_save_record_creates_history_document(monkeypatch: pytest.MonkeyPatch) -> None:
    db, collection, reference = MagicMock(), MagicMock(), MagicMock(id="record-1")
    db.collection.return_value = collection
    collection.add.return_value = ("write-time", reference)
    monkeypatch.setattr(traffic_repository, "require_db", lambda: db)
    monkeypatch.setattr(traffic_repository, "server_timestamp", lambda: "SERVER_TIME")

    record_id = traffic_repository.save_traffic_record({
        "camera_id": "CAM01", "counts": {"car": 2, "motorcycle": 1, "bus": 0, "truck": 0},
    })

    assert record_id == "record-1"
    db.collection.assert_called_once_with("traffic_records")
    payload = collection.add.call_args.args[0]
    assert payload["car_count"] == 2
    assert payload["recorded_at"] == "SERVER_TIME"


def test_history_limit_is_capped_and_timestamp_is_iso(monkeypatch: pytest.MonkeyPatch) -> None:
    db, collection, query = MagicMock(), MagicMock(), MagicMock()
    db.collection.return_value = collection
    collection.where.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    snapshot = MagicMock(id="history-1")
    snapshot.to_dict.return_value = {"recorded_at": datetime(2026, 8, 29, tzinfo=timezone.utc)}
    query.stream.return_value = [snapshot]
    monkeypatch.setattr(traffic_repository, "require_db", lambda: db)

    result = traffic_repository.get_traffic_history("CAM01", limit=999)

    query.limit.assert_called_once_with(200)
    assert result[0]["recorded_at"] == "2026-08-29T00:00:00+00:00"


def test_alert_is_not_repeated_during_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict] = []
    clock = [100.0]
    monkeypatch.setattr("backend.services.history_service.alert_repository.get_active_alert", lambda *_: None)
    monkeypatch.setattr("backend.services.history_service.alert_repository.create_alert", lambda item: created.append(item))
    monkeypatch.setattr(config, "ALERT_COOLDOWN_SECONDS", 600)
    coordinator = AlertCoordinator(now=lambda: clock[0])
    alert = {"camera_id": "CAM01", "alert_type": "severe_congestion"}

    assert coordinator.create_once(alert) is True
    assert coordinator.create_once(alert) is False
    assert len(created) == 1


def test_live_data_does_not_read_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = {"camera_id": "CAM01", "traffic_status": "Lancar"}
    monkeypatch.setattr("backend.main.video_processor.get_snapshot", lambda: snapshot)
    monkeypatch.setattr(traffic_repository, "get_latest_traffic", MagicMock(side_effect=AssertionError))
    assert traffic() is snapshot
    traffic_repository.get_latest_traffic.assert_not_called()

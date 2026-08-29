"""Sambungan Firebase Admin tunggal dengan kegagalan yang tidak mematikan aplikasi."""

from __future__ import annotations

import logging
import json
import os
import threading
import time
from typing import Any

from . import config

LOGGER = logging.getLogger(__name__)
_lock = threading.RLock()
_client: Any | None = None
_connected = False
_last_error: str | None = None
_last_attempt = 0.0


def initialize_firebase(force: bool = False) -> Any | None:
    """Initialize satu Firebase app menggunakan Application Default Credentials."""
    global _client, _connected, _last_error, _last_attempt
    if not config.FIREBASE_ENABLED:
        _connected = False
        _last_error = "Firebase dinyahaktifkan melalui konfigurasi."
        return None
    with _lock:
        if _client is not None and _connected:
            return _client
        now = time.monotonic()
        if not force and _last_attempt and now - _last_attempt < config.FIREBASE_RETRY_INTERVAL_SECONDS:
            return None
        _last_attempt = now
        try:
            import firebase_admin
            from firebase_admin import firestore
            from firebase_admin import credentials
            try:
                app = firebase_admin.get_app()
            except ValueError:
                options = {"projectId": config.FIREBASE_PROJECT_ID} if config.FIREBASE_PROJECT_ID else None
                raw_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
                credential = credentials.Certificate(json.loads(raw_credentials)) if raw_credentials else None
                app = firebase_admin.initialize_app(credential=credential, options=options)
            candidate = firestore.client(app=app)
            # Client Firestore dibina secara lazy; bacaan kecil ini mengesahkan
            # credentials, project dan rangkaian sebelum health melapor connected.
            candidate.collection("system_status").document("backend").get(timeout=5)
            _client = candidate
            _connected = True
            _last_error = None
            LOGGER.info("Firebase Cloud Firestore disambungkan.")
            return _client
        except Exception as exc:
            _client = None
            _connected = False
            _last_error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("Firebase tidak tersedia; analisis live diteruskan: %s", type(exc).__name__)
            return None


def get_firestore_client() -> Any | None:
    return _client if _connected else initialize_firebase()


def is_firebase_connected() -> bool:
    return bool(_connected and _client is not None)


def get_firebase_error() -> str | None:
    return _last_error


def mark_firebase_failure(exc: Exception) -> None:
    global _connected, _last_error, _last_attempt
    with _lock:
        _connected = False
        _last_error = f"{type(exc).__name__}: {exc}"
        _last_attempt = time.monotonic()
    LOGGER.warning("Operasi Firestore gagal (%s); akan cuba semula mengikut sela.", type(exc).__name__)


def reset_for_tests() -> None:
    global _client, _connected, _last_error, _last_attempt
    with _lock:
        _client = None
        _connected = False
        _last_error = None
        _last_attempt = 0.0

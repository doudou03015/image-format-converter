"""Filesystem path helpers for config, logs, and packaged resources."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "ImageFormatConverter"


def get_project_root() -> Path:
    """Return the project root when running from source."""

    return Path(__file__).resolve().parents[2]


def get_resource_base() -> Path:
    """Return the resource base for source and PyInstaller modes."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return get_project_root()


def get_resource_path(relative_path: str) -> Path:
    """Resolve a bundled resource path."""

    return get_resource_base() / relative_path


def get_user_data_dir() -> Path:
    """Return the writable per-user application data directory."""

    if os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base_dir = Path.home() / f".{APP_DIR_NAME.lower()}"

    preferred = base_dir / APP_DIR_NAME
    fallback = get_project_root() / ".runtime" / APP_DIR_NAME

    for candidate in (preferred, fallback):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except PermissionError:
            continue

    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_settings_path() -> Path:
    """Return the user settings file path."""

    return get_user_data_dir() / "settings.json"


def get_logs_dir() -> Path:
    """Return the directory for application logs."""

    path = get_user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path

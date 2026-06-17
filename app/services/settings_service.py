"""Load and save user settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.settings import AppSettings
from app.utils.paths import get_resource_path, get_settings_path


class SettingsService:
    """Manage persisted settings with bundled defaults."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._settings_path = get_settings_path()
        self._default_path = get_resource_path("config/default_settings.json")

    def load(self) -> AppSettings:
        """Load default settings and overlay any user customizations."""

        default_data = self._read_json(self._default_path)
        user_data = self._read_json(self._settings_path)
        merged = {**default_data, **user_data}
        settings = AppSettings.from_dict(merged)
        self._logger.info("Settings loaded from %s", self._settings_path)
        return settings

    def save(self, settings: AppSettings) -> None:
        """Persist the current settings to the user directory."""

        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._logger.info("Settings saved to %s", self._settings_path)

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.warning("Failed to read JSON from %s: %s", path, exc)
            return {}

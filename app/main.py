"""Application entry point."""

from __future__ import annotations

import logging
import sys
from typing import Any

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app import APP_NAME
from app.gui.main_window import MainWindow
from app.services.settings_service import SettingsService
from app.utils.logger import setup_logging
from app.utils.paths import get_resource_path


APP_USER_MODEL_ID = "doudou03015.ImageFormatConverter"


def install_exception_hook(logger: logging.Logger) -> None:
    """Install a global exception hook so unexpected crashes are logged."""

    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.exception("Unhandled application exception", exc_info=(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(None, APP_NAME, "程序发生未处理异常，详细信息已写入日志文件。")

    sys.excepthook = handle_exception


def install_windows_app_user_model_id(logger: logging.Logger) -> None:
    """Set a stable Windows taskbar identity for the application icon."""

    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as exc:  # pragma: no cover - platform-specific best effort
        logger.warning("Failed to set Windows AppUserModelID: %s", exc)


def load_application_icon(logger: logging.Logger) -> QIcon | None:
    """Load the bundled application icon for windows and the taskbar."""

    icon_path = get_resource_path("logo.ico")
    if not icon_path.exists():
        logger.warning("Application icon not found: %s", icon_path)
        return None

    icon = QIcon(str(icon_path))
    if icon.isNull():
        logger.warning("Application icon could not be loaded: %s", icon_path)
        return None
    return icon


def main() -> int:
    """Launch the Qt application."""

    logger = setup_logging()
    install_exception_hook(logger)
    install_windows_app_user_model_id(logger)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Codex")
    app_icon = load_application_icon(logger)
    if app_icon:
        app.setWindowIcon(app_icon)

    settings_service = SettingsService(logger)
    window = MainWindow(settings_service=settings_service, logger=logger)
    if app_icon:
        window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""Application entry point."""

from __future__ import annotations

import logging
import sys
from typing import Any

from PySide6.QtWidgets import QApplication, QMessageBox

from app import APP_NAME
from app.gui.main_window import MainWindow
from app.services.settings_service import SettingsService
from app.utils.logger import setup_logging


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


def main() -> int:
    """Launch the Qt application."""

    logger = setup_logging()
    install_exception_hook(logger)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Codex")

    settings_service = SettingsService(logger)
    window = MainWindow(settings_service=settings_service, logger=logger)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

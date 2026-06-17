import logging
from pathlib import Path

from app.utils import logger as logger_module


def clear_image_converter_logger() -> logging.Logger:
    logger = logging.getLogger("image_converter")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    return logger


def test_setup_logging_falls_back_when_primary_log_file_is_unwritable(tmp_path, monkeypatch):
    clear_image_converter_logger()
    primary_log_dir = tmp_path / "primary"
    fallback_root = tmp_path / "project"
    original_file_handler = logger_module.logging.FileHandler

    def selective_file_handler(filename, *args, **kwargs):
        if Path(filename).parent == primary_log_dir:
            raise PermissionError("primary log is blocked")
        return original_file_handler(filename, *args, **kwargs)

    monkeypatch.setattr(logger_module, "get_logs_dir", lambda: primary_log_dir)
    monkeypatch.setattr(logger_module, "get_project_root", lambda: fallback_root)
    monkeypatch.setattr(logger_module.logging, "FileHandler", selective_file_handler)

    try:
        logger = logger_module.setup_logging()
        logger.info("fallback logging works")
        fallback_log_dir = fallback_root / ".runtime" / "ImageFormatConverter" / "logs"

        assert any(Path(handler.baseFilename).parent == fallback_log_dir for handler in logger.handlers if hasattr(handler, "baseFilename"))
        assert list(fallback_log_dir.glob("image_converter_*.log"))
    finally:
        clear_image_converter_logger()

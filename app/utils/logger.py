"""Logging configuration helpers."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from app.utils.paths import APP_DIR_NAME, get_logs_dir, get_project_root


def setup_logging() -> logging.Logger:
    """Configure and return the application root logger."""

    logger = logging.getLogger("image_converter")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file_name = f"image_converter_{datetime.now():%Y%m%d}.log"
    for log_dir in _candidate_log_dirs(logger):
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / log_file_name, encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to open log file in %s: %s", log_dir, exc)
            continue

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        break

    logger.info("Logging initialized")
    return logger


def _candidate_log_dirs(logger: logging.Logger) -> list[Path]:
    candidates: list[Path] = []
    try:
        candidates.append(get_logs_dir())
    except OSError as exc:
        logger.warning("Failed to prepare user log directory: %s", exc)

    fallback = get_project_root() / ".runtime" / APP_DIR_NAME / "logs"
    if fallback not in candidates:
        candidates.append(fallback)
    return candidates

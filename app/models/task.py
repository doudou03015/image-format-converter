"""Task and result models for image conversion workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.models.settings import ConversionOptions


@dataclass(slots=True)
class ImageInfoSummary:
    """Lightweight image metadata shown in the preview panel."""

    path: Path
    file_name: str
    width: int
    height: int
    format_name: str
    mode: str
    file_size: int
    has_alpha: bool


@dataclass(slots=True)
class ConversionTask:
    """Represents one source file and the desired conversion settings."""

    source_path: Path
    options: ConversionOptions


@dataclass(slots=True)
class ConversionResult:
    """Outcome of a single conversion attempt."""

    source_path: Path
    status: str
    output_path: Path | None = None
    error_message: str | None = None
    elapsed_ms: int = 0


@dataclass(slots=True)
class BatchProgress:
    """Progress information emitted during batch work."""

    total: int
    processed: int
    success_count: int
    failure_count: int
    skipped_count: int
    current_file: str = ""


@dataclass(slots=True)
class SessionSummary:
    """Final summary emitted when batch conversion ends."""

    total: int
    processed: int
    success_count: int
    failure_count: int
    skipped_count: int
    cancelled: bool
    results: list[ConversionResult] = field(default_factory=list)

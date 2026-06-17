"""Application and conversion settings models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AppSettings:
    """Persisted user preferences."""

    theme: str = "light"
    default_output_mode: str = "source"
    default_output_dir: str = ""
    default_format: str = "png"
    jpg_quality: int = 95
    preserve_exif: bool = True
    preserve_icc_profile: bool = True
    jpg_background: str = "#FFFFFF"
    png_optimize: bool = True
    webp_lossless: bool = True
    webp_quality: int = 90
    tiff_compression: str = "tiff_lzw"
    recursive_scan: bool = True
    auto_fix_orientation: bool = True
    resize_enabled: bool = False
    max_long_edge: int = 1920
    duplicate_strategy: str = "rename"
    naming_mode: str = "source_ext"
    naming_marker: str = "_converted"
    rename_prefix: str = ""
    rename_suffix: str = ""
    auto_open_output_dir: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        """Create settings from a raw dictionary."""

        valid_keys = {field.name for field in cls.__dataclass_fields__.values()}
        filtered = {key: value for key, value in data.items() if key in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to a JSON-friendly dictionary."""

        return asdict(self)


@dataclass(slots=True)
class ConversionOptions:
    """Conversion options collected from the GUI."""

    output_format: str
    output_mode: str
    output_dir: Path | None
    naming_mode: str
    naming_marker: str
    rename_prefix: str
    rename_suffix: str
    duplicate_strategy: str
    jpg_quality: int
    preserve_exif: bool
    preserve_icc_profile: bool
    jpg_background: str
    png_optimize: bool
    webp_lossless: bool
    webp_quality: int
    tiff_compression: str
    auto_fix_orientation: bool
    resize_enabled: bool
    max_long_edge: int

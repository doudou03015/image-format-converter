"""Helpers for safely reading image metadata."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.models.task import ImageInfoSummary
from app.utils.exceptions import ImageReadError


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".ico",
}


def is_supported_image_path(path: Path) -> bool:
    """Return True if the path has a supported image suffix."""

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def human_readable_size(size_in_bytes: int) -> str:
    """Convert a byte size into a user-friendly string."""

    units = ["B", "KB", "MB", "GB"]
    size = float(size_in_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size_in_bytes} B"


def image_has_alpha(image: Image.Image) -> bool:
    """Detect whether a PIL image carries transparency information."""

    if image.mode in {"RGBA", "LA"}:
        return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return False


def collect_image_info(path: Path) -> ImageInfoSummary:
    """Safely open an image file and collect metadata for the GUI."""

    try:
        with Image.open(path) as image:
            width, height = image.size
            return ImageInfoSummary(
                path=path,
                file_name=path.name,
                width=width,
                height=height,
                format_name=(image.format or path.suffix.lstrip(".")).upper(),
                mode=image.mode,
                file_size=path.stat().st_size,
                has_alpha=image_has_alpha(image),
            )
    except Exception as exc:  # pragma: no cover - pillow raises format-specific exceptions
        raise ImageReadError(f"无法读取图片：{path.name}") from exc

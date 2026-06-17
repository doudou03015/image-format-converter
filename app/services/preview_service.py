"""Generate scaled previews for the GUI."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtGui import QPixmap

from app.utils.exceptions import ImageReadError


class PreviewService:
    """Create lightweight preview pixmaps without loading original-size images into the UI."""

    def build_preview(self, path: Path, max_size: tuple[int, int]) -> QPixmap:
        """Load an image, scale it in Pillow, and return a QPixmap."""

        try:
            with Image.open(path) as image:
                preview = ImageOps.exif_transpose(image)
                if preview.mode not in {"RGB", "RGBA"}:
                    preview = preview.convert("RGBA")
                preview.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                preview.save(buffer, format="PNG")
        except Exception as exc:  # pragma: no cover - pillow raises format-specific exceptions
            raise ImageReadError(f"无法预览图片：{path.name}") from exc

        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap

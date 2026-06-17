"""Scan files and folders for supported images."""

from __future__ import annotations

from pathlib import Path

from app.utils.image_info import is_supported_image_path


class FileScanner:
    """Find supported image files from explicit paths and folders."""

    def scan(self, input_paths: list[Path], recursive: bool = True) -> list[Path]:
        """Expand files and folders into a deduplicated list of image files."""

        discovered: set[Path] = set()
        for raw_path in input_paths:
            path = raw_path.expanduser().resolve()
            if not path.exists():
                continue

            if path.is_file() and is_supported_image_path(path):
                discovered.add(path)
                continue

            if path.is_dir():
                iterator = path.rglob("*") if recursive else path.glob("*")
                for child in iterator:
                    if child.is_file() and is_supported_image_path(child):
                        discovered.add(child.resolve())

        return sorted(discovered, key=lambda item: str(item).lower())

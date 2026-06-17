"""Core image conversion service."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PIL import Image, ImageColor, ImageOps

from app.models.settings import ConversionOptions
from app.models.task import ConversionResult, ConversionTask
from app.utils.exceptions import ConversionError
from app.utils.image_info import image_has_alpha


FORMAT_MAP = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
    "ico": "ICO",
}

EXIF_ORIENTATION_TAG = 274


class ConverterService:
    """Convert images between supported formats with format-aware safeguards."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def convert_file(self, task: ConversionTask) -> ConversionResult:
        """Convert a single image file and return a structured result."""

        started = time.perf_counter()
        source = task.source_path
        options = task.options

        try:
            output_path = self._build_output_path(source, options)
            if options.duplicate_strategy == "skip" and output_path.exists():
                return ConversionResult(
                    source_path=source,
                    status="skipped",
                    output_path=output_path,
                    elapsed_ms=int((time.perf_counter() - started) * 1000),
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as original:
                image = original.copy()
                metadata = self._collect_metadata(original, options)

            if options.auto_fix_orientation:
                image = ImageOps.exif_transpose(image)

            image = self._resize_if_needed(image, options)
            prepared = self._prepare_for_target(image, options)
            save_kwargs = self._build_save_kwargs(prepared, options, metadata)
            pillow_format = FORMAT_MAP[options.output_format]

            prepared.save(output_path, format=pillow_format, **save_kwargs)
            self._logger.info("Converted %s -> %s", source, output_path)
            return ConversionResult(
                source_path=source,
                status="success",
                output_path=output_path,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            self._logger.exception("Conversion failed for %s", source)
            message = str(exc) or "未知错误"
            return ConversionResult(
                source_path=source,
                status="failed",
                error_message=message,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )

    def _resize_if_needed(self, image: Image.Image, options: ConversionOptions) -> Image.Image:
        if not options.resize_enabled or options.max_long_edge <= 0:
            return image

        width, height = image.size
        longest = max(width, height)
        if longest <= options.max_long_edge:
            return image

        scale = options.max_long_edge / float(longest)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _prepare_for_target(self, image: Image.Image, options: ConversionOptions) -> Image.Image:
        target = options.output_format
        has_alpha = image_has_alpha(image)

        if target in {"jpg", "jpeg"}:
            return self._prepare_jpeg_image(image, options, has_alpha)
        if target == "png":
            return image if image.mode in {"RGB", "RGBA", "L", "LA"} else image.convert("RGBA" if has_alpha else "RGB")
        if target == "webp":
            return image if image.mode in {"RGB", "RGBA", "L", "LA"} else image.convert("RGBA" if has_alpha else "RGB")
        if target == "bmp":
            return image.convert("RGB")
        if target == "tiff":
            if image.mode in {"RGB", "RGBA", "L", "LA", "CMYK"}:
                return image
            return image.convert("RGBA" if has_alpha else "RGB")
        if target == "ico":
            return image.convert("RGBA")

        raise ConversionError(f"暂不支持输出格式：{target}")

    def _prepare_jpeg_image(self, image: Image.Image, options: ConversionOptions, has_alpha: bool) -> Image.Image:
        base_image = image
        if image.mode == "P":
            base_image = image.convert("RGBA" if has_alpha else "RGB")
        elif image.mode not in {"RGB", "RGBA", "L", "LA"}:
            base_image = image.convert("RGBA" if has_alpha else "RGB")

        if has_alpha or base_image.mode in {"RGBA", "LA"}:
            rgba = base_image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, ImageColor.getrgb(options.jpg_background) + (255,))
            composited = Image.alpha_composite(background, rgba)
            return composited.convert("RGB")

        if base_image.mode == "L":
            return base_image
        return base_image.convert("RGB")

    def _build_save_kwargs(self, image: Image.Image, options: ConversionOptions, metadata: dict[str, object]) -> dict[str, object]:
        target = options.output_format
        save_kwargs: dict[str, object] = {}

        if metadata.get("dpi"):
            save_kwargs["dpi"] = metadata["dpi"]

        if options.preserve_icc_profile and metadata.get("icc_profile"):
            save_kwargs["icc_profile"] = metadata["icc_profile"]

        if options.preserve_exif and metadata.get("exif") and target in {"jpg", "jpeg", "png", "webp", "tiff"}:
            save_kwargs["exif"] = metadata["exif"]

        if target in {"jpg", "jpeg"}:
            save_kwargs.update(
                {
                    "quality": options.jpg_quality,
                    "subsampling": 0,
                    "optimize": True,
                }
            )
        elif target == "png":
            save_kwargs["optimize"] = options.png_optimize
        elif target == "webp":
            save_kwargs["lossless"] = options.webp_lossless
            if not options.webp_lossless:
                save_kwargs["quality"] = options.webp_quality
        elif target == "tiff" and options.tiff_compression:
            save_kwargs["compression"] = options.tiff_compression
        elif target == "ico":
            icon_size = min(max(image.size), 256)
            save_kwargs["sizes"] = [(icon_size, icon_size)]

        return save_kwargs

    def _build_output_path(self, source: Path, options: ConversionOptions) -> Path:
        suffix = f".{options.output_format}"
        output_dir = options.output_dir if options.output_mode == "custom" and options.output_dir else source.parent
        base_name = f"{options.rename_prefix}{source.stem}{options.rename_suffix}"
        if options.naming_mode == "source_ext" and source.suffix.lower() == suffix.lower() and output_dir == source.parent:
            base_name = f"{base_name}{options.naming_marker}"
        elif options.naming_mode == "suffix_marker":
            base_name = f"{base_name}{options.naming_marker}"

        candidate = output_dir / f"{base_name}{suffix}"
        if options.duplicate_strategy in {"overwrite", "skip"}:
            return candidate

        if not candidate.exists():
            return candidate

        index = 1
        while True:
            renamed = output_dir / f"{base_name}_{index}{suffix}"
            if not renamed.exists():
                return renamed
            index += 1

    def _collect_metadata(self, original: Image.Image, options: ConversionOptions) -> dict[str, object]:
        exif_data = original.info.get("exif")
        if exif_data and options.auto_fix_orientation:
            exif = original.getexif()
            if exif:
                exif.pop(EXIF_ORIENTATION_TAG, None)
                exif_data = exif.tobytes()
            else:
                exif_data = None

        return {
            "exif": exif_data,
            "icc_profile": original.info.get("icc_profile"),
            "dpi": original.info.get("dpi"),
        }

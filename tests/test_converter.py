import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from app.models.settings import ConversionOptions
from app.models.task import ConversionTask
from app.services.converter import ConverterService


def build_test_logger() -> logging.Logger:
    logger = logging.getLogger("test_converter")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def build_options(output_dir: Path, output_format: str = "jpg") -> ConversionOptions:
    return ConversionOptions(
        output_format=output_format,
        output_mode="custom",
        output_dir=output_dir,
        naming_mode="suffix_marker",
        naming_marker="_converted",
        rename_prefix="",
        rename_suffix="",
        duplicate_strategy="rename",
        jpg_quality=95,
        preserve_exif=True,
        preserve_icc_profile=True,
        jpg_background="#FFFFFF",
        png_optimize=True,
        webp_lossless=True,
        webp_quality=90,
        tiff_compression="tiff_lzw",
        auto_fix_orientation=True,
        resize_enabled=False,
        max_long_edge=1920,
    )


def test_convert_rgba_png_to_jpg_with_background():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / "sample.png"
        image = Image.new("RGBA", (16, 16), (255, 0, 0, 128))
        image.save(source)

        converter = ConverterService(build_test_logger())
        result = converter.convert_file(ConversionTask(source_path=source, options=build_options(temp_path, "jpg")))

        assert result.status == "success"
        assert result.output_path is not None
        assert result.output_path.exists()

        with Image.open(result.output_path) as converted:
            assert converted.mode == "RGB"
            assert converted.size == (16, 16)


def test_duplicate_strategy_rename_avoids_overwrite():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / "sample.png"
        Image.new("RGB", (10, 10), "blue").save(source)

        converter = ConverterService(build_test_logger())
        options = build_options(temp_path, "png")

        first = converter.convert_file(ConversionTask(source_path=source, options=options))
        second = converter.convert_file(ConversionTask(source_path=source, options=options))

        assert first.status == "success"
        assert second.status == "success"
        assert first.output_path != second.output_path


def test_auto_orientation_removes_original_exif_orientation():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / "rotated.jpg"
        image = Image.new("RGB", (10, 20), "red")
        exif = Image.Exif()
        exif[274] = 6
        image.save(source, exif=exif)

        converter = ConverterService(build_test_logger())
        result = converter.convert_file(ConversionTask(source_path=source, options=build_options(temp_path, "jpg")))

        assert result.status == "success"
        assert result.output_path is not None
        with Image.open(result.output_path) as converted:
            assert converted.size == (20, 10)
            assert converted.getexif().get(274) != 6

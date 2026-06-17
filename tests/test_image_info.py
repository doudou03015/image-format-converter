from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from app.utils.image_info import collect_image_info


def test_collect_image_info_detects_alpha():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        path = Path(temp_dir) / "transparent.png"
        Image.new("RGBA", (32, 24), (0, 255, 0, 120)).save(path)

        info = collect_image_info(path)

        assert info.width == 32
        assert info.height == 24
        assert info.has_alpha is True
        assert info.format_name == "PNG"
        assert info.mode == "RGBA"

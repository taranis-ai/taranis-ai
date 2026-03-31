import base64
from io import BytesIO

import pytest
from models.types import COLLECTOR_TYPES
from PIL import Image

from core.config import Config
from core.model.osint_source import OSINTSource


def _make_image_bytes(size: tuple[int, int], image_format: str, mode: str = "RGBA", color: tuple[int, ...] | int = (255, 0, 0, 255)) -> bytes:
    image = Image.new(mode, size, color)
    if image_format == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")
    with BytesIO() as output:
        image.save(output, format=image_format)
        return output.getvalue()


def _to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


_VALID_PNG_BYTES = _make_image_bytes((16, 16), "PNG")
_VALID_PNG_BASE64 = _to_base64(_VALID_PNG_BYTES)
_VALID_JPEG_BASE64 = _to_base64(_make_image_bytes((24, 12), "JPEG", mode="RGB", color=(80, 140, 220)))
_VALID_GIF_BASE64 = _to_base64(_make_image_bytes((8, 8), "GIF", mode="P", color=1))
_WIDE_PNG_BASE64 = _to_base64(_make_image_bytes((Config.OSINT_SOURCE_ICON_PIXELS, Config.OSINT_SOURCE_ICON_PIXELS // 2), "PNG"))
_INVALID_BASE64_IMAGE = _to_base64(b"not-an-image")
_INVALID_IMAGE_BYTES = b"not-an-image"
_SVG_BASE64 = _to_base64(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")


def _assert_normalized_png(icon_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(icon_bytes)) as image:
        assert image.format == "PNG"
        assert image.size == (Config.OSINT_SOURCE_ICON_PIXELS, Config.OSINT_SOURCE_ICON_PIXELS)
        return image.copy()


@pytest.mark.usefixtures("app")
def test_osint_source_creation_normalizes_png_icon(session):
    source = OSINTSource(
        name="Test Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        icon=_VALID_PNG_BASE64,
    )
    session.add(source)
    session.commit()

    assert source.icon is not None
    _assert_normalized_png(source.icon)


@pytest.mark.usefixtures("app")
def test_osint_source_creation_normalizes_jpeg_to_png(session):
    source = OSINTSource(
        name="JPEG Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        icon=_VALID_JPEG_BASE64,
    )
    session.add(source)
    session.commit()

    assert source.icon is not None
    _assert_normalized_png(source.icon)


@pytest.mark.usefixtures("app")
def test_osint_source_creation_contains_non_square_icon(session):
    source = OSINTSource(
        name="Wide Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        icon=_WIDE_PNG_BASE64,
    )
    session.add(source)
    session.commit()

    normalized = _assert_normalized_png(source.icon)
    target_size = Config.OSINT_SOURCE_ICON_PIXELS
    wide_height = target_size // 2
    top_offset = (target_size - wide_height) // 2
    expected_bbox = (0, top_offset, target_size, top_offset + wide_height)
    alpha = normalized.split()[-1]
    assert alpha.getbbox() == expected_bbox
    assert normalized.getpixel((target_size // 2, 0))[3] == 0
    assert normalized.getpixel((target_size // 2, target_size // 2))[3] == 255


@pytest.mark.usefixtures("app")
def test_osint_source_creation_with_invalid_icon_raises():
    with pytest.raises(ValueError):
        OSINTSource(
            name="Invalid",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=_INVALID_BASE64_IMAGE,
        )


@pytest.mark.usefixtures("app")
def test_update_icon_rejects_invalid_image(session):
    source = OSINTSource(
        name="Source",
        description="Desc",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
    )
    session.add(source)
    session.commit()

    with pytest.raises(ValueError):
        source.update_icon(_INVALID_BASE64_IMAGE)


@pytest.mark.usefixtures("app")
def test_update_icon_can_clear_icon(session):
    source = OSINTSource(
        name="Clearable",
        description="Desc",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
    )
    session.add(source)
    session.commit()

    source.update_icon(_VALID_PNG_BYTES)
    assert source.icon is not None
    _assert_normalized_png(source.icon)

    source.update_icon("")
    assert source.icon is None


@pytest.mark.usefixtures("app")
def test_pre_seed_update_removes_invalid_icons(session):
    from core.managers.db_manager import db
    from core.managers.db_seed_manager import pre_seed_update

    source = OSINTSource(
        name="PreSeed",
        description="Desc",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        icon=_VALID_PNG_BASE64,
    )
    session.add(source)
    session.commit()

    # Simulate legacy data with invalid bytes bypassing validation.
    source.icon = _INVALID_IMAGE_BYTES
    db.session.commit()

    pre_seed_update(db.engine)

    db.session.expire_all()
    updated = OSINTSource.get(source.id)
    assert updated is not None
    assert updated.icon is None


@pytest.mark.usefixtures("app")
def test_osint_source_creation_rejects_oversized_icon():
    oversized_icon = _to_base64(b"\x00" * (Config.OSINT_SOURCE_ICON_MAX_BYTES + 1))

    with pytest.raises(ValueError, match="maximum size"):
        OSINTSource(
            name="Too Large",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=oversized_icon,
        )


@pytest.mark.usefixtures("app")
def test_osint_source_creation_rejects_svg_icon():
    with pytest.raises(ValueError, match="SVG icons are not supported"):
        OSINTSource(
            name="SVG Icon",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=_SVG_BASE64,
        )


@pytest.mark.usefixtures("app")
def test_osint_source_creation_rejects_unsupported_image_format():
    with pytest.raises(ValueError, match="Unsupported icon format"):
        OSINTSource(
            name="GIF Icon",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=_VALID_GIF_BASE64,
        )


@pytest.mark.usefixtures("app")
def test_osint_source_creation_converts_decompression_bomb_to_value_error(monkeypatch):
    def raise_decompression_bomb(*args, **kwargs):
        raise Image.DecompressionBombError("Decompression bomb")

    monkeypatch.setattr("core.model.osint_source.Image.open", raise_decompression_bomb)

    with pytest.raises(ValueError, match="Icon payload is not a valid image file."):
        OSINTSource(
            name="Bomb Icon",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=_VALID_PNG_BASE64,
        )

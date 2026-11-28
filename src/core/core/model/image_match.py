"""Conservative matching of static collector images, using Pillow's native image operations."""

from io import BytesIO

from PIL import Image, ImageChops, ImageOps, ImageStat


def color_signature(image: Image.Image) -> bytes:
    # A 192-byte shortlist key. Only candidates with similar colors in the same places need their bytes opened.
    if image.mode in {"P", "1"} or "transparency" in image.info:
        image = image.convert("RGBA")
    sample = ImageOps.exif_transpose(image.resize((8, 8), Image.Resampling.BOX, reducing_gap=3)).convert("RGBA")
    return Image.alpha_composite(Image.new("RGBA", (8, 8), "white"), sample).convert("RGB").tobytes()


def source_key(colors: bytes) -> int:
    # A 49-bit difference hash plus coarse RGB means keeps flat graphics out of a single bucket.
    gray = Image.frombytes("RGB", (8, 8), colors).convert("L").tobytes()
    key = 0
    for channel in range(3):
        key = (key << 4) | (sum(colors[channel::3]) // (64 * 16))
    for row in range(7):
        for col in range(7):
            i = 8 * row + col
            key = (key << 1) | (gray[i] > gray[i + 1])
    return key


def close_colors(first: bytes, second: bytes) -> bool:
    return all(abs(a - b) <= 8 for a, b in zip(first, second, strict=True))


def same_picture(first: bytes, second: bytes, colors: bytes, *, same_article: bool) -> bool:
    try:
        with (
            Image.open(BytesIO(first), formats=("JPEG", "PNG", "WEBP")) as left,
            Image.open(BytesIO(second), formats=("JPEG", "PNG", "WEBP")) as right,
        ):
            return _compare_pixels(left, right, colors, same_article)
    except (ValueError, OSError, EOFError, SyntaxError, IndexError, Image.DecompressionBombError):
        # An older stored file may no longer be decodable. Keep the incoming file in that case.
        return False


def _compare_pixels(left: Image.Image, right: Image.Image, colors: bytes, same_article: bool) -> bool:
    if any(image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"} for image in (left, right)):
        return False
    left.load()
    right.load()
    # Different color profiles or rendering metadata can change the displayed colors.
    if any(left.info.get(key) != right.info.get(key) for key in ("icc_profile", "gamma", "chromaticity", "srgb")):
        return False
    # A reused source file must not introduce another article's embedded captions, EXIF or XMP.
    if not same_article:
        codec_fields = {"jfif", "jfif_version", "jfif_unit", "jfif_density", "dpi", "progressive", "progression", "background", "loop"}
        if any(left.info.get(key) != value for key, value in right.info.items() if key not in codec_fields):
            return False
    ImageOps.exif_transpose(left, in_place=True)
    ImageOps.exif_transpose(right, in_place=True)
    small, large = sorted((left, right), key=lambda image: image.width * image.height)
    aspect_tolerance = 0.01 if same_article else 0.002
    if abs(small.width * large.height - large.width * small.height) > aspect_tolerance * small.width * large.height:
        return False
    resized = large.size != small.size
    lossy = left.format in {"JPEG", "WEBP"} or right.format in {"JPEG", "WEBP"}
    # Keep subtly different solid swatches distinct, even when one is a JPEG.
    has_contrast = any(max(colors[c::3]) - min(colors[c::3]) >= 24 for c in range(3))
    allow_noise = (resized or lossy) and min(small.size) >= 32 and has_contrast
    if same_article and allow_noise:
        # Reduce JPEG edge ringing and differences between publishers' thumbnail resamplers.
        if small.mode not in {"RGB", "RGBA"} or "transparency" in small.info:
            small = small.convert("RGBA")
        small.thumbnail((256, 256), Image.Resampling.LANCZOS)
    if large.size != small.size:
        if large.mode not in {"RGB", "RGBA"} or "transparency" in large.info:
            large = large.convert("RGBA")
        large = large.resize(small.size, Image.Resampling.LANCZOS, reducing_gap=3)
    total_error = 0.0
    for y in range(0, small.height, 128):
        box = (0, y, small.width, min(y + 128, small.height))
        original = small.crop(box).convert("RGBA").convert("RGBa")
        difference = ImageChops.difference(original, large.crop(box).convert("RGBA").convert("RGBa"))
        if not difference.getbbox(alpha_only=False):
            continue
        if not allow_noise:
            return False
        stats = ImageStat.Stat(difference)
        alpha_tolerance = 16 if same_article and resized else 0
        if stats.extrema[3][1] > alpha_tolerance or max(high for _, high in stats.extrema) > (48 if same_article else 24):
            return False
        total_error += sum(stats.sum)
    return total_error <= (3 if same_article else 1) * 3 * small.width * small.height

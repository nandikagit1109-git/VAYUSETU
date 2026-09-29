"""Heuristic photo scorer (section 10) — scorer id "heuristic_v1".

This is a stand-in for a trained haze-classification model: with no internet
and no bundled weights, a trained CNN cannot ship in the offline demo. The
score is a deterministic function of image contrast, brightness and saturation.
The UI must label the result "heuristic estimate".
"""
import base64
import binascii
import io

from PIL import Image, ImageFile

from ..config import PHOTO_MAX_BYTES

# Decompression-bomb guard (section 10): anything bigger is rejected before
# decode, and truncated images fail loudly instead of half-decoding.
Image.MAX_IMAGE_PIXELS = 20_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = False

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

SCORER_ID = "heuristic_v1"
CONFIDENCE = 0.5  # fixed: heuristic, not a calibrated model

MANUAL_SCORES = {
    "clear": (60.0, 0.4),
    "hazy": (180.0, 0.4),
    "very_hazy": (340.0, 0.4),
}


class PhotoError(Exception):
    pass


class ImageTooLarge(PhotoError):
    pass


# Back-compat alias: byte-limit rejections were historically PhotoTooLarge.
PhotoTooLarge = ImageTooLarge


def decode_photo(photo_base64: str, max_bytes: int) -> bytes:
    payload = photo_base64.strip()
    if payload.lower().startswith("data:"):
        # Strip an optional data:...;base64, prefix.
        idx = payload.find(",")
        if idx != -1:
            payload = payload[idx + 1:]
    # Cheap pre-check BEFORE decoding: base64 is 4 chars per 3 bytes, so a
    # payload longer than 4/3 * max_bytes must exceed the limit. Rejecting
    # here stops a multi-GB string from being materialised in memory first.
    if len(payload) > (max_bytes // 3 + 1) * 4:
        raise ImageTooLarge(f"photo exceeds {max_bytes} bytes")
    try:
        raw = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise PhotoError("could not read image") from exc
    if len(raw) > max_bytes:
        raise ImageTooLarge(f"photo exceeds {max_bytes} bytes")
    return raw


def _load_image(raw: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # integrity check
        img = Image.open(io.BytesIO(raw))  # reopen: verify() leaves the image unusable
        img.load()
    except Image.DecompressionBombError as exc:
        raise ImageTooLarge("image too large") from exc
    except Exception as exc:
        raise PhotoError("could not read image") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoError("unsupported image format")
    return img


def score_photo(raw: bytes) -> float:
    """haze_score in [20, 480] from resized gray/HSV statistics."""
    img = _load_image(raw)
    longest = max(img.size)
    scale = 256.0 / longest if longest > 256 else 1.0
    size = (max(1, int(img.size[0] * scale)), max(1, int(img.size[1] * scale)))
    small = img.resize(size)

    gray = small.convert("L")
    pixels = list(gray.getdata())
    n = len(pixels)
    mean = sum(pixels) / n
    std = (sum((p - mean) ** 2 for p in pixels) / n) ** 0.5
    contrast_n = min(1.0, max(0.0, std / 64.0))
    brightness = mean / 255.0

    hsv = small.convert("HSV")
    sat_pixels = list(hsv.getdata())
    sat = sum(p[1] for p in sat_pixels) / len(sat_pixels) / 255.0

    haze_index = min(1.0, max(0.0, 0.5 * (1 - contrast_n) + 0.3 * brightness + 0.2 * (1 - sat)))
    haze_score = min(480.0, max(20.0, 500.0 * haze_index ** 1.2))
    return round(haze_score, 1)


def score_manual(visibility: str) -> tuple[float, float]:
    return MANUAL_SCORES[visibility]


def score_report(photo_raw: bytes | None, manual_visibility: str | None, max_bytes: int | None = None) -> tuple[float, float, str]:
    """Returns (haze_score, confidence, scorer). Photo wins when both given.
    Raises PhotoError only for invalid photo bytes; callers map that to 422."""
    limit = max_bytes if max_bytes is not None else PHOTO_MAX_BYTES
    if photo_raw is not None:
        return score_photo(photo_raw), CONFIDENCE, SCORER_ID
    if manual_visibility is not None:
        score, conf = score_manual(manual_visibility)
        return score, conf, "manual"
    raise PhotoError("nothing to score")

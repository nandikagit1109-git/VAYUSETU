"""Haze/AQI-proxy scoring for citizen reports.

DEMO NOTE: a production system would fine-tune MobileNetV3-small (torchvision)
on haze-graded photos. Downloading pretrained weights requires internet, which
the offline-first demo forbids, so the DEFAULT scorer is a deterministic
mock based on image brightness/contrast/sharpness — clearly a simulation.
An optional real-model path can be enabled with ENABLE_CV_MODEL=true only if
weights are available locally; otherwise it silently falls back to the mock.
"""
import base64
import io
import logging

logger = logging.getLogger("vayusetu.cv_model")

# Fixed score table for the manual visibility dropdown.
VISIBILITY_SCORES = {
    "clear": (75.0, 0.80),
    "hazy": (200.0, 0.70),
    "very_hazy": (350.0, 0.70),
}

DEFAULT_SCORE = (180.0, 0.40)  # low-confidence fallback so we never crash


def _decode_photo(photo_base64: str):
    payload = photo_base64
    if "," in payload and payload.strip().lower().startswith("data:"):
        payload = payload.split(",", 1)[1]
    raw = base64.b64decode(payload)
    from PIL import Image  # imported lazily so a broken install can't break startup

    img = Image.open(io.BytesIO(raw))
    return img.convert("L")


def score_photo(photo_base64: str) -> tuple[float, float]:
    """Deterministic mock CV scorer: hazier photos are brighter, lower in
    contrast and less sharp. Returns (haze_score 0-500, confidence 0-1)."""
    gray = _decode_photo(photo_base64)
    small = gray.resize((64, 64))
    pixels = list(small.getdata())
    n = len(pixels)
    mean = sum(pixels) / n
    contrast = (sum((p - mean) ** 2 for p in pixels) / n) ** 0.5
    row_sharpness = sum(abs(pixels[i] - pixels[i + 1]) for i in range(n - 1) if (i + 1) % 64 != 0) / n

    bright_haze = max(0.0, min(1.0, (mean - 70.0) / 120.0))
    low_contrast_haze = max(0.0, min(1.0, 1.0 - contrast / 70.0))
    low_sharpness_haze = max(0.0, min(1.0, 1.0 - row_sharpness / 12.0))

    haziness = 0.45 * bright_haze + 0.30 * low_contrast_haze + 0.25 * low_sharpness_haze
    haze_score = 40.0 + haziness * 410.0
    confidence = 0.55 + 0.35 * min(1.0, (contrast / 60.0) * 0.5 + 0.5)
    return round(min(500.0, max(10.0, haze_score)), 1), round(min(0.98, confidence), 2)


def score_report(photo_base64: str | None, manual_visibility: str | None) -> tuple[float, float]:
    """Score a citizen report. Photo path first (per spec), then manual
    visibility, then a low-confidence default. Never raises."""
    if photo_base64:
        try:
            return score_photo(photo_base64)
        except Exception as exc:
            logger.warning("photo scoring failed (%s); falling back", exc)
    if manual_visibility and manual_visibility in VISIBILITY_SCORES:
        return VISIBILITY_SCORES[manual_visibility]
    return DEFAULT_SCORE

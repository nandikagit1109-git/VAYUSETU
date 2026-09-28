"""CV scorer + report maths tests (section 14.8 supplementary)."""
import base64
import io

import pytest
from PIL import Image

from app.services import cv_scorer


def _png_bytes(color=(180, 170, 160), size=(320, 240)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    return buf.getvalue()


def test_score_photo_bounds():
    raw = _png_bytes()
    score = cv_scorer.score_photo(raw)
    assert 20.0 <= score <= 480.0


def test_uniform_vs_textured():
    """A flat bright image should look hazier than a high-contrast one."""
    flat = cv_scorer.score_photo(_png_bytes(color=(200, 195, 190)))
    arr = Image.new("RGB", (256, 256))
    px = arr.load()
    for x in range(256):
        for y in range(256):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, (x * y) % 256)
    buf = io.BytesIO()
    arr.save(buf, format="PNG")
    textured = cv_scorer.score_photo(buf.getvalue())
    assert flat > textured


def test_decode_photo_strips_data_uri():
    raw = _png_bytes()
    b64 = base64.b64encode(raw).decode()
    decoded = cv_scorer.decode_photo(f"data:image/png;base64,{b64}", 5_000_000)
    assert decoded == raw


def test_decode_photo_rejects_garbage():
    with pytest.raises(cv_scorer.PhotoError):
        cv_scorer.decode_photo("not base64 at all ###", 5_000_000)


def test_decode_photo_size_limit():
    raw = _png_bytes()
    with pytest.raises(cv_scorer.PhotoTooLarge):
        cv_scorer.decode_photo(base64.b64encode(raw).decode(), 10)


def test_manual_scores():
    assert cv_scorer.score_manual("clear") == (60.0, 0.4)
    assert cv_scorer.score_manual("hazy") == (180.0, 0.4)
    assert cv_scorer.score_manual("very_hazy") == (340.0, 0.4)


def test_photo_wins_over_manual():
    raw = _png_bytes()
    score, conf, scorer = cv_scorer.score_report(raw, "very_hazy")
    assert scorer == cv_scorer.SCORER_ID
    assert conf == 0.5


def test_trust_weight_bounds():
    from app.routers.reports import _trust_weight

    assert _trust_weight(180.0, None) == 0.6  # no reference -> 0.6
    assert _trust_weight(180.0, 180.0) == 1.0  # perfect agreement
    assert _trust_weight(480.0, 20.0) == 0.2  # floor
    assert _trust_weight(20.0, 480.0) == 0.2

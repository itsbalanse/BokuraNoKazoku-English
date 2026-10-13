"""Detect the spring 'Year 35' season banner: both the full 'Year NN' glyphs and the second
digit must match the reference frame (Year 15/25/30 each fail one of the two checks)."""
import os
import numpy as np
from PIL import Image

REF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shots", "year35spr.png")


def ymask(im):
    a = np.asarray(im.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 140) & (g > 120) & (b < 120) & (r - b > 70)


_ref = None


def _iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def score(im):
    global _ref
    if _ref is None:
        _ref = ymask(Image.open(REF))
    m = ymask(im)
    whole = _iou(m[40:62, 75:165], _ref[40:62, 75:165])
    digit = _iou(m[40:62, 146:162], _ref[40:62, 146:162])
    return min(whole, digit) if m[40:62, 75:165].sum() > 0.8 * _ref[40:62, 75:165].sum() else 0.0

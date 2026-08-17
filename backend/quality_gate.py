"""
fynd(cars) — Pixel Quality Gate (Gate 0)
Pre-ingestion check: blur variance (Laplacian) + luminance range.
Cost: ~2ms CPU, $0. Runs before any ML model or API call.
"""
import cv2
import numpy as np


def check_image_quality(image_bytes: bytes) -> tuple[bool, str]:
    """
    Returns (passes: bool, rejection_reason: str).
    Empty reason means the image passed.

    Thresholds (per spec):
      - Blur:      Laplacian variance >= 100.0
      - Luminance: grayscale mean in [40, 220]

    ponytail: single function, no class, no config file — thresholds
    are spec-fixed constants, not tunable at runtime.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return False, "Cannot decode image — unsupported format or corrupted file."

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur check
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if lap_var < 100.0:
        return False, f"Image too blurry for structural inspection (Laplacian variance {lap_var:.1f} < 100.0)."

    # Luminance check
    mean_lum = float(gray.mean())
    if mean_lum < 40:
        return False, f"Image too dark for structural inspection (luminance mean {mean_lum:.1f} < 40)."
    if mean_lum > 220:
        return False, f"Image overexposed for structural inspection (luminance mean {mean_lum:.1f} > 220)."

    return True, ""

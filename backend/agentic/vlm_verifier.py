"""
fynd(cars) — One-Shot VLM Verifier (Gate 4)
Single multimodal call to OpenRouter (google/gemma-4-31b-it:free).
Receives all car images + document images + extracted RC data.
Returns structured verification JSON per spec contract.

Re-uses LLM_BASE_URL / LLM_API_KEY / LLM_MODEL from .env — no extra vars.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("fynd(cars)_api")

# Safe default returned when VLM is unavailable — pipeline never hard-fails
_DEFAULT_RESULT: dict = {
    "same_vehicle": {"is_consistent": True, "detected_make": None, "detected_model": None, "detected_color": None, "confidence": 0.0},
    "viewpoint_coverage": {"is_complete_360": False, "angles_present": [], "missing_angles": ["front_left", "front_right", "rear_left", "rear_right"]},
    "telemetry": {"odometer_visible": False, "odometer_km": None, "confidence": 0.0},
    "legal_identity": {"plate_visible": False, "plate_readout": None, "document_reg_number": None, "matches_document": None, "is_temporary": False, "is_commercial": False, "notes": "VLM unavailable — manual review required."},
    "verdict": "PARTIAL",
    "discrepancies": ["VLM verification skipped — provider not configured."],
}

_SYSTEM_PROMPT = """You are a vehicle verification AI for a used-car marketplace.
You will receive multiple images of a car (exterior, interior, dashboard) and optionally a
registration certificate (RC) document image, plus extracted RC fields as JSON.

Respond ONLY with a single valid JSON object — no markdown fences, no prose, no explanation.
The schema must exactly match:

{
  "same_vehicle": {
    "is_consistent": <bool>,
    "detected_make": <string or null>,
    "detected_model": <string or null>,
    "detected_color": <string or null>,
    "confidence": <float 0-1>
  },
  "viewpoint_coverage": {
    "is_complete_360": <bool>,
    "angles_present": <array of: "front_left"|"front_right"|"rear_left"|"rear_right"|"interior"|"dashboard">,
    "missing_angles": <array>
  },
  "telemetry": {
    "odometer_visible": <bool>,
    "odometer_km": <integer or null — normalize miles to km if needed>,
    "confidence": <float 0-1>
  },
  "legal_identity": {
    "plate_visible": <bool>,
    "plate_readout": <string or null — OCR from photo, account for O↔0 B↔8 substitutions>,
    "document_reg_number": <string or null — from RC fields>,
    "matches_document": <bool or null — null if plate not visible>,
    "is_temporary": <bool>,
    "is_commercial": <bool>,
    "notes": <string — one sentence>
  },
  "verdict": <"PASSED"|"FAILED"|"PARTIAL">,
  "discrepancies": <array of strings — empty if none>
}

Rules:
- PASSED: vehicle consistent, plate matches doc, no fraud signals.
- FAILED: make/model mismatch between photos and doc, OR plate clearly contradicts doc.
- PARTIAL: insufficient data (no plate visible, no odometer, partial coverage) but no active fraud.
- OCR ambiguity (O↔0, B↔8, I↔1): resolve in favour of match when plausible.
- Temporary/dealer plates: set is_temporary=true and do NOT flag as mismatch.
- If all images belong to multiple distinct vehicles: is_consistent=false, verdict=FAILED.
- Multi-vehicle frames: judge by the primary foreground vehicle (>50% frame area).
"""


def _encode_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Build an OpenAI-style image_url content part from raw bytes."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "auto"}}


def verify(
    car_image_bytes: list[bytes],
    doc_image_bytes: list[bytes],
    extracted_rc: Optional[dict] = None,
    *,
    timeout_s: float = 90.0,
) -> dict:
    """
    One-shot VLM call to verify all uploaded assets simultaneously.

    Args:
        car_image_bytes: Raw bytes for each car photo (exterior/interior/dashboard).
        doc_image_bytes: Raw bytes for document images (RC scans).
        extracted_rc:    Docling-extracted RC fields dict (enriches the prompt context).
        timeout_s:       OpenRouter call timeout.

    Returns:
        Structured verification dict per spec contract.
        Falls back to _DEFAULT_RESULT on any error so the pipeline never hard-fails.

    ponytail: single sync httpx call — no retry loop, no circuit breaker.
    Caller (auto-extract route) decides on degraded-mode behaviour.
    """
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    api_key  = os.getenv("LLM_API_KEY", "").strip()
    model    = os.getenv("LLM_MODEL", "google/gemma-4-31b-it:free").strip()

    if not base_url or not api_key:
        logger.warning("VLM verifier: LLM_BASE_URL / LLM_API_KEY not set — returning safe default.")
        return _DEFAULT_RESULT.copy()

    if not base_url.endswith("/v1"):
        base_url += "/v1"
    url = base_url + "/chat/completions"

    # Build message content: text context first, then all images
    content: list[dict] = []

    rc_context = ""
    if extracted_rc:
        rc_context = f"\n\nExtracted RC fields:\n{json.dumps(extracted_rc, indent=2, default=str)}"

    content.append({
        "type": "text",
        "text": (
            f"Analyse the following vehicle images and verify them against the registration document.{rc_context}\n\n"
            "Car photos follow (exterior angles, interior, dashboard). "
            "Then any document/RC scans. Return ONLY the JSON."
        ),
    })

    for img_bytes in car_image_bytes:
        content.append(_encode_image(img_bytes))

    for doc_bytes in doc_image_bytes:
        content.append(_encode_image(doc_bytes))

    payload = {
        "model": model,
        "temperature": 0.1,  # near-deterministic for structured output
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://fynd.cars",
                "X-Title": "fynd(cars)",
            },
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"] or ""
        result = json.loads(raw_text)
        logger.info("VLM verdict: %s", result.get("verdict"))
        return result
    except json.JSONDecodeError as e:
        logger.error("VLM: JSON parse error — %s | raw: %.200s", e, raw_text)
        return _DEFAULT_RESULT.copy()
    except Exception as e:
        logger.error("VLM verifier error: %s", e)
        return _DEFAULT_RESULT.copy()

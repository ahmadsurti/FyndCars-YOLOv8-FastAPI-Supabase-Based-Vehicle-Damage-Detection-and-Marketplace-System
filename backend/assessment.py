"""
fynd(cars) — Shared damage assessment pipeline.
Single source of truth for: YOLOv8 detection → policy decision → stats + expert commentary.
Called by POST /assess (api.py) and POST /listings/{id}/images (routes/listings.py).
"""

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("fynd(cars)_api")

PROJECT_ROOT = Path(__file__).resolve().parent

_detector = None
_agent = None

try:
    from car_damage_detector import CarDamageDetector
    _detector = CarDamageDetector(
        model_path=os.getenv("MODEL_PATH") or None,
        confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.25")),
    )
    logger.info("CarDamageDetector loaded (threshold=%s)", os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
except Exception as e:
    logger.warning("CV module unavailable: %s", e)

try:
    from agentic.decision_agent import DecisionAgent
    _agent = DecisionAgent(policies_dir=PROJECT_ROOT / "policies")
    logger.info("DecisionAgent loaded")
except Exception as e:
    logger.warning("DecisionAgent unavailable: %s", e)

cv_available = _detector is not None
agent_available = _agent is not None


def available() -> bool:
    return cv_available and agent_available


def run_assessment(image_bytes: bytes) -> dict:
    """
    Full pipeline on raw image bytes.
    Returns the assessment payload dict. Keys map to both the /assess API response
    and the Supabase `assessments` columns (except damage_stats / expert_commentary,
    which are response-only — the assessments table has no columns for them).
    """
    import io
    from PIL import Image as PILImage

    from agentic.adapters import pick_primary_detection, detection_to_damage_signal
    from agentic.expert_ai import generate_expert_commentary
    from agentic.schemas import DamageSignal
    from utils import calculate_damage_stats

    start = time.time()
    pil_img = PILImage.open(io.BytesIO(image_bytes))
    result = _detector.detect_damage(pil_img)

    # Normalize detector dicts ("type") to the API shape ("damage_type")
    damages = [
        {
            "damage_type": d.get("type", d.get("damage_type", "unknown")),
            "confidence": d.get("confidence", 0.5),
            "severity": d.get("severity", "minor"),
            "location": d.get("location", "unknown"),
            "bbox": d.get("bbox", []),
            "area_percentage": d.get("area_percentage", 0.0),
            "estimated_cost": d.get("estimated_cost", 0),
        }
        for d in result.get("damages", [])
    ]

    primary = pick_primary_detection(damages)
    if primary:
        sig = detection_to_damage_signal(primary)
        signal = DamageSignal(
            damage_type=sig["damage_type"],
            severity=sig.get("severity"),
            confidence=sig["confidence"],
        )
        decision_confidence = float(sig["confidence"])
        signal_dict = sig
    else:
        signal = DamageSignal(damage_type="none", confidence=0.0)
        decision_confidence = 0.95
        signal_dict = {"damage_type": "none", "severity": "none", "confidence": 0.0}

    dec = _agent.decide(signal)

    commentary = generate_expert_commentary(
        decision_action=dec.action,
        decision_reason=dec.reason,
        sop_evidence=dec.evidence,
        signal=signal_dict,
        primary_detection=primary,
        knowledge_dir=PROJECT_ROOT / "knowledge",
        enable_llm=os.getenv("LLM_ENABLED", "0") == "1",
    )

    return {
        "damages_detected": damages,
        "total_damages": len(damages),
        "decision": dec.action,
        "decision_confidence": round(decision_confidence, 3),
        "decision_trace": [
            {"rule_applied": r, "threshold": "", "evidence": dec.evidence or ""}
            for r in dec.policy_refs
        ],
        "damage_stats": calculate_damage_stats(damages),
        "expert_commentary": commentary.text,
        "human_review_required": dec.action != "AUTO_APPROVE",
        "model_version": "yolov8n-v1",
        "policy_version": "v1.0",
        "cv_backend": "yolov8",
        "processing_time_ms": int((time.time() - start) * 1000),
    }

from __future__ import annotations
from typing import Any, Dict, Optional
from agentic._utils import norm_severity, norm_damage_type


def pick_primary_detection(detections: list[dict]) -> Optional[dict]:
    """Pick the most critical detection: highest severity, then highest confidence."""
    if not detections:
        return None
    # norm_severity() produces lowercase: "minor", "moderate", "severe"
    severity_rank = {"minor": 1, "moderate": 2, "severe": 3}
    return sorted(
        detections,
        key=lambda d: (severity_rank.get(str(d.get("severity", "")).lower(), 0), d.get("confidence", 0.0)),
        reverse=True,
    )[0]


def detection_to_damage_signal(detection: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a CV detection dict to a policy-engine signal dict."""
    return {
        "damage_type": norm_damage_type(detection.get("type", detection.get("damage_type", ""))),
        "severity": norm_severity(detection.get("severity", "")),
        "confidence": float(detection.get("confidence", 0.0)),
        "bbox": detection.get("bbox"),
        "area_percentage": float(detection.get("area_percentage", 0.0)),
        "estimated_cost": float(detection.get("estimated_cost", 0.0)),
        "raw": detection,
    }

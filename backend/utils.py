"""
fynd(cars) — Shared helpers for the FastAPI backend.
Single source of truth for assessment stats, timestamps, and asset downloads.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx
from db import supabase


def utc_now_iso() -> str:
    """Return current UTC time in ISO format with timezone."""
    return datetime.now(timezone.utc).isoformat()


async def fetch_image_bytes(storage_path: str) -> Optional[bytes]:
    """Download image bytes from a public URL or Supabase Storage 'bucket/path'."""
    if storage_path.startswith(("http://", "https://")):
        async with httpx.AsyncClient() as client:
            resp = await client.get(storage_path, timeout=15.0)
            return resp.content if resp.status_code == 200 else None
    if supabase:
        bucket, _, fpath = storage_path.partition("/")
        if fpath:
            return supabase.storage.from_(bucket).download(fpath)
    return None


def calculate_damage_stats(detections: List[Dict]) -> Dict:
    """Aggregate stats from a list of damage detections (damage_type-keyed, type tolerated)."""
    if not detections:
        return {
            "total_damages": 0, "damage_types": {}, "severity_distribution": {"minor": 0, "moderate": 0, "severe": 0},
            "average_confidence": 0.0, "total_area_affected": 0.0, "total_estimated_cost": 0, "risk_assessment": "No damage detected",
            "most_common_damage": "none",
        }

    types: Dict[str, int] = {}
    severity_counts = {"minor": 0, "moderate": 0, "severe": 0}
    total_area = total_cost = 0.0
    confidences = []

    for d in detections:
        t = d.get("damage_type", d.get("type", "unknown"))
        types[t] = types.get(t, 0) + 1
        sev = d.get("severity", "minor")
        if sev in severity_counts:
            severity_counts[sev] += 1
        total_area += d.get("area_percentage", 0.0)
        total_cost += d.get("estimated_cost", 0)
        confidences.append(d.get("confidence", 0.0))

    risk = "High" if severity_counts["severe"] > 0 else "Moderate" if severity_counts["moderate"] > 1 else "Low-Moderate" if severity_counts["moderate"] else "Low"

    return {
        "total_damages": len(detections),
        "damage_types": types,
        "severity_distribution": severity_counts,
        "average_confidence": round(sum(confidences) / len(confidences), 3),
        "total_area_affected": round(total_area, 2),
        "total_estimated_cost": int(total_cost),
        "risk_assessment": risk,
        "most_common_damage": max(types, key=types.get) if types else "none",
    }

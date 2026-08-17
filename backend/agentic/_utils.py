"""
Shared micro-utilities for the agentic package.
ponytail: single source for pick/_norm_* used across agentic modules.
"""
from __future__ import annotations
from typing import Any


def pick(d: Any, key: str, default=None):
    if d is None:
        return default
    if isinstance(d, dict):
        return d.get(key, default)
    return getattr(d, key, default)


def norm_severity(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    return {"light": "minor", "minor": "minor", "moderate": "moderate",
            "medium": "moderate", "severe": "severe", "critical": "severe",
            "high": "severe"}.get(s, s.replace(" ", "_") or "unknown")


def norm_damage_type(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if "scratch" in s:
        return "scratch"
    if "dent" in s:
        return "dent"
    if "paint" in s:
        return "paint_damage"
    if "broken" in s or "part" in s:
        return "broken_part"
    return s.replace(" ", "_") or "unknown"

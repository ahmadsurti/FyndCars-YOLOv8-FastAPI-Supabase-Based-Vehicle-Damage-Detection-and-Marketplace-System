from __future__ import annotations
from pathlib import Path
from typing import Tuple


def extract_section(markdown_text: str, anchor: str) -> str:
    """Extract section under ## <anchor> until next ## heading."""
    target = f"## {anchor.lstrip('#').strip()}".lower()
    lines = markdown_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].strip().startswith("## ")), len(lines))
            return "\n".join(lines[i:end]).strip()
    return ""


def load_sop_section(policies_dir: str | Path, sop_ref: str) -> Tuple[str, str]:
    """sop_ref: 'damage_triage.md#minor-scratch' -> ('SOP:...', text)"""
    fname, _, anchor = sop_ref.partition("#")
    text = (Path(policies_dir) / fname).read_text(encoding="utf-8")
    return f"SOP:{fname}{'#' + anchor if anchor else ''}", extract_section(text, anchor) if anchor else text

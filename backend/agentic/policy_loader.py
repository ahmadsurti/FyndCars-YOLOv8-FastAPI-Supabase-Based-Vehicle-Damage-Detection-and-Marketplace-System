from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import yaml


@dataclass
class Rule:
    name: str
    cond: Dict[str, Any]
    action: str
    sop_ref: str
    reason: str


@dataclass
class Policy:
    thresholds: Dict[str, float]
    rules: List[Rule]


def load_policy(policies_dir: str | Path) -> Policy:
    try:
        data = yaml.safe_load((Path(policies_dir) / "rules.yaml").read_text(encoding="utf-8")) or {}
    except Exception:
        return Policy(thresholds={}, rules=[])

    rules = []
    for item in data.get("rules", []):
        if not isinstance(item, dict):
            continue
        then_block = item.get("then") if isinstance(item.get("then"), dict) else {}
        rules.append(
            Rule(
                name=item.get("name", "unnamed_rule"),
                cond=item.get("if") if isinstance(item.get("if"), dict) else {},
                action=then_block.get("action", "HUMAN_REVIEW"),
                sop_ref=then_block.get("sop_ref", ""),
                reason=then_block.get("reason", ""),
            )
        )
    return Policy(thresholds=data.get("thresholds") or {}, rules=rules)


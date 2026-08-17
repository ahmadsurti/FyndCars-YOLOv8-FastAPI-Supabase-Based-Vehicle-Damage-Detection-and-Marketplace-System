from __future__ import annotations
from pathlib import Path
from agentic._utils import pick
from agentic.policy_loader import Policy, load_policy
from agentic.schemas import Decision, DamageSignal
from agentic.sop_retriever import load_sop_section


def _match_rule(signal, cond: dict) -> bool:
    dtype = pick(signal, "damage_type")
    sev = pick(signal, "severity")
    conf = float(pick(signal, "confidence", 0.0))

    if "damage_type_in" in cond and dtype not in cond["damage_type_in"]:
        return False
    if "severity_in" in cond and sev not in cond["severity_in"]:
        return False
    if "confidence_gte" in cond and conf < float(cond["confidence_gte"]):
        return False
    if "confidence_lt" in cond and conf >= float(cond["confidence_lt"]):
        return False
    return True


def _extract_next_steps(sop_text: str) -> list[str]:
    if not sop_text:
        return []
    lines = [line.strip() for line in sop_text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if line.lower().startswith("**next steps:**"):
            after = line.split(":", 1)[-1].strip()
            if after:
                return [after]
            steps = []
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("- "):
                    steps.append(lines[j][2:].strip())
                else:
                    break
            return steps
    return []


class DecisionAgent:
    """Policy-first triage agent evaluated against rules.yaml and SOP docs."""

    def __init__(self, policies_dir: str | Path = "policies"):
        self.policies_dir = Path(policies_dir)
        self.policy: Policy = load_policy(self.policies_dir)

    def decide(self, signal: DamageSignal) -> Decision:
        for rule in self.policy.rules:
            if _match_rule(signal, rule.cond):
                policy_ref, sop_text = load_sop_section(self.policies_dir, rule.sop_ref)
                return Decision(
                    action=rule.action,  # type: ignore
                    reason=rule.reason,
                    policy_refs=[policy_ref],
                    next_steps=_extract_next_steps(sop_text),
                    evidence=sop_text[:1200] if sop_text else None,
                )

        policy_ref, sop_text = load_sop_section(self.policies_dir, "damage_triage.md#low-confidence")
        return Decision(
            action="HUMAN_REVIEW",
            reason="No policy rule matched. Defaulting to human review for safety.",
            policy_refs=[policy_ref],
            next_steps=_extract_next_steps(sop_text) or ["Request additional images and verify context."],
            evidence=sop_text[:1200] if sop_text else None,
        )

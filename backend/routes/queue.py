"""
fynd(cars) — Admin Review Queue & Override API
Human-in-the-loop governance for HUMAN_REVIEW and ESCALATE listings.
Admin-only (assessor role removed; admin is the sole reviewer).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from db import supabase
from middleware.auth import require_role

router = APIRouter(prefix="/queue", tags=["Review Queue"])


class OverrideRequest(BaseModel):
    override_decision: str = Field(..., description="APPROVE | REJECT")
    reason: str = Field(..., min_length=10, description="Auditable reasoning")


@router.get("", dependencies=[Depends(require_role(["admin"]))])
async def get_review_queue(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Listings pending human review (status: pending or escalated), with images and assessments."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("listings")
        .select("*, listing_images(*), assessments(*), profiles(full_name, email)")
        .in_("status", ["pending", "escalated"])
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data


@router.post(
    "/{listing_id}/override",
    status_code=status.HTTP_201_CREATED,
)
async def submit_override(
    listing_id: str,
    payload: OverrideRequest,
    user: dict = Depends(require_role(["admin"])),
):
    """
    Admin submits an override decision.
    - Updates listing.status to 'active' (APPROVE) or 'rejected' (REJECT)
    - Writes an immutable audit record to assessment_overrides
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    decision_norm = payload.override_decision.upper()
    if decision_norm not in ("APPROVE", "REJECT"):
        raise HTTPException(400, "override_decision must be APPROVE or REJECT")

    listing_res = (
        supabase.table("listings")
        .select("id, status")
        .eq("id", listing_id)
        .single()
        .execute()
    )
    if not listing_res.data:
        raise HTTPException(404, "Listing not found")
    if listing_res.data["status"] not in ("pending", "escalated"):
        raise HTTPException(400, f"Listing status is '{listing_res.data['status']}' — only pending/escalated can be overridden")

    asm_res = (
        supabase.table("assessments")
        .select("id, decision")
        .eq("listing_id", listing_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not asm_res.data:
        raise HTTPException(400, "No assessment found for this listing. Cannot override.")

    assessment = asm_res.data[0]
    new_status = "active" if decision_norm == "APPROVE" else "rejected"

    supabase.table("listings").update({"status": new_status}).eq("id", listing_id).execute()

    override_row = {
        "assessment_id": assessment["id"],
        "listing_id": listing_id,
        "assessor_id": user["id"],
        "original_decision": assessment["decision"],
        "override_decision": decision_norm,
        "reason": payload.reason,
    }
    override_res = supabase.table("assessment_overrides").insert(override_row).execute()

    return {
        "listing_id": listing_id,
        "new_status": new_status,
        "audit_record": override_res.data[0] if override_res.data else override_row,
    }


@router.get("/audit-log")
async def get_audit_log(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                        user: dict = Depends(require_role(["admin"]))):
    """Full override audit log. Admin-only."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("assessment_overrides")
        .select("*, profiles(full_name, email), listings(title, make, model, year)")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data

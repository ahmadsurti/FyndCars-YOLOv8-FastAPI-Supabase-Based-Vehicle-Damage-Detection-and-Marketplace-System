"""
fynd(cars) — Admin API
User management, role assignment, platform analytics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import supabase
from middleware.auth import require_role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(["admin"]))],
)


def _db():
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    return supabase

VALID_ROLES = ("admin", "seller", "buyer")


class RoleUpdate(BaseModel):
    new_role: str = Field(..., description="admin | seller | buyer")


class DocumentVerification(BaseModel):
    verification_status: str = Field(..., description="verified | rejected")
    rejection_reason: Optional[str] = Field(None, description="Mandatory when rejecting")


@router.get("/users")
async def list_users(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """All platform profiles with roles."""
    return _db().table("profiles").select(
        "id, full_name, phone, role, region, created_at, updated_at"
    ).order("created_at", desc=True).range(offset, offset + limit - 1).execute().data


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, payload: RoleUpdate):
    """Assign a new role to a user."""
    db = _db()
    if payload.new_role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {VALID_ROLES}")

    existing = db.table("profiles").select("id, role, full_name").eq("id", user_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "User not found")

    res = db.table("profiles").update({"role": payload.new_role}).eq("id", user_id).execute()
    return {
        "user_id": user_id,
        "old_role": existing.data["role"],
        "new_role": payload.new_role,
        "profile": res.data[0] if res.data else None,
    }


@router.patch("/documents/{document_id}/verify")
async def verify_listing_document(document_id: str, payload: DocumentVerification):
    """Verify or reject a legal document (RC, insurance, etc.)."""
    db = _db()
    decision = payload.verification_status.lower()
    if decision not in ("verified", "rejected"):
        raise HTTPException(400, "verification_status must be 'verified' or 'rejected'")
    if decision == "rejected" and (not payload.rejection_reason or len(payload.rejection_reason.strip()) < 5):
        raise HTTPException(400, "A rejection reason of at least 5 characters is required")

    existing = db.table("listing_documents").select("id, listing_id, document_type, verification_status").eq("id", document_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(404, "Document not found")

    previous_status = existing.data[0]["verification_status"]
    updates = {
        "verification_status": decision,
        "rejection_reason": payload.rejection_reason if decision == "rejected" else None,
    }
    res = db.table("listing_documents").update(updates).eq("id", document_id).execute()
    return {
        "document_id": document_id,
        "previous_status": previous_status,
        **(res.data[0] if res.data else updates),
    }


@router.get("/subscriptions")
async def list_all_subscriptions(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Every subscription on the platform."""
    return _db().table("user_subscriptions").select("*").order("created_at", desc=True).range(offset, offset + limit - 1).execute().data


@router.get("/stats")
async def get_platform_stats():
    """Executive KPIs: listing status distribution, auto-approval rate, total users/overrides."""
    db = _db()
    listings = db.table("listings").select("status, assessments(decision)").execute().data or []
    status_counts: dict[str, int] = {}
    auto_approved = 0

    for listing in listings:
        s = listing.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        for asm in (listing.get("assessments") or []):
            if asm.get("decision") == "AUTO_APPROVE":
                auto_approved += 1

    total = len(listings)
    overrides_res = db.table("assessment_overrides").select("id", count="exact").execute()
    users_res = db.table("profiles").select("id", count="exact").execute()

    return {
        "total_listings": total,
        "by_status": status_counts,
        "auto_approval_rate_percent": round((auto_approved / max(total, 1)) * 100, 1),
        "total_overrides": overrides_res.count or 0,
        "total_users": users_res.count or 0,
    }


@router.get("/audit")
async def get_full_audit(limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Full audit log of all assessor overrides."""
    return _db().table("assessment_overrides").select(
        "*, profiles(full_name, email), listings(title)"
    ).order("created_at", desc=True).range(offset, offset + limit - 1).execute().data

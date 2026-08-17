"""
fynd(cars) — Marketplace Listings API
Wired to Supabase via service_role client.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import httpx

import assessment
from db import supabase
from middleware.auth import get_current_user, require_role

logger = logging.getLogger("fynd(cars)_api")
router = APIRouter(prefix="/listings", tags=["Listings"])


class ImageUpload(BaseModel):
    storage_path: str = Field(..., description="Supabase Storage path or public image URL")
    is_primary: bool = False
    order_index: int = 0
    auto_assess: bool = True


class DocumentUpload(BaseModel):
    document_type: str = Field(..., description="ownership_title | road_inspection | insurance_proof | loan_clearance | service_history")
    document_name: Optional[str] = None
    storage_path: str


class ListingCreate(BaseModel):
    make: str
    model: str
    year: int = Field(ge=1900, le=2100)
    variant: Optional[str] = None
    price: float = Field(gt=0)
    currency: str = "INR"
    fuel_type: str
    transmission: str
    mileage_km: int = Field(ge=0)
    owner_count: int = Field(1, ge=1, le=10)
    city: str
    body_type: Optional[str] = None
    color: Optional[str] = None
    insurance_valid_until: Optional[str] = None
    insurance_type: Optional[str] = None
    description: Optional[str] = None


class SaleRecord(BaseModel):
    buyer_id: Optional[str] = Field(None, description="Buyer's profile id — recorded so they can leave a verified review")


# --- Public feed (no auth, lightweight — no raw assessment data) ---

_SORTS = {
    "newest": ("created_at", True),
    "oldest": ("created_at", False),
    "price_asc": ("price", False),
    "price_desc": ("price", True),
    "year_desc": ("year", True),
    "mileage_asc": ("mileage_km", False),
}


@router.get("", tags=["Listings"])
async def list_listings(
    status_filter: str = "active",
    make: Optional[str] = None,
    model: Optional[str] = None,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    fuel_type: Optional[str] = None,
    transmission: Optional[str] = None,
    body_type: Optional[str] = None,
    max_mileage_km: Optional[int] = None,
    features: Optional[str] = Query(None, description="Comma-separated equipment tags, e.g. 'Sunroof,Cruise Control'"),
    q: Optional[str] = Query(None, description="Free-text search on the auto-generated title"),
    sort: str = "newest",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Public marketplace feed with full faceted search.
    Images included; assessment details via GET /listings/{id}/assessment.
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    if sort not in _SORTS:
        raise HTTPException(400, f"Invalid sort. Must be one of: {', '.join(_SORTS)}")
    sort_col, sort_desc = _SORTS[sort]
    query = (
        supabase.table("listings")
        .select("*, listing_images(*)")
        .order(sort_col, desc=sort_desc)
        .range(offset, offset + limit - 1)
    )
    if status_filter != "all":
        query = query.eq("status", status_filter)
    if make:
        query = query.ilike("make", make)
    if model:
        query = query.ilike("model", model)
    if city:
        query = query.ilike("city", city)
    if min_price is not None:
        query = query.gte("price", min_price)
    if max_price is not None:
        query = query.lte("price", max_price)
    if min_year is not None:
        query = query.gte("year", min_year)
    if max_year is not None:
        query = query.lte("year", max_year)
    if fuel_type:
        query = query.eq("fuel_type", fuel_type.lower())
    if transmission:
        query = query.eq("transmission", transmission.lower())
    if body_type:
        query = query.eq("body_type", body_type.lower())
    if max_mileage_km is not None:
        query = query.lte("mileage_km", max_mileage_km)
    if features:
        tags = [t.strip() for t in features.split(",") if t.strip()]
        if tags:
            query = query.contains("features", tags)
    if q:
        query = query.ilike("title", f"%{q}%")
    return query.execute().data


@router.get("/mine", tags=["Listings"])
async def my_listings(user: dict = Depends(get_current_user)):
    """All of the current user's listings, any status — the seller dashboard feed."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("listings")
        .select("*, listing_images(*)")
        .eq("seller_id", user["id"])
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return res.data


@router.get("/{listing_id}", tags=["Listings"])
async def get_listing(listing_id: str):
    """Single listing with images and documents. Assessment details via separate endpoint."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("listings")
        .select("*, listing_images(*), listing_documents(*)")
        .eq("id", listing_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Listing not found")
    return res.data


# --- Authenticated endpoints ---

@router.post("", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def create_listing(
    payload: ListingCreate,
    user: dict = Depends(require_role(["seller", "admin"])),
):
    """Seller creates a new listing (status=draft). Images uploaded separately."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    row = {
        "seller_id": user["id"],
        "make": payload.make, "model": payload.model, "year": payload.year,
        "variant": payload.variant, "price": payload.price, "currency": payload.currency,
        "fuel_type": payload.fuel_type, "transmission": payload.transmission,
        "mileage_km": payload.mileage_km, "owner_count": payload.owner_count,
        "city": payload.city, "body_type": payload.body_type, "color": payload.color,
        "insurance_valid_until": payload.insurance_valid_until,
        "insurance_type": payload.insurance_type, "description": payload.description,
        "status": "draft",
    }
    res = supabase.table("listings").insert(row).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create listing")
    return res.data[0]


@router.patch("/{listing_id}", tags=["Listings"])
async def update_listing(
    listing_id: str, payload: dict, user: dict = Depends(get_current_user),
):
    """Seller updates their own draft listing. Admin can update any."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] not in ("draft",) and user["role"] != "admin":
        raise HTTPException(400, "Only draft listings can be edited")
    payload.pop("status", None)
    payload.pop("seller_id", None)
    res = supabase.table("listings").update(payload).eq("id", listing_id).execute()
    return res.data[0] if res.data else {"status": "updated"}


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Listings"])
async def delete_listing(listing_id: str, user: dict = Depends(get_current_user)):
    """Seller can only delete their own draft listings. Admin can delete any."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    is_owner = existing.data["seller_id"] == user["id"]
    is_admin = user["role"] == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(403, "Not authorized")
    if is_owner and not is_admin and existing.data["status"] != "draft":
        raise HTTPException(400, "Only draft listings can be deleted by seller")
    supabase.table("listings").delete().eq("id", listing_id).execute()


# --- Helpers ---

async def fetch_image_bytes(storage_path: str) -> Optional[bytes]:
    """Download image bytes from a public URL or a Supabase Storage 'bucket/path'."""
    if storage_path.startswith(("http://", "https://")):
        async with httpx.AsyncClient() as client:
            resp = await client.get(storage_path, timeout=15.0)
            return resp.content if resp.status_code == 200 else None
    if supabase:
        bucket, _, fpath = storage_path.partition("/")
        if fpath:
            return supabase.storage.from_(bucket).download(fpath)
    return None


# assessments-table columns written on auto-assess (damage_stats/expert_commentary are response-only)
ASSESSMENT_DB_FIELDS = (
    "damages_detected", "total_damages", "decision", "decision_confidence", "decision_trace",
    "model_version", "policy_version", "cv_backend", "processing_time_ms",
)

_DECISION_RANK = {"ESCALATE": 3, "HUMAN_REVIEW": 2, "AUTO_APPROVE": 1}


def _worst_decision(assessments: list) -> str:
    """Pick the most severe decision from a list of assessment rows."""
    if not assessments:
        return "HUMAN_REVIEW"  # no assessments → needs review
    return max(assessments, key=lambda a: _DECISION_RANK.get(a.get("decision", "AUTO_APPROVE"), 0)).get("decision", "HUMAN_REVIEW")


# --- Image / Document upload ---

@router.post("/{listing_id}/images", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def upload_listing_image(
    listing_id: str, payload: ImageUpload,
    user: dict = Depends(require_role(["seller", "admin"])),
):
    """
    Register an uploaded image for a listing and optionally run damage assessment.
    Assessment is saved per-image but listing status is NOT flipped here —
    the decision happens at submit time (POST /listings/{id}/submit).
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] not in ("draft",) and user["role"] != "admin":
        raise HTTPException(400, "Can only upload images to draft listings")

    img_row = {"listing_id": listing_id, "storage_path": payload.storage_path,
               "is_primary": payload.is_primary, "order_index": payload.order_index}
    img_res = supabase.table("listing_images").insert(img_row).execute()
    if not img_res.data:
        raise HTTPException(500, "Failed to register image")
    image_record = img_res.data[0]

    assessment_record = None
    damage_stats = expert_commentary = None
    if payload.auto_assess and assessment.available():
        try:
            image_bytes = await fetch_image_bytes(payload.storage_path)
            if image_bytes:
                result = assessment.run_assessment(image_bytes)
                damage_stats = result["damage_stats"]
                expert_commentary = result["expert_commentary"]
                asm_row = {"listing_id": listing_id, "image_id": image_record["id"],
                           "assessment_id_ext": str(uuid.uuid4())[:12],
                           **{k: result[k] for k in ASSESSMENT_DB_FIELDS}}
                asm_res = supabase.table("assessments").insert(asm_row).execute()
                if asm_res.data:
                    assessment_record = asm_res.data[0]
        except Exception as assess_err:
            logger.error("Auto-assessment error: %s", assess_err)

    return {"image": image_record, "assessment": assessment_record,
            "damage_stats": damage_stats, "expert_commentary": expert_commentary}


@router.post("/{listing_id}/documents", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def upload_listing_document(
    listing_id: str, payload: DocumentUpload,
    user: dict = Depends(require_role(["seller", "admin"])),
):
    """Seller uploads a document record (RC/Title, insurance, etc.) for a listing."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] not in ("draft",) and user["role"] != "admin":
        raise HTTPException(400, "Can only upload documents to draft listings")

    doc_row = {"listing_id": listing_id, "document_type": payload.document_type,
               "document_name": payload.document_name, "storage_path": payload.storage_path,
               "verification_status": "pending"}
    res = supabase.table("listing_documents").insert(doc_row).execute()
    if not res.data:
        raise HTTPException(500, "Failed to record document")
    return res.data[0]


# --- Submit & Assessment ---

@router.post("/{listing_id}/submit", tags=["Listings"])
async def submit_listing(
    listing_id: str, user: dict = Depends(require_role(["seller", "admin"])),
):
    """
    Move listing from draft → the correct review status.
    DB trigger validates: minimum 3 images + ownership_title document required.
    Then reads ALL assessments to determine listing status:
      - Any ESCALATE           → escalated
      - Any HUMAN_REVIEW       → pending
      - All AUTO_APPROVE       → active (auto-approved, no human review needed)
      - No assessments         → pending (needs review)
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] != "draft":
        raise HTTPException(400, f"Listing is already '{existing.data['status']}'")

    # Step 1: draft → pending (triggers DB validation: 3 images + ownership doc)
    try:
        supabase.table("listings").update({"status": "pending"}).eq("id", listing_id).execute()
    except Exception as e:
        raise HTTPException(400, str(e))

    # Step 2: read all assessments and pick worst decision
    asm_res = (
        supabase.table("assessments")
        .select("decision")
        .eq("listing_id", listing_id)
        .execute()
    )
    worst = _worst_decision(asm_res.data or [])
    final_status = {"ESCALATE": "escalated", "HUMAN_REVIEW": "pending"}.get(worst, "active")

    # Step 3: set final status
    res = supabase.table("listings").update({"status": final_status}).eq("id", listing_id).execute()
    return {"listing_id": listing_id, "final_status": final_status, **res.data[0]}


@router.post("/{listing_id}/sell", tags=["Listings"])
async def mark_listing_sold(
    listing_id: str,
    payload: Optional[SaleRecord] = None,
    user: dict = Depends(require_role(["seller", "admin"])),
):
    """
    Close a deal: active → sold. Records sold_at and (optionally) the buyer,
    which is what entitles that buyer to leave a verified seller review.
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    existing = supabase.table("listings").select("seller_id, status").eq("id", listing_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data[0]["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data[0]["status"] != "active":
        raise HTTPException(400, f"Only active listings can be marked sold (current: '{existing.data[0]['status']}')")

    updates = {
        "status": "sold",
        "sold_at": datetime.now(timezone.utc).isoformat(),
        "buyer_id": payload.buyer_id if payload else None,
    }
    res = supabase.table("listings").update(updates).eq("id", listing_id).execute()
    return res.data[0] if res.data else {"listing_id": listing_id, **updates}


@router.get("/{listing_id}/assessment", tags=["Listings"])
async def get_listing_assessment(listing_id: str):
    """Get the latest AI assessment for a listing."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("assessments")
        .select("*")
        .eq("listing_id", listing_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "No assessment found for this listing")
    return res.data[0]

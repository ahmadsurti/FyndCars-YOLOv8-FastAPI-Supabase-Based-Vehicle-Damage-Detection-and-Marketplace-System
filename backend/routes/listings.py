"""
fynd(cars) — Marketplace Listings API
Unified AI Intake (POST /auto-extract), verification guards, and catalog endpoints.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

import assessment
import quality_gate
from agentic import rc_extractor, vlm_verifier
from db import supabase
from middleware.auth import get_current_user, require_role
from utils import fetch_image_bytes, utc_now_iso

logger = logging.getLogger("fynd(cars)_api")
router = APIRouter(prefix="/listings", tags=["Listings"])


def _db():
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    return supabase

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ImageUpload(BaseModel):
    storage_path: str = Field(..., description="Supabase Storage path or public URL")
    is_primary: bool = False
    order_index: int = 0
    auto_assess: bool = True


class DocumentUpload(BaseModel):
    document_type: str = Field(..., description="ownership_title | road_inspection | insurance_proof | loan_clearance | service_history")
    document_name: Optional[str] = None
    storage_path: str


class SaleRecord(BaseModel):
    buyer_id: Optional[str] = Field(None, description="Buyer profile id for verified review")


# ---------------------------------------------------------------------------
# Constants & Helpers
# ---------------------------------------------------------------------------

_SORTS = {
    "newest":      ("created_at", True),
    "oldest":      ("created_at", False),
    "price_asc":   ("price", False),
    "price_desc":  ("price", True),
    "year_desc":   ("year", True),
    "mileage_asc": ("mileage_km", False),
}

_DECISION_RANK = {"ESCALATE": 3, "HUMAN_REVIEW": 2, "AUTO_APPROVE": 1}
_SEV_RANK = {"severe": 3, "moderate": 2, "minor": 1, "none": 0}

ASSESSMENT_DB_FIELDS = (
    "damages_detected", "total_damages", "decision", "decision_confidence",
    "decision_trace", "model_version", "policy_version", "cv_backend", "processing_time_ms",
)


def _worst_decision(assessments: list) -> str:
    if not assessments:
        return "HUMAN_REVIEW"
    return max(assessments, key=lambda a: _DECISION_RANK.get(a.get("decision", "AUTO_APPROVE"), 0)).get("decision", "HUMAN_REVIEW")


# ---------------------------------------------------------------------------
# Public Listings Feed
# ---------------------------------------------------------------------------

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
    features: Optional[str] = Query(None, description="Comma-separated tags"),
    q: Optional[str] = Query(None, description="Free-text title search"),
    sort: str = "newest",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Public marketplace feed with full faceted search."""
    db = _db()
    if sort not in _SORTS:
        raise HTTPException(400, f"Invalid sort. Must be one of: {', '.join(_SORTS)}")

    sort_col, sort_desc = _SORTS[sort]
    query = db.table("listings").select("*, listing_images(*)").order(sort_col, desc=sort_desc).range(offset, offset + limit - 1)

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
    """All listings owned by the logged-in user."""
    return _db().table("listings").select("*, listing_images(*)").eq("seller_id", user["id"]).order("created_at", desc=True).limit(100).execute().data


@router.get("/{listing_id}", tags=["Listings"])
async def get_listing(listing_id: str):
    """Single listing with images, documents, and telemetry columns."""
    res = _db().table("listings").select("*, listing_images(*), listing_documents(*)").eq("id", listing_id).single().execute()
    if not res.data:
        raise HTTPException(404, "Listing not found")
    return res.data


# ---------------------------------------------------------------------------
# CORE INTAKE: POST /listings/auto-extract
# ---------------------------------------------------------------------------

@router.post("/auto-extract", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def auto_extract(
    images: list[UploadFile] = File(..., description="Car photos (min 3)"),
    document: UploadFile = File(..., description="Registration Certificate (PDF or image)"),
    user: dict = Depends(require_role(["seller", "admin"])),
):
    """
    Automated Intake Pipeline:
    Gate 0  -> Pixel quality check (OpenCV blur/luminance)
    Gate 1a -> YOLOv8 damage inspection
    Gate 1b -> Docling RC OCR & entity extraction
    Gate 1c -> Gemma 4 multimodal VLM verification & odometer telemetry
    Gate 2  -> Draft listing inserted with telemetry metadata
    """
    db = _db()
    if len(images) < 3:
        raise HTTPException(400, "Minimum 3 car photos required.")

    # Gate 0: Quality Check
    car_bytes_list: list[bytes] = []
    for img in images:
        raw = await img.read()
        passes, reason = quality_gate.check_image_quality(raw)
        if not passes:
            raise HTTPException(400, f"Image '{img.filename}' rejected — {reason}")
        car_bytes_list.append(raw)

    doc_bytes = await document.read()

    # Upload to Supabase Storage
    image_paths: list[str] = []
    for img, raw in zip(images, car_bytes_list):
        ext = (img.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
        path = f"listings/{user['id']}/{uuid.uuid4()}.{ext}"
        db.storage.from_("car-images").upload(path, raw, {"content-type": img.content_type or "image/jpeg"})
        image_paths.append(f"car-images/{path}")

    doc_ext = (document.filename or "doc.pdf").rsplit(".", 1)[-1].lower()
    doc_path = f"listings/{user['id']}/{uuid.uuid4()}.{doc_ext}"
    db.storage.from_("car-documents").upload(doc_path, doc_bytes, {"content-type": document.content_type or "application/pdf"})
    doc_storage_path = f"car-documents/{doc_path}"

    # Gate 1a: YOLOv8 Damage Assessment
    all_damages, damage_assessments = [], []
    if assessment.available():
        for raw in car_bytes_list:
            try:
                res = assessment.run_assessment(raw)
                all_damages.extend(res.get("damages_detected", []))
                damage_assessments.append(res)
            except Exception as e:
                logger.error("YOLOv8 error: %s", e)

    worst_yolo = _worst_decision(damage_assessments)
    highest_severity = max(all_damages, key=lambda d: _SEV_RANK.get(d.get("severity", "none"), 0)).get("severity", "none") if all_damages else "none"
    total_cost = sum(d.get("estimated_cost", 0) for d in all_damages)

    # Gate 1b: Docling RC Extraction
    extracted_rc = rc_extractor.extract_rc_fields(doc_bytes, filename=document.filename or "document.pdf")

    # Gate 1c: Multimodal VLM Verification
    doc_images = [doc_bytes] if (document.content_type and document.content_type.startswith("image/")) else []
    vlm_result = vlm_verifier.verify(car_image_bytes=car_bytes_list, doc_image_bytes=doc_images, extracted_rc=extracted_rc)

    telemetry = vlm_result.get("telemetry", {})
    legal = vlm_result.get("legal_identity", {})

    # Gate 2: Insert Draft Listing
    listing_row = {
        "seller_id":           user["id"],
        "make":                extracted_rc.get("make") or "Unknown",
        "model":               extracted_rc.get("model") or "Unknown",
        "year":                extracted_rc.get("year") or 2000,
        "variant":             extracted_rc.get("variant"),
        "fuel_type":           extracted_rc.get("fuel_type") or "petrol",
        "transmission":        "manual",
        "mileage_km":          telemetry.get("odometer_km") or 0,
        "owner_count":         extracted_rc.get("owner_serial") or 1,
        "city":                "",
        "price":               1.0,
        "status":              "draft",
        "verification_status": "unverified",
        "vlm_report":          vlm_result,
        "ocr_odometer_km":     telemetry.get("odometer_km"),
        "plate_number":        legal.get("plate_readout"),
    }

    listing_res = db.table("listings").insert(listing_row).execute()
    if not listing_res.data:
        raise HTTPException(500, "Failed to create draft listing")
    listing_id = listing_res.data[0]["id"]

    # Insert images
    inserted_images = db.table("listing_images").insert([
        {"listing_id": listing_id, "storage_path": p, "is_primary": i == 0, "order_index": i}
        for i, p in enumerate(image_paths)
    ]).execute().data or []

    # Insert document
    db.table("listing_documents").insert({
        "listing_id": listing_id, "document_type": "ownership_title",
        "document_name": document.filename, "storage_path": doc_storage_path, "verification_status": "pending",
    }).execute()

    # Insert assessments
    if damage_assessments and assessment.available() and inserted_images:
        asm_rows = [
            {
                "listing_id": listing_id, "image_id": inserted_images[i]["id"] if i < len(inserted_images) else None,
                "assessment_id_ext": str(uuid.uuid4())[:12],
                **{k: asm[k] for k in ASSESSMENT_DB_FIELDS if k in asm},
            }
            for i, asm in enumerate(damage_assessments)
        ]
        db.table("assessments").insert(asm_rows).execute()

    return {
        "listing_id": listing_id,
        "extracted_specs": {
            "make":         extracted_rc.get("make"),
            "model":        extracted_rc.get("model"),
            "year":         extracted_rc.get("year"),
            "variant":      extracted_rc.get("variant"),
            "fuel_type":    extracted_rc.get("fuel_type"),
            "transmission": None,
            "owner_count":  extracted_rc.get("owner_serial"),
            "color":        vlm_result.get("same_vehicle", {}).get("detected_color"),
            "body_type":    None,
            "mileage_km":   telemetry.get("odometer_km"),
            "plate_number": legal.get("plate_readout"),
            "chassis_vin":  extracted_rc.get("chassis_vin"),
        },
        "damage_assessment": {
            "total_damages":         len(all_damages),
            "highest_severity":      highest_severity,
            "estimated_repair_cost": total_cost,
            "decision":              worst_yolo,
        },
        "verification_verdict": vlm_result.get("verdict"),
        "vlm_discrepancies":    vlm_result.get("discrepancies", []),
        "missing_fields":       ["price", "city", "transmission", "description"],
    }


# ---------------------------------------------------------------------------
# Listing Management (Update, Delete, Image/Doc Upload)
# ---------------------------------------------------------------------------

@router.patch("/{listing_id}", tags=["Listings"])
async def update_listing(listing_id: str, payload: dict, user: dict = Depends(get_current_user)):
    """Seller updates draft listing. Telemetry fields are immutable by seller."""
    db = _db()
    existing = db.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] != "draft" and user["role"] != "admin":
        raise HTTPException(400, "Only draft listings can be edited")

    for k in ("status", "seller_id", "verification_status", "vlm_report", "ocr_odometer_km", "plate_number"):
        payload.pop(k, None)

    res = db.table("listings").update(payload).eq("id", listing_id).execute()
    return res.data[0] if res.data else {"status": "updated"}


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Listings"])
async def delete_listing(listing_id: str, user: dict = Depends(get_current_user)):
    """Delete draft listing (seller) or any listing (admin)."""
    db = _db()
    existing = db.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    is_owner, is_admin = existing.data["seller_id"] == user["id"], user["role"] == "admin"
    if not is_owner and not is_admin:
        raise HTTPException(403, "Not authorized")
    if is_owner and not is_admin and existing.data["status"] != "draft":
        raise HTTPException(400, "Only draft listings can be deleted by seller")
    db.table("listings").delete().eq("id", listing_id).execute()


@router.post("/{listing_id}/images", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def upload_listing_image(listing_id: str, payload: ImageUpload, user: dict = Depends(require_role(["seller", "admin"]))):
    """Upload and optionally assess an individual image."""
    db = _db()
    existing = db.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] != "draft" and user["role"] != "admin":
        raise HTTPException(400, "Can only upload images to draft listings")

    img_res = db.table("listing_images").insert({
        "listing_id": listing_id, "storage_path": payload.storage_path,
        "is_primary": payload.is_primary, "order_index": payload.order_index,
    }).execute()
    if not img_res.data:
        raise HTTPException(500, "Failed to register image")
    image_record = img_res.data[0]

    assessment_record = damage_stats = expert_commentary = None
    if payload.auto_assess and assessment.available():
        try:
            image_bytes = await fetch_image_bytes(payload.storage_path)
            if image_bytes:
                result = assessment.run_assessment(image_bytes)
                damage_stats = result["damage_stats"]
                expert_commentary = result["expert_commentary"]
                asm_res = db.table("assessments").insert({
                    "listing_id": listing_id, "image_id": image_record["id"],
                    "assessment_id_ext": str(uuid.uuid4())[:12],
                    **{k: result[k] for k in ASSESSMENT_DB_FIELDS},
                }).execute()
                if asm_res.data:
                    assessment_record = asm_res.data[0]
        except Exception as e:
            logger.error("Auto-assessment error: %s", e)

    return {"image": image_record, "assessment": assessment_record, "damage_stats": damage_stats, "expert_commentary": expert_commentary}


@router.post("/{listing_id}/documents", status_code=status.HTTP_201_CREATED, tags=["Listings"])
async def upload_listing_document(listing_id: str, payload: DocumentUpload, user: dict = Depends(require_role(["seller", "admin"]))):
    """Upload an ownership/inspection document."""
    db = _db()
    existing = db.table("listings").select("seller_id, status").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    if existing.data["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if existing.data["status"] != "draft" and user["role"] != "admin":
        raise HTTPException(400, "Can only upload documents to draft listings")

    res = db.table("listing_documents").insert({
        "listing_id": listing_id, "document_type": payload.document_type,
        "document_name": payload.document_name, "storage_path": payload.storage_path, "verification_status": "pending",
    }).execute()
    if not res.data:
        raise HTTPException(500, "Failed to record document")
    return res.data[0]


# ---------------------------------------------------------------------------
# Submission Guard & Lifecycle
# ---------------------------------------------------------------------------

@router.post("/{listing_id}/submit", tags=["Listings"])
async def submit_listing(listing_id: str, user: dict = Depends(require_role(["seller", "admin"]))):
    """Move listing from draft -> pending/active/escalated with anti-fraud guards."""
    db = _db()
    existing = db.table("listings").select("seller_id, status, mileage_km, ocr_odometer_km, vlm_report").eq("id", listing_id).single().execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    listing = existing.data
    if listing["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if listing["status"] != "draft":
        raise HTTPException(400, f"Listing is already '{listing['status']}'")

    # Step 1: Draft -> Pending (Database trigger validates minimum 3 photos + title doc)
    try:
        db.table("listings").update({"status": "pending"}).eq("id", listing_id).execute()
    except Exception as e:
        raise HTTPException(400, str(e))

    final_status = "pending"
    updates: dict = {}

    # Step 2: Odometer Delta Guard (<= 1500 km)
    ocr_km = listing.get("ocr_odometer_km")
    if ocr_km is not None and abs(listing.get("mileage_km", 0) - ocr_km) > 1500:
        updates["verification_status"] = "flagged_discrepancy"

    # Step 3: Physical Plate vs RC Mismatch Guard
    vlm = listing.get("vlm_report") or {}
    if vlm.get("legal_identity", {}).get("matches_document") is False:
        final_status = "escalated"

    # Step 4: YOLOv8 Assessment Decision Integration
    asm_res = db.table("assessments").select("decision").eq("listing_id", listing_id).execute()
    worst = _worst_decision(asm_res.data or [])
    yolo_status = {"ESCALATE": "escalated", "HUMAN_REVIEW": "pending"}.get(worst, "active")

    status_rank = {"escalated": 3, "pending": 2, "active": 1}
    if status_rank.get(yolo_status, 0) > status_rank.get(final_status, 0):
        final_status = yolo_status

    updates["status"] = final_status
    if "verification_status" not in updates and final_status == "active":
        updates["verification_status"] = "verified_clean"

    res = db.table("listings").update(updates).eq("id", listing_id).execute()
    return {"listing_id": listing_id, "final_status": final_status, **(res.data[0] if res.data else {})}


@router.post("/{listing_id}/sell", tags=["Listings"])
async def mark_listing_sold(listing_id: str, payload: Optional[SaleRecord] = None, user: dict = Depends(require_role(["seller", "admin"]))):
    """Mark active listing as sold."""
    db = _db()
    existing = db.table("listings").select("seller_id, status").eq("id", listing_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(404, "Listing not found")
    row = existing.data[0]
    if row["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Not your listing")
    if row["status"] != "active":
        raise HTTPException(400, f"Only active listings can be marked sold (current: '{row['status']}')")

    updates = {"status": "sold", "sold_at": utc_now_iso(), "buyer_id": payload.buyer_id if payload else None}
    res = db.table("listings").update(updates).eq("id", listing_id).execute()
    return res.data[0] if res.data else {"listing_id": listing_id, **updates}


@router.get("/{listing_id}/assessment", tags=["Listings"])
async def get_listing_assessment(listing_id: str):
    """Latest damage assessment report for a listing."""
    res = _db().table("assessments").select("*").eq("listing_id", listing_id).order("created_at", desc=True).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "No assessment found for this listing")
    return res.data[0]


# ---------------------------------------------------------------------------
# Vehicle Catalog Endpoints (Autofill & Cascading Dropdowns)
# ---------------------------------------------------------------------------

@router.get("/catalog/makes", tags=["Catalog"])
async def catalog_makes():
    """Distinct car makes."""
    res = _db().table("vehicle_catalog").select("make").execute()
    return [{"make": m} for m in sorted({row["make"] for row in (res.data or [])})]


@router.get("/catalog/models", tags=["Catalog"])
async def catalog_models(make: str = Query(..., description="Filter by make")):
    """Distinct models for a make."""
    res = _db().table("vehicle_catalog").select("model").eq("make", make.strip().title()).execute()
    return [{"model": m} for m in sorted({row["model"] for row in (res.data or [])})]


@router.get("/catalog/variants", tags=["Catalog"])
async def catalog_variants(make: str = Query(...), model: str = Query(...)):
    """All variants and specs for a make + model."""
    res = _db().table("vehicle_catalog").select(
        "variant, year_start, year_end, body_type, fuel_type, transmission, features, colors"
    ).eq("make", make.strip().title()).eq("model", model.strip().title()).order("year_start", desc=True).execute()
    return res.data or []

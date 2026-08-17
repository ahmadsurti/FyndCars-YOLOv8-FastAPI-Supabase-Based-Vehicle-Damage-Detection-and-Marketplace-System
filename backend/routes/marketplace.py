"""
fynd(cars) — Marketplace Extensions API
Routes for messages, saved_listings, listing_views, seller_reviews, search_alerts, user_subscriptions.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from db import supabase
from middleware.auth import get_current_user, get_optional_user

logger = logging.getLogger("fynd(cars)_api")


def _db():
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    return supabase

messages_router = APIRouter(prefix="/messages", tags=["Messages"])
saved_router = APIRouter(prefix="/saved-listings", tags=["Saved Listings"])
listing_extras_router = APIRouter(prefix="/listings")
sellers_router = APIRouter(prefix="/sellers", tags=["Seller Reviews"])
alerts_router = APIRouter(prefix="/search-alerts", tags=["Search Alerts"])
subs_router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

PLAN_TYPES = ("seller_unlimited_listings", "pro_buyer_alerts", "ai_inspection_bundle")


class MessageCreate(BaseModel):
    listing_id: str
    body: str = Field(min_length=1, max_length=4000)
    receiver_id: Optional[str] = Field(None, description="Defaults to the listing's seller")


class SavedListingCreate(BaseModel):
    listing_id: str


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class SearchAlertBase(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    max_price: Optional[float] = Field(None, gt=0)
    min_year: Optional[int] = Field(None, ge=1900, le=2100)
    city: Optional[str] = None


class SearchAlertUpdate(SearchAlertBase):
    is_active: Optional[bool] = None


class SubscriptionCreate(BaseModel):
    plan_type: str
    amount_paid: float = Field(gt=0)
    currency: str = "INR"
    valid_until: Optional[str] = Field(None, description="ISO datetime")


class SubscriptionConfirm(BaseModel):
    razorpay_order_id: str = Field(min_length=4)
    razorpay_payment_id: str = Field(min_length=4)


def _get_listing(listing_id: str) -> Optional[dict]:
    res = _db().table("listings").select("id, seller_id, status, buyer_id").eq("id", listing_id).limit(1).execute()
    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@messages_router.post("", status_code=status.HTTP_201_CREATED)
async def send_message(payload: MessageCreate, user: dict = Depends(get_current_user)):
    """Send a message about a listing."""
    listing = _get_listing(payload.listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    receiver_id = payload.receiver_id or listing["seller_id"]
    if receiver_id == user["id"]:
        raise HTTPException(400, "Cannot send a message to yourself")

    res = _db().table("messages").insert({
        "listing_id": payload.listing_id, "sender_id": user["id"],
        "receiver_id": receiver_id, "body": payload.body,
    }).execute()
    if not res.data:
        raise HTTPException(500, "Failed to send message")
    return res.data[0]


@messages_router.get("")
async def list_messages(
    listing_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """Conversation history for logged-in user."""
    db = _db()
    sent = db.table("messages").select("*").eq("sender_id", user["id"]).execute()
    received = db.table("messages").select("*").eq("receiver_id", user["id"]).execute()
    rows = {m["id"]: m for m in (sent.data or []) + (received.data or [])}.values()
    if listing_id:
        rows = [m for m in rows if m.get("listing_id") == listing_id]
    if unread_only:
        rows = [m for m in rows if m.get("receiver_id") == user["id"] and not m.get("read")]
    sorted_rows = sorted(rows, key=lambda m: m.get("created_at") or "")
    return sorted_rows[offset:offset + limit]


@messages_router.get("/unread-count")
async def unread_message_count(user: dict = Depends(get_current_user)):
    """Unread message count badge."""
    res = _db().table("messages").select("id").eq("receiver_id", user["id"]).eq("read", False).execute()
    return {"unread_count": len(res.data or [])}


@messages_router.patch("/{message_id}/read")
async def mark_message_read(message_id: str, user: dict = Depends(get_current_user)):
    """Mark received message as read."""
    db = _db()
    res = db.table("messages").select("*").eq("id", message_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Message not found")
    if res.data[0]["receiver_id"] != user["id"]:
        raise HTTPException(403, "Only the receiver can mark a message as read")
    updated = db.table("messages").update({"read": True}).eq("id", message_id).execute()
    return updated.data[0] if updated.data else {"id": message_id, "read": True}


# ---------------------------------------------------------------------------
# Saved Listings (Bookmarks)
# ---------------------------------------------------------------------------

@saved_router.get("")
async def my_saved_listings(user: dict = Depends(get_current_user)):
    """Bookmarked listings with details."""
    db = _db()
    saved = db.table("saved_listings").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute()
    rows = saved.data or []
    if not rows:
        return []
    listings = db.table("listings").select("*").in_("id", [r["listing_id"] for r in rows]).execute()
    by_id = {item["id"]: item for item in (listings.data or [])}
    return [{**r, "listing": by_id.get(r["listing_id"])} for r in rows]


@saved_router.post("", status_code=status.HTTP_201_CREATED)
async def save_listing(payload: SavedListingCreate, user: dict = Depends(get_current_user)):
    """Bookmark a listing (idempotent)."""
    db = _db()
    if not _get_listing(payload.listing_id):
        raise HTTPException(404, "Listing not found")
    existing = db.table("saved_listings").select("*").eq("user_id", user["id"]).eq("listing_id", payload.listing_id).limit(1).execute()
    if existing.data:
        return JSONResponse(status_code=200, content=existing.data[0])
    res = db.table("saved_listings").insert({"user_id": user["id"], "listing_id": payload.listing_id}).execute()
    if not res.data:
        raise HTTPException(500, "Failed to save listing")
    return res.data[0]


@saved_router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_listing(listing_id: str, user: dict = Depends(get_current_user)):
    """Remove bookmark."""
    _db().table("saved_listings").delete().eq("user_id", user["id"]).eq("listing_id", listing_id).execute()


# ---------------------------------------------------------------------------
# Listing Views & Analytics
# ---------------------------------------------------------------------------

def _hash_ip(request: Request) -> str:
    host = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    return hashlib.sha256(host.encode()).hexdigest()[:16]


@listing_extras_router.post("/{listing_id}/view", status_code=status.HTTP_201_CREATED, tags=["Listing Views"])
async def log_listing_view(listing_id: str, request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Record view impression."""
    if not _get_listing(listing_id):
        raise HTTPException(404, "Listing not found")
    _db().table("listing_views").insert({
        "listing_id": listing_id, "viewer_id": user["id"] if user else None, "ip_hash": _hash_ip(request),
    }).execute()
    return {"logged": True}


@listing_extras_router.get("/{listing_id}/views", tags=["Listing Views"])
async def listing_view_stats(listing_id: str, user: dict = Depends(get_current_user)):
    """Analytics for listing owner or admin."""
    listing = _get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Only the listing owner or an admin can view analytics")
    rows = _db().table("listing_views").select("*").eq("listing_id", listing_id).order("viewed_at", desc=True).execute().data or []
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    unique = {(v.get("viewer_id") or v.get("ip_hash")) for v in rows}
    return {
        "listing_id": listing_id,
        "total_views": len(rows),
        "unique_viewers": len(unique),
        "views_last_7_days": sum(1 for v in rows if (v.get("viewed_at") or "") >= week_ago),
        "recent": rows[:10],
    }


# ---------------------------------------------------------------------------
# Seller Reviews
# ---------------------------------------------------------------------------

@listing_extras_router.post("/{listing_id}/reviews", status_code=status.HTTP_201_CREATED, tags=["Seller Reviews"])
async def review_sold_listing(listing_id: str, payload: ReviewCreate, user: dict = Depends(get_current_user)):
    """Submit post-sale verified review."""
    db = _db()
    listing = _get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["status"] != "sold":
        raise HTTPException(400, "Only sold listings can be reviewed")
    if listing["seller_id"] == user["id"]:
        raise HTTPException(403, "Sellers cannot review themselves")
    buyer_of_record = listing.get("buyer_id")
    if buyer_of_record and buyer_of_record != user["id"]:
        raise HTTPException(403, "Only the buyer recorded on this sale can review it")

    dup = db.table("seller_reviews").select("id").eq("listing_id", listing_id).eq("buyer_id", user["id"]).limit(1).execute()
    if dup.data:
        raise HTTPException(409, "You have already reviewed this deal")

    res = db.table("seller_reviews").insert({
        "seller_id": listing["seller_id"], "buyer_id": user["id"],
        "listing_id": listing_id, "rating": payload.rating, "comment": payload.comment,
    }).execute()
    if not res.data:
        raise HTTPException(500, "Failed to save review")
    return res.data[0]


@sellers_router.get("/{seller_id}/reviews")
async def get_seller_reviews(seller_id: str, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Public seller trust profile."""
    db = _db()
    total = db.table("seller_reviews").select("id", count="exact").eq("seller_id", seller_id).execute()
    reviews = db.table("seller_reviews").select("*").eq("seller_id", seller_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    rows = reviews.data or []
    ratings = [r["rating"] for r in rows]
    return {
        "seller_id": seller_id,
        "total_reviews": total.count if total.count is not None else len(rows),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "reviews": rows,
    }


# ---------------------------------------------------------------------------
# Search Alerts
# ---------------------------------------------------------------------------

def _alert_matches_query(alert: dict):
    q = _db().table("listings").select("*").eq("status", "active").order("created_at", desc=True)
    if alert.get("make"):
        q = q.ilike("make", alert["make"])
    if alert.get("model"):
        q = q.ilike("model", alert["model"])
    if alert.get("city"):
        q = q.ilike("city", alert["city"])
    if alert.get("max_price") is not None:
        q = q.lte("price", alert["max_price"])
    if alert.get("min_year") is not None:
        q = q.gte("year", alert["min_year"])
    return q


def _get_own_alert(alert_id: str, user: dict) -> dict:
    res = _db().table("search_alerts").select("*").eq("id", alert_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Alert not found")
    if res.data[0]["user_id"] != user["id"]:
        raise HTTPException(403, "Not your alert")
    return res.data[0]


@alerts_router.get("")
async def my_search_alerts(user: dict = Depends(get_current_user)):
    """Active saved searches."""
    return _db().table("search_alerts").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute().data


@alerts_router.post("", status_code=status.HTTP_201_CREATED)
async def create_search_alert(payload: SearchAlertBase, user: dict = Depends(get_current_user)):
    """Create a search alert."""
    criteria = payload.model_dump()
    if not any(v is not None for v in criteria.values()):
        raise HTTPException(400, "At least one search criterion is required")
    res = _db().table("search_alerts").insert({"user_id": user["id"], "is_active": True, **criteria}).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create alert")
    return res.data[0]


@alerts_router.patch("/{alert_id}")
async def update_search_alert(alert_id: str, payload: SearchAlertUpdate, user: dict = Depends(get_current_user)):
    """Update or toggle search alert."""
    _get_own_alert(alert_id, user)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")
    res = _db().table("search_alerts").update(updates).eq("id", alert_id).execute()
    return res.data[0] if res.data else {"id": alert_id, **updates}


@alerts_router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_alert(alert_id: str, user: dict = Depends(get_current_user)):
    """Delete search alert."""
    _get_own_alert(alert_id, user)
    _db().table("search_alerts").delete().eq("id", alert_id).execute()


@alerts_router.get("/{alert_id}/matches")
async def search_alert_matches(alert_id: str, limit: int = Query(20, ge=1, le=100), user: dict = Depends(get_current_user)):
    """Evaluate alert against live inventory."""
    alert = _get_own_alert(alert_id, user)
    return {"alert_id": alert_id, "matches": _alert_matches_query(alert).limit(limit).execute().data or []}


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

@subs_router.get("")
async def my_subscriptions(user: dict = Depends(get_current_user)):
    """User subscription status."""
    return _db().table("user_subscriptions").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute().data


@subs_router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(payload: SubscriptionCreate, user: dict = Depends(get_current_user)):
    """Initiate subscription checkout intent."""
    if payload.plan_type not in PLAN_TYPES:
        raise HTTPException(400, f"Invalid plan_type. Must be one of: {PLAN_TYPES}")
    valid_until = payload.valid_until or (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    res = _db().table("user_subscriptions").insert({
        "user_id": user["id"], "plan_type": payload.plan_type, "status": "pending",
        "amount_paid": payload.amount_paid, "currency": payload.currency, "valid_until": valid_until,
    }).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create subscription")
    return res.data[0]


@subs_router.patch("/{subscription_id}/confirm")
async def confirm_subscription(subscription_id: str, payload: SubscriptionConfirm, user: dict = Depends(get_current_user)):
    """Activate subscription upon payment confirmation."""
    db = _db()
    res = db.table("user_subscriptions").select("*").eq("id", subscription_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Subscription not found")
    sub = res.data[0]
    if sub["user_id"] != user["id"]:
        raise HTTPException(403, "Not your subscription")
    if sub["status"] != "pending":
        raise HTTPException(400, f"Subscription is already '{sub['status']}'")
    updates = {"status": "active", "razorpay_order_id": payload.razorpay_order_id, "razorpay_payment_id": payload.razorpay_payment_id}
    updated = db.table("user_subscriptions").update(updates).eq("id", subscription_id).execute()
    return updated.data[0] if updated.data else {"id": subscription_id, **updates}


@subs_router.delete("/{subscription_id}")
async def cancel_subscription(subscription_id: str, user: dict = Depends(get_current_user)):
    """Cancel subscription."""
    db = _db()
    res = db.table("user_subscriptions").select("*").eq("id", subscription_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Subscription not found")
    sub = res.data[0]
    if sub["user_id"] != user["id"]:
        raise HTTPException(403, "Not your subscription")
    if sub["status"] == "canceled":
        return sub
    updated = db.table("user_subscriptions").update({"status": "canceled"}).eq("id", subscription_id).execute()
    return updated.data[0] if updated.data else {**sub, "status": "canceled"}

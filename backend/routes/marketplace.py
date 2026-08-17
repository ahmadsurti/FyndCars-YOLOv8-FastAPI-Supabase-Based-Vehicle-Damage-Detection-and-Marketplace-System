"""
fynd(cars) — Marketplace Extensions API
Backend routes for the extension tables built in migrations 004/005:
messages, saved_listings, listing_views, seller_reviews, search_alerts,
user_subscriptions.

Authorization here mirrors the DB RLS policies rule-for-rule: this client
runs with the service_role key (RLS is bypassed), so every endpoint
re-checks ownership and state transitions itself.
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

messages_router = APIRouter(prefix="/messages", tags=["Messages"])
saved_router = APIRouter(prefix="/saved-listings", tags=["Saved Listings"])
listing_extras_router = APIRouter(prefix="/listings")  # view logging + reviews, per-route tags
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
    valid_until: Optional[str] = Field(None, description="ISO datetime; defaults to now + 30 days")


class SubscriptionConfirm(BaseModel):
    razorpay_order_id: str = Field(min_length=4)
    razorpay_payment_id: str = Field(min_length=4)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_listing(listing_id: str) -> Optional[dict]:
    res = supabase.table("listings").select("id, seller_id, status, buyer_id").eq("id", listing_id).limit(1).execute()
    return res.data[0] if res.data else None


# ===========================================================================
# Messages (buyer ↔ seller chat about a listing)
# ===========================================================================

@messages_router.post("", status_code=status.HTTP_201_CREATED)
async def send_message(payload: MessageCreate, user: dict = Depends(get_current_user)):
    """Send a message about a listing. Receiver defaults to the listing's seller."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    listing = _get_listing(payload.listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    receiver_id = payload.receiver_id or listing["seller_id"]
    if receiver_id == user["id"]:
        raise HTTPException(400, "Cannot send a message to yourself")
    row = {
        "listing_id": payload.listing_id,
        "sender_id": user["id"],
        "receiver_id": receiver_id,
        "body": payload.body,
    }
    res = supabase.table("messages").insert(row).execute()
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
    """My side of every conversation: messages I sent or received, oldest first."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    sent = supabase.table("messages").select("*").eq("sender_id", user["id"]).execute()
    received = supabase.table("messages").select("*").eq("receiver_id", user["id"]).execute()
    rows = {m["id"]: m for m in (sent.data or []) + (received.data or [])}.values()
    if listing_id:
        rows = [m for m in rows if m.get("listing_id") == listing_id]
    if unread_only:
        rows = [m for m in rows if m.get("receiver_id") == user["id"] and not m.get("read")]
    rows = sorted(rows, key=lambda m: m.get("created_at") or "")
    return rows[offset:offset + limit]


@messages_router.get("/unread-count")
async def unread_message_count(user: dict = Depends(get_current_user)):
    """Count of messages addressed to me that I haven't read (navbar badge)."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("messages")
        .select("id")
        .eq("receiver_id", user["id"])
        .eq("read", False)
        .execute()
    )
    return {"unread_count": len(res.data or [])}


@messages_router.patch("/{message_id}/read")
async def mark_message_read(message_id: str, user: dict = Depends(get_current_user)):
    """Mark a message as read. Only the receiver may do this."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = supabase.table("messages").select("*").eq("id", message_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Message not found")
    if res.data[0]["receiver_id"] != user["id"]:
        raise HTTPException(403, "Only the receiver can mark a message as read")
    updated = supabase.table("messages").update({"read": True}).eq("id", message_id).execute()
    return updated.data[0] if updated.data else {"id": message_id, "read": True}


# ===========================================================================
# Saved listings (favorites / bookmarks)
# ===========================================================================

@saved_router.get("")
async def my_saved_listings(user: dict = Depends(get_current_user)):
    """My bookmarked listings, newest save first, with the listing attached."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    saved = (
        supabase.table("saved_listings")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    rows = saved.data or []
    if not rows:
        return []
    listing_ids = [r["listing_id"] for r in rows]
    listings = supabase.table("listings").select("*").in_("id", listing_ids).execute()
    by_id = {l["id"]: l for l in (listings.data or [])}
    return [{**r, "listing": by_id.get(r["listing_id"])} for r in rows]


@saved_router.post("", status_code=status.HTTP_201_CREATED)
async def save_listing(payload: SavedListingCreate, user: dict = Depends(get_current_user)):
    """Bookmark a listing. Idempotent: re-saving returns the existing row with 200."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    if not _get_listing(payload.listing_id):
        raise HTTPException(404, "Listing not found")
    existing = (
        supabase.table("saved_listings")
        .select("*")
        .eq("user_id", user["id"])
        .eq("listing_id", payload.listing_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return JSONResponse(status_code=200, content=existing.data[0])
    res = supabase.table("saved_listings").insert({"user_id": user["id"], "listing_id": payload.listing_id}).execute()
    if not res.data:
        raise HTTPException(500, "Failed to save listing")
    return res.data[0]


@saved_router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_listing(listing_id: str, user: dict = Depends(get_current_user)):
    """Remove a bookmark. Idempotent: deleting an unsaved listing is a no-op."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    supabase.table("saved_listings").delete().eq("user_id", user["id"]).eq("listing_id", listing_id).execute()


# ===========================================================================
# Listing views (impressions / seller analytics)
# ===========================================================================

def _hash_ip(request: Request) -> str:
    host = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not host and request.client:
        host = request.client.host
    return hashlib.sha256(host.encode()).hexdigest()[:16]


@listing_extras_router.post("/{listing_id}/view", status_code=status.HTTP_201_CREATED, tags=["Listing Views"])
async def log_listing_view(listing_id: str, request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Log one impression. Public — viewer identity recorded only if a token is present."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    if not _get_listing(listing_id):
        raise HTTPException(404, "Listing not found")
    row = {
        "listing_id": listing_id,
        "viewer_id": user["id"] if user else None,
        "ip_hash": _hash_ip(request),
    }
    supabase.table("listing_views").insert(row).execute()
    return {"logged": True}


@listing_extras_router.get("/{listing_id}/views", tags=["Listing Views"])
async def listing_view_stats(listing_id: str, user: dict = Depends(get_current_user)):
    """View analytics for one listing. Seller (owner) or admin only."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    listing = _get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Only the listing owner or an admin can view analytics")
    views = supabase.table("listing_views").select("*").eq("listing_id", listing_id).order("viewed_at", desc=True).execute()
    rows = views.data or []
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    unique = {(v.get("viewer_id") or v.get("ip_hash")) for v in rows}
    return {
        "listing_id": listing_id,
        "total_views": len(rows),
        "unique_viewers": len(unique),
        "views_last_7_days": sum(1 for v in rows if (v.get("viewed_at") or "") >= week_ago),
        "recent": rows[:10],
    }


# ===========================================================================
# Seller reviews (verified post-sale feedback)
# ===========================================================================

@listing_extras_router.post("/{listing_id}/reviews", status_code=status.HTTP_201_CREATED, tags=["Seller Reviews"])
async def review_sold_listing(listing_id: str, payload: ReviewCreate, user: dict = Depends(get_current_user)):
    """
    Leave a 1–5 star review for the seller of a SOLD listing.
    Mirrors the DB rules: no self-review, listing must be 'sold', one review
    per buyer per deal. If the sale recorded a buyer_id, only that buyer may review.
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
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
    dup = (
        supabase.table("seller_reviews")
        .select("id")
        .eq("listing_id", listing_id)
        .eq("buyer_id", user["id"])
        .limit(1)
        .execute()
    )
    if dup.data:
        raise HTTPException(409, "You have already reviewed this deal")
    row = {
        "seller_id": listing["seller_id"],
        "buyer_id": user["id"],
        "listing_id": listing_id,
        "rating": payload.rating,
        "comment": payload.comment,
    }
    res = supabase.table("seller_reviews").insert(row).execute()
    if not res.data:
        raise HTTPException(500, "Failed to save review")
    return res.data[0]


@sellers_router.get("/{seller_id}/reviews")
async def get_seller_reviews(
    seller_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Public trust profile: a seller's reviews with the aggregate rating."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    total = supabase.table("seller_reviews").select("id", count="exact").eq("seller_id", seller_id).execute()
    reviews = (
        supabase.table("seller_reviews")
        .select("*")
        .eq("seller_id", seller_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    rows = reviews.data or []
    ratings = [r["rating"] for r in rows]
    return {
        "seller_id": seller_id,
        "total_reviews": total.count if total.count is not None else len(rows),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "reviews": rows,
    }


# ===========================================================================
# Search alerts (pro-buyer saved searches)
# ===========================================================================

def _alert_matches_query(alert: dict):
    """Build a listings query matching an alert's criteria (active listings only)."""
    q = supabase.table("listings").select("*").eq("status", "active").order("created_at", desc=True)
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


@alerts_router.get("")
async def my_search_alerts(user: dict = Depends(get_current_user)):
    """My saved searches, newest first."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("search_alerts")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@alerts_router.post("", status_code=status.HTTP_201_CREATED)
async def create_search_alert(payload: SearchAlertBase, user: dict = Depends(get_current_user)):
    """Save a search ('Toyota under ₹10L in Mumbai'). At least one criterion required."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    criteria = payload.model_dump()
    if not any(v is not None for v in criteria.values()):
        raise HTTPException(400, "At least one search criterion is required")
    res = supabase.table("search_alerts").insert({"user_id": user["id"], "is_active": True, **criteria}).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create alert")
    return res.data[0]


def _get_own_alert(alert_id: str, user: dict) -> dict:
    res = supabase.table("search_alerts").select("*").eq("id", alert_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Alert not found")
    if res.data[0]["user_id"] != user["id"]:
        raise HTTPException(403, "Not your alert")
    return res.data[0]


@alerts_router.patch("/{alert_id}")
async def update_search_alert(alert_id: str, payload: SearchAlertUpdate, user: dict = Depends(get_current_user)):
    """Edit criteria or pause/resume an alert (is_active)."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    _get_own_alert(alert_id, user)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")
    res = supabase.table("search_alerts").update(updates).eq("id", alert_id).execute()
    return res.data[0] if res.data else {"id": alert_id, **updates}


@alerts_router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_alert(alert_id: str, user: dict = Depends(get_current_user)):
    """Delete one of my alerts."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    _get_own_alert(alert_id, user)
    supabase.table("search_alerts").delete().eq("id", alert_id).execute()


@alerts_router.get("/{alert_id}/matches")
async def search_alert_matches(alert_id: str, limit: int = Query(20, ge=1, le=100), user: dict = Depends(get_current_user)):
    """Run an alert against the current active inventory (the frontend 'notifications' feed)."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    alert = _get_own_alert(alert_id, user)
    res = _alert_matches_query(alert).limit(limit).execute()
    return {"alert_id": alert_id, "matches": res.data or []}


# ===========================================================================
# User subscriptions (platform fees — Razorpay)
# ===========================================================================

@subs_router.get("")
async def my_subscriptions(user: dict = Depends(get_current_user)):
    """My subscription history, newest first."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = (
        supabase.table("user_subscriptions")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@subs_router.post("", status_code=status.HTTP_201_CREATED)
async def create_subscription(payload: SubscriptionCreate, user: dict = Depends(get_current_user)):
    """Create a subscription order (status=pending) — the Razorpay checkout intent."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    if payload.plan_type not in PLAN_TYPES:
        raise HTTPException(400, f"Invalid plan_type. Must be one of: {PLAN_TYPES}")
    valid_until = payload.valid_until or (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    row = {
        "user_id": user["id"],
        "plan_type": payload.plan_type,
        "status": "pending",
        "amount_paid": payload.amount_paid,
        "currency": payload.currency,
        "valid_until": valid_until,
    }
    res = supabase.table("user_subscriptions").insert(row).execute()
    if not res.data:
        raise HTTPException(500, "Failed to create subscription")
    return res.data[0]


@subs_router.patch("/{subscription_id}/confirm")
async def confirm_subscription(subscription_id: str, payload: SubscriptionConfirm, user: dict = Depends(get_current_user)):
    """
    Mark a pending subscription active after Razorpay payment succeeds.
    Dev/manual path — in production this arrives via a signed Razorpay webhook
    instead, so payment ids can't be forged.
    """
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = supabase.table("user_subscriptions").select("*").eq("id", subscription_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Subscription not found")
    sub = res.data[0]
    if sub["user_id"] != user["id"]:
        raise HTTPException(403, "Not your subscription")
    if sub["status"] != "pending":
        raise HTTPException(400, f"Subscription is already '{sub['status']}'")
    updates = {
        "status": "active",
        "razorpay_order_id": payload.razorpay_order_id,
        "razorpay_payment_id": payload.razorpay_payment_id,
    }
    updated = supabase.table("user_subscriptions").update(updates).eq("id", subscription_id).execute()
    return updated.data[0] if updated.data else {"id": subscription_id, **updates}


@subs_router.delete("/{subscription_id}")
async def cancel_subscription(subscription_id: str, user: dict = Depends(get_current_user)):
    """Cancel a subscription (row is kept for audit; status → canceled)."""
    if not supabase:
        raise HTTPException(503, "Database client unavailable")
    res = supabase.table("user_subscriptions").select("*").eq("id", subscription_id).limit(1).execute()
    if not res.data:
        raise HTTPException(404, "Subscription not found")
    sub = res.data[0]
    if sub["user_id"] != user["id"]:
        raise HTTPException(403, "Not your subscription")
    if sub["status"] == "canceled":
        return sub
    updated = supabase.table("user_subscriptions").update({"status": "canceled"}).eq("id", subscription_id).execute()
    return updated.data[0] if updated.data else {**sub, "status": "canceled"}

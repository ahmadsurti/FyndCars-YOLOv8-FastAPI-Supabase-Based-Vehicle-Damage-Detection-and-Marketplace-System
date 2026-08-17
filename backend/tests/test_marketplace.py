"""
fynd(cars) — Marketplace Extensions Tests
Covers: extended listing search, /listings/mine, mark-as-sold,
document verification, messages, saved listings, listing views,
seller reviews, search alerts, subscriptions.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api import app

client = TestClient(app)

NOW = datetime.now(timezone.utc).isoformat()

SELLER = {"Authorization": "Bearer demo-seller-token"}
BUYER = {"Authorization": "Bearer demo-buyer-token"}
ADMIN = {"Authorization": "Bearer demo-admin-token"}
SELLER_ID, BUYER_ID, ADMIN_ID = "demo-seller-id", "demo-buyer-id", "demo-admin-id"


def make_listing(lid, seller_id=SELLER_ID, status="active", **over):
    row = {
        "id": lid, "seller_id": seller_id, "make": "Toyota", "model": "Corolla",
        "year": 2020, "title": "2020 Toyota Corolla", "price": 900000.0,
        "currency": "INR", "fuel_type": "petrol", "transmission": "manual",
        "mileage_km": 40000, "owner_count": 1, "city": "Mumbai",
        "status": status, "features": [], "buyer_id": None, "sold_at": None,
        "created_at": NOW,
    }
    row.update(over)
    return row


def search_seed():
    """L1 Toyota 900k Mumbai, L2 Honda City 600k diesel Delhi, L3 Tata Nexon 1.2M Mumbai, L4 draft."""
    return [
        make_listing("L1", features=["Sunroof"], created_at="2026-08-01T00:00:00+00:00"),
        make_listing("L2", make="Honda", model="City", title="2018 Honda City", year=2018,
                     price=600000.0, fuel_type="diesel", transmission="automatic",
                     city="Delhi", mileage_km=80000, created_at="2026-08-02T00:00:00+00:00"),
        make_listing("L3", make="Tata", model="Nexon", title="2022 Tata Nexon", year=2022,
                     price=1200000.0, mileage_km=20000,
                     features=["Sunroof", "Cruise Control"], created_at="2026-08-03T00:00:00+00:00"),
        make_listing("L4", status="draft"),
    ]


def ids(rows):
    return sorted(r["id"] for r in rows)


# ===========================================================================
# Extended listing search (Gap 5)
# ===========================================================================

class TestListingSearch:
    def test_default_returns_active_only(self, install_db):
        install_db({"listings": search_seed()})
        assert ids(client.get("/listings").json()) == ["L1", "L2", "L3"]

    def test_price_range(self, install_db):
        install_db({"listings": search_seed()})
        r = client.get("/listings", params={"min_price": 700000, "max_price": 1000000})
        assert ids(r.json()) == ["L1"]

    def test_fuel_and_transmission(self, install_db):
        install_db({"listings": search_seed()})
        assert ids(client.get("/listings", params={"fuel_type": "diesel"}).json()) == ["L2"]
        assert ids(client.get("/listings", params={"transmission": "automatic"}).json()) == ["L2"]

    def test_year_range(self, install_db):
        install_db({"listings": search_seed()})
        r = client.get("/listings", params={"min_year": 2019, "max_year": 2023})
        assert ids(r.json()) == ["L1", "L3"]

    def test_max_mileage(self, install_db):
        install_db({"listings": search_seed()})
        assert ids(client.get("/listings", params={"max_mileage_km": 30000}).json()) == ["L3"]

    def test_city(self, install_db):
        install_db({"listings": search_seed()})
        assert ids(client.get("/listings", params={"city": "mumbai"}).json()) == ["L1", "L3"]

    def test_features_contains(self, install_db):
        install_db({"listings": search_seed()})
        r = client.get("/listings", params={"features": "Sunroof,Cruise Control"})
        assert ids(r.json()) == ["L3"]

    def test_free_text_title_search(self, install_db):
        install_db({"listings": search_seed()})
        assert ids(client.get("/listings", params={"q": "corolla"}).json()) == ["L1"]

    def test_sort_price_desc(self, install_db):
        install_db({"listings": search_seed()})
        rows = client.get("/listings", params={"sort": "price_desc"}).json()
        assert [r["id"] for r in rows] == ["L3", "L1", "L2"]  # 1.2M → 900k → 600k

    def test_invalid_sort_rejected(self, install_db):
        install_db({"listings": search_seed()})
        assert client.get("/listings", params={"sort": "fastest"}).status_code == 400


class TestMyListings:
    def test_seller_sees_all_own_statuses(self, install_db):
        install_db({"listings": search_seed() + [make_listing("L5", seller_id=BUYER_ID)]})
        r = client.get("/listings/mine", headers=SELLER)
        assert ids(r.json()) == ["L1", "L2", "L3", "L4"]

    def test_buyer_sees_own_only(self, install_db):
        install_db({"listings": search_seed()})
        assert client.get("/listings/mine", headers=BUYER).json() == []

    def test_requires_auth(self, install_db):
        install_db({"listings": search_seed()})
        assert client.get("/listings/mine").status_code == 401


# ===========================================================================
# Mark as sold (Gap 3)
# ===========================================================================

class TestMarkAsSold:
    def test_sell_records_sale(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        r = client.post("/listings/L1/sell", json={"buyer_id": BUYER_ID}, headers=SELLER)
        assert r.status_code == 200
        assert r.json()["status"] == "sold"
        assert r.json()["buyer_id"] == BUYER_ID
        assert r.json()["sold_at"] is not None

    def test_sell_without_buyer(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        r = client.post("/listings/L1/sell", headers=SELLER)
        assert r.status_code == 200 and r.json()["buyer_id"] is None

    def test_admin_can_sell_any(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/L1/sell", headers=ADMIN).status_code == 200

    def test_non_owner_forbidden(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/L1/sell", headers=BUYER).status_code == 403

    def test_only_active_can_be_sold(self, install_db):
        install_db({"listings": [make_listing("L1", status="draft"), make_listing("L5", status="sold")]})
        assert client.post("/listings/L1/sell", headers=SELLER).status_code == 400
        assert client.post("/listings/L5/sell", headers=SELLER).status_code == 400

    def test_unknown_listing(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/nope/sell", headers=SELLER).status_code == 404

    def test_requires_auth(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/L1/sell").status_code == 401


# ===========================================================================
# Document verification (Gap 4)
# ===========================================================================

def doc_seed():
    return [{
        "id": "d1", "listing_id": "L1", "document_type": "ownership_title",
        "document_name": "RC", "storage_path": "car-documents/u/rc.pdf",
        "verification_status": "pending", "rejection_reason": None,
    }]


class TestDocumentVerification:
    def test_admin_verifies(self, install_db):
        install_db({"listing_documents": doc_seed()})
        r = client.patch("/admin/documents/d1/verify", json={"verification_status": "verified"}, headers=ADMIN)
        assert r.status_code == 200
        assert r.json()["verification_status"] == "verified"
        assert r.json()["previous_status"] == "pending"

    def test_reject_requires_reason(self, install_db):
        install_db({"listing_documents": doc_seed()})
        r = client.patch("/admin/documents/d1/verify", json={"verification_status": "rejected"}, headers=ADMIN)
        assert r.status_code == 400

    def test_reject_with_reason(self, install_db):
        install_db({"listing_documents": doc_seed()})
        r = client.patch(
            "/admin/documents/d1/verify",
            json={"verification_status": "rejected", "rejection_reason": "RC number does not match chassis"},
            headers=ADMIN,
        )
        assert r.status_code == 200
        assert "chassis" in r.json()["rejection_reason"]

    def test_invalid_status_value(self, install_db):
        install_db({"listing_documents": doc_seed()})
        r = client.patch("/admin/documents/d1/verify", json={"verification_status": "maybe"}, headers=ADMIN)
        assert r.status_code == 400

    def test_non_admin_forbidden(self, install_db):
        install_db({"listing_documents": doc_seed()})
        assert client.patch("/admin/documents/d1/verify",
                            json={"verification_status": "verified"}, headers=BUYER).status_code == 403

    def test_unknown_document(self, install_db):
        install_db({"listing_documents": doc_seed()})
        assert client.patch("/admin/documents/nope/verify",
                            json={"verification_status": "verified"}, headers=ADMIN).status_code == 404


# ===========================================================================
# Messages
# ===========================================================================

def msg_seed():
    return [
        {"id": "m1", "listing_id": "L1", "sender_id": BUYER_ID, "receiver_id": SELLER_ID,
         "body": "Is the price negotiable?", "read": False, "created_at": "2026-08-01T10:00:00+00:00"},
        {"id": "m2", "listing_id": "L1", "sender_id": BUYER_ID, "receiver_id": SELLER_ID,
         "body": "Still available?", "read": False, "created_at": "2026-08-02T10:00:00+00:00"},
        {"id": "m3", "listing_id": "L2", "sender_id": SELLER_ID, "receiver_id": BUYER_ID,
         "body": "Yes, it is.", "read": True, "created_at": "2026-08-03T10:00:00+00:00"},
    ]


class TestMessages:
    def test_send_derives_receiver_from_listing(self, install_db):
        install_db({"listings": [make_listing("L1")], "messages": []})
        r = client.post("/messages", json={"listing_id": "L1", "body": "Hello!"}, headers=BUYER)
        assert r.status_code == 201
        assert r.json()["receiver_id"] == SELLER_ID
        assert r.json()["sender_id"] == BUYER_ID

    def test_cannot_message_yourself(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        r = client.post("/messages", json={"listing_id": "L1", "body": "hi",
                                           "receiver_id": BUYER_ID}, headers=BUYER)
        assert r.status_code == 400

    def test_unknown_listing(self, install_db):
        install_db({"listings": []})
        assert client.post("/messages", json={"listing_id": "L1", "body": "hi"},
                           headers=BUYER).status_code == 404

    def test_inbox_shows_only_my_messages(self, install_db):
        install_db({"messages": msg_seed() + [
            {"id": "m9", "listing_id": "L2", "sender_id": ADMIN_ID, "receiver_id": SELLER_ID,
             "body": "other convo", "read": True, "created_at": "2026-08-04T10:00:00+00:00"}]})
        buyer_view = ids(client.get("/messages", headers=BUYER).json())
        seller_view = ids(client.get("/messages", headers=SELLER).json())
        assert buyer_view == ["m1", "m2", "m3"]
        assert seller_view == ["m1", "m2", "m3", "m9"]

    def test_listing_filter(self, install_db):
        install_db({"messages": msg_seed()})
        assert ids(client.get("/messages", params={"listing_id": "L1"}, headers=BUYER).json()) == ["m1", "m2"]

    def test_unread_only_counts_receptions(self, install_db):
        install_db({"messages": msg_seed()})
        rows = client.get("/messages", params={"unread_only": True}, headers=SELLER).json()
        assert ids(rows) == ["m1", "m2"]

    def test_unread_count(self, install_db):
        install_db({"messages": msg_seed()})
        assert client.get("/messages/unread-count", headers=SELLER).json()["unread_count"] == 2
        assert client.get("/messages/unread-count", headers=BUYER).json()["unread_count"] == 0

    def test_mark_read_by_receiver_only(self, install_db):
        install_db({"messages": msg_seed()})
        assert client.patch("/messages/m1/read", headers=BUYER).status_code == 403  # sender can't
        r = client.patch("/messages/m1/read", headers=SELLER)
        assert r.status_code == 200 and r.json()["read"] is True
        assert client.get("/messages/unread-count", headers=SELLER).json()["unread_count"] == 1

    def test_requires_auth(self, install_db):
        install_db({"messages": msg_seed()})
        assert client.get("/messages").status_code == 401


# ===========================================================================
# Saved listings
# ===========================================================================

class TestSavedListings:
    def test_save_and_list(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        r = client.post("/saved-listings", json={"listing_id": "L1"}, headers=BUYER)
        assert r.status_code == 201
        saved = client.get("/saved-listings", headers=BUYER).json()
        assert len(saved) == 1
        assert saved[0]["listing"]["id"] == "L1" and saved[0]["listing"]["make"] == "Toyota"

    def test_resave_is_idempotent(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        first = client.post("/saved-listings", json={"listing_id": "L1"}, headers=BUYER)
        second = client.post("/saved-listings", json={"listing_id": "L1"}, headers=BUYER)
        assert first.status_code == 201 and second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert len(client.get("/saved-listings", headers=BUYER).json()) == 1

    def test_save_unknown_listing(self, install_db):
        install_db({"listings": []})
        assert client.post("/saved-listings", json={"listing_id": "L1"}, headers=BUYER).status_code == 404

    def test_unsave(self, install_db):
        install_db({"listings": [make_listing("L1")],
                    "saved_listings": [{"id": "s1", "user_id": BUYER_ID, "listing_id": "L1", "created_at": NOW}]})
        assert client.delete("/saved-listings/L1", headers=BUYER).status_code == 204
        assert client.get("/saved-listings", headers=BUYER).json() == []

    def test_saves_are_private(self, install_db):
        install_db({"listings": [make_listing("L1")],
                    "saved_listings": [{"id": "s1", "user_id": BUYER_ID, "listing_id": "L1", "created_at": NOW}]})
        assert client.get("/saved-listings", headers=SELLER).json() == []


# ===========================================================================
# Listing views
# ===========================================================================

class TestListingViews:
    def test_anon_can_log_view(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/L1/view").status_code == 201

    def test_stats_count_anon_and_authed_separately(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        client.post("/listings/L1/view")  # anon → ip_hash identity
        client.post("/listings/L1/view", headers=BUYER)  # identified viewer
        stats = client.get("/listings/L1/views", headers=SELLER).json()
        assert stats["total_views"] == 2
        assert stats["unique_viewers"] == 2
        assert stats["views_last_7_days"] == 2

    def test_stats_owner_only(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.get("/listings/L1/views", headers=BUYER).status_code == 403
        assert client.get("/listings/L1/views", headers=ADMIN).status_code == 200

    def test_unknown_listing(self, install_db):
        install_db({"listings": []})
        assert client.post("/listings/nope/view").status_code == 404


# ===========================================================================
# Seller reviews
# ===========================================================================

class TestSellerReviews:
    def test_buyer_reviews_sold_listing(self, install_db):
        install_db({"listings": [make_listing("L1", status="sold")]})
        r = client.post("/listings/L1/reviews", json={"rating": 5, "comment": "Smooth deal"}, headers=BUYER)
        assert r.status_code == 201
        assert r.json()["seller_id"] == SELLER_ID and r.json()["rating"] == 5

    def test_cannot_review_unsold_listing(self, install_db):
        install_db({"listings": [make_listing("L1")]})
        assert client.post("/listings/L1/reviews", json={"rating": 5}, headers=BUYER).status_code == 400

    def test_no_self_review(self, install_db):
        install_db({"listings": [make_listing("L1", status="sold")]})
        assert client.post("/listings/L1/reviews", json={"rating": 5}, headers=SELLER).status_code == 403

    def test_recorded_buyer_only(self, install_db):
        install_db({"listings": [make_listing("L1", status="sold", buyer_id=BUYER_ID)]})
        assert client.post("/listings/L1/reviews", json={"rating": 5}, headers=BUYER).status_code == 201
        assert client.post("/listings/L1/reviews", json={"rating": 5}, headers=ADMIN).status_code == 403

    def test_duplicate_review_rejected(self, install_db):
        install_db({"listings": [make_listing("L1", status="sold")]})
        assert client.post("/listings/L1/reviews", json={"rating": 4}, headers=BUYER).status_code == 201
        assert client.post("/listings/L1/reviews", json={"rating": 2}, headers=BUYER).status_code == 409

    def test_rating_bounds(self, install_db):
        install_db({"listings": [make_listing("L1", status="sold")]})
        assert client.post("/listings/L1/reviews", json={"rating": 6}, headers=BUYER).status_code == 422
        assert client.post("/listings/L1/reviews", json={"rating": 0}, headers=BUYER).status_code == 422

    def test_public_aggregate(self, install_db):
        install_db({"seller_reviews": [
            {"id": "r1", "seller_id": SELLER_ID, "buyer_id": BUYER_ID, "listing_id": "L1",
             "rating": 4, "comment": "Good", "created_at": NOW},
            {"id": "r2", "seller_id": SELLER_ID, "buyer_id": ADMIN_ID, "listing_id": "L2",
             "rating": 5, "comment": None, "created_at": NOW},
        ]})
        r = client.get(f"/sellers/{SELLER_ID}/reviews")
        assert r.status_code == 200
        assert r.json()["total_reviews"] == 2
        assert r.json()["average_rating"] == 4.5

    def test_public_aggregate_empty(self, install_db):
        install_db({"seller_reviews": []})
        r = client.get(f"/sellers/{SELLER_ID}/reviews")
        assert r.json()["average_rating"] is None and r.json()["reviews"] == []


# ===========================================================================
# Search alerts
# ===========================================================================

class TestSearchAlerts:
    def test_create_requires_criteria(self, install_db):
        install_db({"search_alerts": []})
        assert client.post("/search-alerts", json={}, headers=BUYER).status_code == 400
        r = client.post("/search-alerts", json={"make": "Toyota", "max_price": 1000000}, headers=BUYER)
        assert r.status_code == 201 and r.json()["is_active"] is True

    def test_list_and_patch_and_delete(self, install_db):
        install_db({"search_alerts": [
            {"id": "a1", "user_id": BUYER_ID, "make": "Toyota", "model": None, "max_price": 1000000.0,
             "min_year": None, "city": None, "is_active": True, "created_at": NOW}]})
        assert ids(client.get("/search-alerts", headers=BUYER).json()) == ["a1"]
        r = client.patch("/search-alerts/a1", json={"is_active": False}, headers=BUYER)
        assert r.status_code == 200 and r.json()["is_active"] is False
        assert client.patch("/search-alerts/a1", json={"city": "Pune"}, headers=BUYER).json()["city"] == "Pune"
        assert client.delete("/search-alerts/a1", headers=BUYER).status_code == 204
        assert client.get("/search-alerts", headers=BUYER).json() == []

    def test_foreign_alert_forbidden(self, install_db):
        install_db({"search_alerts": [
            {"id": "a1", "user_id": BUYER_ID, "make": "Toyota", "model": None, "max_price": None,
             "min_year": None, "city": None, "is_active": True, "created_at": NOW}]})
        assert client.patch("/search-alerts/a1", json={"city": "Pune"}, headers=SELLER).status_code == 403
        assert client.delete("/search-alerts/a1", headers=SELLER).status_code == 403

    def test_matches_active_listings(self, install_db):
        install_db({
            "listings": search_seed(),
            "search_alerts": [
                {"id": "a1", "user_id": BUYER_ID, "make": "Toyota", "model": None, "max_price": 1000000.0,
                 "min_year": None, "city": None, "is_active": True, "created_at": NOW}],
        })
        r = client.get("/search-alerts/a1/matches", headers=BUYER)
        assert r.status_code == 200
        assert ids(r.json()["matches"]) == ["L1"]  # L2 Honda / L3 over budget / L4 draft

    def test_unknown_alert(self, install_db):
        install_db({"search_alerts": []})
        assert client.get("/search-alerts/nope/matches", headers=BUYER).status_code == 404


# ===========================================================================
# Subscriptions
# ===========================================================================

class TestSubscriptions:
    def test_create_pending_order(self, install_db):
        install_db({"user_subscriptions": []})
        r = client.post("/subscriptions",
                        json={"plan_type": "pro_buyer_alerts", "amount_paid": 499.0}, headers=BUYER)
        assert r.status_code == 201
        assert r.json()["status"] == "pending"
        assert r.json()["valid_until"]  # defaulted to now + 30 days

    def test_invalid_plan(self, install_db):
        install_db({"user_subscriptions": []})
        r = client.post("/subscriptions", json={"plan_type": "gold", "amount_paid": 99}, headers=BUYER)
        assert r.status_code == 400

    def test_confirm_activates(self, install_db):
        install_db({"user_subscriptions": [
            {"id": "s1", "user_id": BUYER_ID, "plan_type": "pro_buyer_alerts", "status": "pending",
             "razorpay_order_id": None, "razorpay_payment_id": None, "amount_paid": 499.0,
             "currency": "INR", "valid_until": "2026-09-30T00:00:00+00:00", "created_at": NOW}]})
        r = client.patch("/subscriptions/s1/confirm",
                         json={"razorpay_order_id": "order_123", "razorpay_payment_id": "pay_123"},
                         headers=BUYER)
        assert r.status_code == 200
        assert r.json()["status"] == "active"
        assert r.json()["razorpay_payment_id"] == "pay_123"
        assert client.patch("/subscriptions/s1/confirm",
                            json={"razorpay_order_id": "order_123", "razorpay_payment_id": "pay_123"},
                            headers=BUYER).status_code == 400  # already active

    def test_cancel_keeps_row(self, install_db):
        install_db({"user_subscriptions": [
            {"id": "s1", "user_id": BUYER_ID, "plan_type": "pro_buyer_alerts", "status": "active",
             "razorpay_order_id": "o", "razorpay_payment_id": "p", "amount_paid": 499.0,
             "currency": "INR", "valid_until": "2026-09-30T00:00:00+00:00", "created_at": NOW}]})
        r = client.delete("/subscriptions/s1", headers=BUYER)
        assert r.status_code == 200 and r.json()["status"] == "canceled"
        assert len(client.get("/subscriptions", headers=BUYER).json()) == 1  # row kept for audit

    def test_foreign_subscription_forbidden(self, install_db):
        install_db({"user_subscriptions": [
            {"id": "s1", "user_id": SELLER_ID, "plan_type": "seller_unlimited_listings", "status": "pending",
             "razorpay_order_id": None, "razorpay_payment_id": None, "amount_paid": 999.0,
             "currency": "INR", "valid_until": "2026-09-30T00:00:00+00:00", "created_at": NOW}]})
        assert client.patch("/subscriptions/s1/confirm",
                            json={"razorpay_order_id": "order_x", "razorpay_payment_id": "pay_x"},
                            headers=BUYER).status_code == 403
        assert client.delete("/subscriptions/s1", headers=BUYER).status_code == 403

    def test_requires_auth(self, install_db):
        install_db({"user_subscriptions": []})
        assert client.get("/subscriptions").status_code == 401


class TestAdminSubscriptions:
    def test_admin_sees_all(self, install_db):
        install_db({"user_subscriptions": [
            {"id": "s1", "user_id": BUYER_ID, "plan_type": "pro_buyer_alerts", "status": "pending",
             "razorpay_order_id": None, "razorpay_payment_id": None, "amount_paid": 499.0,
             "currency": "INR", "valid_until": "2026-09-30T00:00:00+00:00", "created_at": NOW}]})
        assert len(client.get("/admin/subscriptions", headers=ADMIN).json()) == 1

    def test_non_admin_forbidden(self, install_db):
        install_db({"user_subscriptions": []})
        assert client.get("/admin/subscriptions", headers=BUYER).status_code == 403

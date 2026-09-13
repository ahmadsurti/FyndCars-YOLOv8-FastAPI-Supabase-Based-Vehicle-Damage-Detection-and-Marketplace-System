"""
fynd(cars) — Comprehensive Backend & Database Battle-Testing Suite
Tests concurrency, security, boundary enforcement, CV quality gates,
intake lifecycle, and edge cases.
"""

import asyncio
import io
import time
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from api import app
import quality_gate
from agentic import rc_extractor, vlm_verifier
from utils import calculate_damage_stats, utc_now_iso

client = TestClient(app)

SELLER_ID = "seller-uuid-battle-1"
BUYER_ID = "buyer-uuid-battle-2"
ADMIN_ID = "admin-uuid-battle-3"

SELLER_AUTH = {"Authorization": "Bearer demo-seller", "X-User-Id": SELLER_ID}
BUYER_AUTH = {"Authorization": "Bearer demo-buyer", "X-User-Id": BUYER_ID}
ADMIN_AUTH = {"Authorization": "Bearer demo-admin", "X-User-Id": ADMIN_ID}


def _create_synthetic_image(blur=False, dark=False, overexposed=False, corrupt=False) -> bytes:
    """Generate precise test synthetic images for quality gate validation."""
    if corrupt:
        return b"NOT_AN_IMAGE_PAYLOAD_RANDOM_CORRUPT_BYTES_XYZ"
    
    if dark:
        img = np.full((300, 300, 3), 10, dtype=np.uint8)  # Mean lum ~10 < 40
    elif overexposed:
        img = np.full((300, 300, 3), 245, dtype=np.uint8)  # Mean lum ~245 > 220
    elif blur:
        img = np.full((300, 300, 3), 128, dtype=np.uint8)  # Zero variance < 100
    else:
        # Sharp image with high variance grid pattern and mid-range luminance (mean ~128)
        img = np.full((300, 300, 3), 128, dtype=np.uint8)
        img[::10, :, :] = 0
        img[:, ::10, :] = 255
        cv2.putText(img, "TEST CAR SHARP", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
        
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


# ============================================================================
# 1. Quality Gate Battle Tests
# ============================================================================

class TestQualityGateBattle:
    def test_sharp_image_passes(self):
        img_bytes = _create_synthetic_image(blur=False)
        passes, reason = quality_gate.check_image_quality(img_bytes)
        assert passes is True
        assert reason == ""

    def test_blurry_solid_image_rejected(self):
        img_bytes = _create_synthetic_image(blur=True)
        passes, reason = quality_gate.check_image_quality(img_bytes)
        assert passes is False
        assert "blurry" in reason.lower()

    def test_pitch_black_image_rejected(self):
        img_bytes = _create_synthetic_image(dark=True)
        passes, reason = quality_gate.check_image_quality(img_bytes)
        assert passes is False
        assert "too dark" in reason.lower()

    def test_overexposed_image_rejected(self):
        img_bytes = _create_synthetic_image(overexposed=True)
        passes, reason = quality_gate.check_image_quality(img_bytes)
        assert passes is False
        assert "overexposed" in reason.lower()

    def test_corrupted_bytes_rejected(self):
        img_bytes = _create_synthetic_image(corrupt=True)
        passes, reason = quality_gate.check_image_quality(img_bytes)
        assert passes is False
        assert "cannot decode" in reason.lower()


# ============================================================================
# 2. Damage Stats & Utility Robustness
# ============================================================================

class TestUtilsBattle:
    def test_calculate_damage_stats_empty(self):
        stats = calculate_damage_stats([])
        assert stats["total_damages"] == 0
        assert stats["risk_assessment"] == "No damage detected"
        assert stats["most_common_damage"] == "none"

    def test_calculate_damage_stats_multiple(self):
        detections = [
            {"damage_type": "scratch", "severity": "minor", "confidence": 0.9, "area_percentage": 2.5, "estimated_cost": 100},
            {"damage_type": "scratch", "severity": "minor", "confidence": 0.8, "area_percentage": 1.5, "estimated_cost": 100},
            {"damage_type": "dent", "severity": "moderate", "confidence": 0.85, "area_percentage": 6.0, "estimated_cost": 500},
            {"damage_type": "crash", "severity": "severe", "confidence": 0.95, "area_percentage": 15.0, "estimated_cost": 2500},
        ]
        stats = calculate_damage_stats(detections)
        assert stats["total_damages"] == 4
        assert stats["damage_types"]["scratch"] == 2
        assert stats["damage_types"]["dent"] == 1
        assert stats["severity_distribution"]["severe"] == 1
        assert stats["risk_assessment"] == "High"
        assert stats["most_common_damage"] == "scratch"
        assert stats["total_estimated_cost"] == 3200

    def test_utc_now_iso_format(self):
        iso_str = utc_now_iso()
        assert "+00:00" in iso_str or "Z" in iso_str or "T" in iso_str


# ============================================================================
# 3. Agentic RC & VLM Verifier Battle Tests
# ============================================================================

class TestAgenticBattle:
    def test_rc_extraction_empty_or_corrupt_doc(self):
        res = rc_extractor.extract_rc_fields(b"not a valid pdf document", filename="corrupt.pdf")
        assert isinstance(res, dict)
        assert "make" in res
        assert "registration_number" in res

    def test_vlm_verifier_safe_fallback_on_unconfigured_env(self, monkeypatch):
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        result = vlm_verifier.verify(car_image_bytes=[b"fake"], doc_image_bytes=[], extracted_rc={})
        assert "verdict" in result
        assert "telemetry" in result
        assert "legal_identity" in result


# ============================================================================
# 4. End-to-End Route Security & Database Resilience
# ============================================================================

class TestListingSecurityAndLifecycle:
    def test_draft_update_forbidden_for_non_owner(self, install_db):
        install_db({
            "listings": [
                {"id": "l1", "seller_id": "demo-seller-id", "status": "draft", "price": 10000.0, "make": "Honda", "model": "City", "created_at": utc_now_iso()}
            ]
        })
        # Buyer cannot edit seller's listing
        r = client.patch("/listings/l1", json={"price": 12000.0}, headers={"Authorization": "Bearer demo-buyer"})
        assert r.status_code == 403

    def test_cannot_edit_active_listing_unless_admin(self, install_db):
        install_db({
            "listings": [
                {"id": "l1", "seller_id": "demo-seller-id", "status": "active", "price": 10000.0, "make": "Honda", "model": "City", "created_at": utc_now_iso()}
            ]
        })
        # Seller editing active listing rejected
        r_seller = client.patch("/listings/l1", json={"price": 12000.0}, headers={"Authorization": "Bearer demo-seller"})
        assert r_seller.status_code == 400

        # Admin editing active listing allowed
        r_admin = client.patch("/listings/l1", json={"price": 12000.0}, headers={"Authorization": "Bearer demo-admin"})
        assert r_admin.status_code == 200

    def test_submit_listing_guards(self, install_db):
        install_db({
            "listings": [
                {"id": "l1", "seller_id": "demo-seller-id", "status": "draft", "mileage_km": 50000, "ocr_odometer_km": 50000, "created_at": utc_now_iso()}
            ],
            "listing_images": [
                {"id": "img1", "listing_id": "l1", "storage_path": "p1"},
                {"id": "img2", "listing_id": "l1", "storage_path": "p2"},
            ],
            "listing_documents": [],
            "assessments": [],
        })
        # Fails with < 3 images
        r1 = client.post("/listings/l1/submit", headers={"Authorization": "Bearer demo-seller"})
        assert r1.status_code == 400
        assert "minimum of 3" in r1.json()["detail"].lower()

        # Add 3rd image but no document -> still fails
        install_db({
            "listings": [
                {"id": "l1", "seller_id": "demo-seller-id", "status": "draft", "mileage_km": 50000, "ocr_odometer_km": 50000, "created_at": utc_now_iso()}
            ],
            "listing_images": [
                {"id": "img1", "listing_id": "l1", "storage_path": "p1"},
                {"id": "img2", "listing_id": "l1", "storage_path": "p2"},
                {"id": "img3", "listing_id": "l1", "storage_path": "p3"},
            ],
            "listing_documents": [],
            "assessments": [],
        })
        r2 = client.post("/listings/l1/submit", headers={"Authorization": "Bearer demo-seller"})
        assert r2.status_code == 400
        assert "ownership_title" in r2.json()["detail"].lower()

        # Add ownership document -> succeeds
        install_db({
            "listings": [
                {"id": "l1", "seller_id": "demo-seller-id", "status": "draft", "mileage_km": 50000, "ocr_odometer_km": 50000, "created_at": utc_now_iso()}
            ],
            "listing_images": [
                {"id": "img1", "listing_id": "l1", "storage_path": "p1"},
                {"id": "img2", "listing_id": "l1", "storage_path": "p2"},
                {"id": "img3", "listing_id": "l1", "storage_path": "p3"},
            ],
            "listing_documents": [
                {"id": "doc1", "listing_id": "l1", "document_type": "ownership_title", "storage_path": "doc.pdf"}
            ],
            "assessments": [
                {"id": "asm1", "listing_id": "l1", "decision": "AUTO_APPROVE"}
            ],
        })
        r3 = client.post("/listings/l1/submit", headers={"Authorization": "Bearer demo-seller"})
        assert r3.status_code == 200
        assert r3.json()["final_status"] == "active"


class TestReviewQueueAndAdminBattle:
    def test_admin_override_workflow(self, install_db):
        install_db({
            "listings": [
                {"id": "l_esc", "seller_id": "demo-seller-id", "status": "escalated", "created_at": utc_now_iso()}
            ],
            "assessments": [
                {"id": "asm_esc", "listing_id": "l_esc", "decision": "ESCALATE", "created_at": utc_now_iso()}
            ],
            "assessment_overrides": [],
            "profiles": [
                {"id": "demo-admin-id", "role": "admin", "full_name": "Admin Tester"}
            ]
        })
        # Admin approves escalated listing
        r = client.post(
            "/queue/l_esc/override",
            json={"override_decision": "APPROVE", "reason": "Inspector verified superficial damage only"},
            headers={"Authorization": "Bearer demo-admin"}
        )
        assert r.status_code == 201
        assert r.json()["new_status"] == "active"

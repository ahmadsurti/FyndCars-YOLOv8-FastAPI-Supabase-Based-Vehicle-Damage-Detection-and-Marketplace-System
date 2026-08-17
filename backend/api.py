"""
fynd(cars) — FastAPI app
POST /assess  — YOLOv8 inference → policy decision
GET  /health  — system status
GET  /policy  — current rules config
Routers: /listings, /queue, /admin (mounted below)
         /messages, /saved-listings, /sellers, /search-alerts, /subscriptions
         (marketplace extensions)
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import assessment

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("fynd(cars)_api")

PROJECT_ROOT = assessment.PROJECT_ROOT


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class DamageDetection(BaseModel):
    damage_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str
    location: str = "unknown"
    bbox: list = Field(default_factory=list)
    area_percentage: float = 0.0
    estimated_cost: int = 0


class DecisionTrace(BaseModel):
    rule_applied: str
    threshold: str = ""
    evidence: str = ""


class AssessmentResult(BaseModel):
    assessment_id: str
    timestamp: str
    processing_time_ms: int
    damages_detected: list[DamageDetection] = Field(default_factory=list)
    total_damages: int = 0
    decision: str  # AUTO_APPROVE | HUMAN_REVIEW | ESCALATE
    decision_confidence: float = Field(ge=0.0, le=1.0)
    decision_trace: list[DecisionTrace] = Field(default_factory=list)
    damage_stats: dict | None = None
    expert_commentary: str | None = None
    model_version: str = "yolov8n-v1"
    policy_version: str = "v1.0"
    cv_backend: str
    human_review_required: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    cv_available: bool
    agent_available: bool
    uptime_seconds: float


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
APP_START_TIME = time.time()

app = FastAPI(
    title="fynd(cars) API",
    description="AI-powered car marketplace backend. YOLOv8 damage assessment + policy triage.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from routes.listings import router as listings_router
    from routes.queue import router as queue_router
    from routes.admin import router as admin_router
    from routes.marketplace import (
        messages_router, saved_router, listing_extras_router,
        sellers_router, alerts_router, subs_router,
    )
    app.include_router(listings_router)
    app.include_router(queue_router)
    app.include_router(admin_router)
    app.include_router(messages_router)
    app.include_router(saved_router)
    app.include_router(listing_extras_router)
    app.include_router(sellers_router)
    app.include_router(alerts_router)
    app.include_router(subs_router)
    logger.info("All routers mounted")
except Exception as e:
    logger.error("Router mount failed: %s", e)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        cv_available=assessment.cv_available,
        agent_available=assessment.agent_available,
        uptime_seconds=round(time.time() - APP_START_TIME, 1),
    )


@app.post("/assess", response_model=AssessmentResult, tags=["Assessment"])
async def assess_damage(image: UploadFile = File(...)):
    """
    Upload a vehicle image → structured damage assessment.
    Returns: detected damages, AUTO_APPROVE / HUMAN_REVIEW / ESCALATE decision, full trace, stats and expert insight.
    """
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, f"Unsupported type: {image.content_type}. Use JPEG, PNG, or WebP.")

    image_bytes = await image.read()
    if len(image_bytes) < 1000:
        raise HTTPException(400, "Image too small or empty.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "Image exceeds 20MB limit.")

    if not assessment.cv_available:
        raise HTTPException(503, "CV model not available. Ensure best.pt is present and dependencies installed.")
    if not assessment.agent_available:
        raise HTTPException(503, "Policy agent not available.")

    assessment_id = str(uuid.uuid4())[:12]
    logger.info("[%s] Assessing: %s (%d bytes)", assessment_id, image.filename, len(image_bytes))

    try:
        result = assessment.run_assessment(image_bytes)
    except Exception as e:
        logger.error("[%s] Assessment error: %s", assessment_id, e)
        raise HTTPException(500, f"Assessment failed: {e}")

    logger.info("[%s] Done: %d damages, %s, %dms",
                assessment_id, result["total_damages"], result["decision"], result["processing_time_ms"])

    return AssessmentResult(
        assessment_id=assessment_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **result,
    )


@app.get("/policy", tags=["Policy"])
async def get_policy():
    """Current policy config — what rules drive decisions."""
    policy_path = PROJECT_ROOT / "policies"
    files = {f.stem: f.name for f in policy_path.glob("*.y*ml")} if policy_path.exists() else {}
    return {
        "policy_version": "v1.0",
        "policy_files": files,
        "decision_types": ["AUTO_APPROVE", "HUMAN_REVIEW", "ESCALATE"],
        "severity_levels": ["minor", "moderate", "severe"],
        "rules_summary": {
            "no_damage": "AUTO_APPROVE",
            "minor_only": "AUTO_APPROVE",
            "any_moderate": "HUMAN_REVIEW",
            "multiple_moderate": "HUMAN_REVIEW",
            "any_severe": "ESCALATE",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

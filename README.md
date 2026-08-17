# FyndCars: Multimodal AI Vehicle Assessment & Verified Marketplace

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=flat-square&logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FE5F50?style=flat-square)
![Docling](https://img.shields.io/badge/Docling-Document%20Parsing-8A2BE2?style=flat-square)
![OpenRouter](https://img.shields.io/badge/VLM-Gemma%204%2031B-4285F4?style=flat-square)
![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square)

> **Autonomous Intake • Multimodal AI Verification • Deterministic Policy Triage • Verified Automotive Marketplace**

**FyndCars** is an enterprise-grade automotive marketplace and automated vehicle intake platform. It replaces tedious manual seller forms with an intelligent one-shot ingestion pipeline: sellers upload vehicle inspection photos and an Indian Registration Certificate (RC), and the system automatically inspects image quality, parses ownership records, verifies 360° coverage, reads odometer telemetry, detects exterior damages via YOLOv8, and triages the listing using a deterministic policy engine with complete auditability in Supabase PostgreSQL under strict Row Level Security (RLS).

---

## 📑 Table of Contents

1. [System Architecture & Intake Pipeline](#-system-architecture--intake-pipeline)
2. [Core Features](#-core-features)
3. [Database Architecture & Migrations](#-database-architecture--migrations)
4. [Prerequisites & Installation](#-prerequisites--installation)
5. [Configuration & Environment Variables](#-configuration--environment-variables)
6. [API Reference](#-api-reference)
7. [Automated Testing & Performance](#-automated-testing--performance)
8. [License & Notice](#-license--notice)

---

## 🏗 System Architecture & Intake Pipeline

FyndCars implements a layered, fail-fast intake architecture that prevents corrupted, fraudulent, or poor-quality listings from entering the marketplace:

```
[Seller Upload: 360° Images + RC PDF/Image]
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │ Gate 0: Pre-Upload Quality Gate         │ ──(Fails Laplacian blur < 100.0 or
  │ (Laplacian Variance + Luminance Check)  │    Luminance < 40 / > 220) ──► 400 Bad Request
  └─────────────────────────────────────────┘
                     │ (Passes ~2ms CPU check)
                     ▼
  ┌─────────────────────────────────────────┐
  │ Gate 1: Docling Document Intelligence   │ ──(Extracts: Make, Model, Variant,
  │ (In-Memory Stream + Regex/LLM Fallback) │    VIN, Plate No, Fuel, Mfg Year)
  └─────────────────────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │ Gate 2: Multimodal VLM Verification     │ ──(One-shot Gemma 4 31B:
  │ (OpenRouter Gemma 4 31B Vision)         │    360° coverage, Odometer OCR, Plate Match)
  └─────────────────────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │ Gate 3: YOLOv8 Computer Vision          │ ──(10 Damage Classes: Scratches,
  │ (Bounding Boxes + Severity Estimation)  │    Dents, Broken Lamps, Glass Shatter, etc.)
  └─────────────────────────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │ Gate 4: Deterministic Policy Triage     │ ──(Evaluates rules.yaml against signals)
  │ (AUTO_APPROVE / HUMAN_REVIEW / ESCALATE)│
  └─────────────────────────────────────────┘
                     │
                     ▼
[Draft Listing Created in Supabase with RLS & Auto-filled Specs]
```

### 1. Gate 0: Ultra-Fast OpenCV Quality Gate (`quality_gate.py`)
- **Blur Detection:** Calculates the variance of the Laplacian operator on all uploaded photos. Rejects blurry imagery (`variance < 100.0`).
- **Lighting Check:** Analyzes average grayscale luminance. Flags underexposed (`< 40`) or overexposed (`> 220`) imagery.
- **Cost:** ~$0.00, executes in ~2ms on CPU before any cloud or LLM API calls are dispatched.

### 2. Gate 1: Docling Document Parsing (`agentic/rc_extractor.py`)
- Ingests Registration Certificate (RC) documents directly from memory buffers using Docling's `DocumentStream`.
- Employs pre-compiled regular expressions for Indian RTO formats (Registration Numbers, Chassis/VIN numbers, Engine Numbers, Fuel Types, Years).
- Seamless fallback to OpenRouter LLM (`google/gemma-4-31b-it:free`) for non-standard or distressed document layouts.

### 3. Gate 2: Gemma 4 31B Multimodal VLM Verification (`agentic/vlm_verifier.py`)
- Dispatches a single structured multimodal prompt to Gemma 4 31B with all vehicle photos.
- **360° Angle Audit:** Verifies standard perspectives (`front`, `rear`, `left_side`, `right_side`, `interior`, `odometer`).
- **Odometer OCR:** Extracts digital or analog odometer reading (`ocr_odometer_km`) for anti-rollback fraud prevention.
- **License Plate Arbitration:** Extracts visible registration plates and cross-references them against the Docling RC extraction.

### 4. Gate 3 & 4: YOLOv8 Inference & Policy Triage (`assessment.py`)
- Detects 10 vehicle damage classes (`crack`, `crash`, `dent`, `dislocated_part`, `glass_shatter`, `lamp_broken`, `no_part`, `rub`, `scratch`, `tire_flat`).
- Calculates surface area percentages and repair cost estimates.
- Maps detections against `policies/rules.yaml` and `damage_triage.md` SOPs, generating an immutable, explainable `decision_trace`.

---

## ⚡ Core Features

| Module | Technical Implementation |
| --- | --- |
| **One-Shot Automated Intake** | `POST /listings/auto-extract` processes multipart images and RC document in a single request, creating the draft listing and saving complete damage telemetry. |
| **Indian Automotive Catalog** | Seeded with 284+ verified variants (2000–2026) across major Indian OEMs (Maruti Suzuki, Hyundai, Tata, Mahindra, Kia, Toyota, Honda, etc.). Provides lookup endpoints (`/listings/catalog/makes`, `/models`, `/variants`). |
| **Anti-Fraud Odometer Check** | `POST /listings/{id}/submit` compares seller-declared `mileage_km` against VLM-detected `ocr_odometer_km`. Deviations $> 5,000\text{ km}$ trigger automated review escalation. |
| **Faceted Marketplace Search** | `GET /listings` supports multi-parameter filtering (make, model, city, price range, year range, fuel type, transmission, body type, mileage, equipment tags, and full-text search). |
| **Admin Review Queue & Overrides** | Dedicated review portal (`/queue`) enabling administrators to inspect pending/escalated vehicles, analyze model detections, and execute auditable approval/rejection overrides with mandatory justification logs stored in `assessment_overrides`. |
| **Supabase JWT Authentication & RBAC** | Custom middleware (`middleware/auth.py`) verifying Supabase access tokens using `PyJWT` (HS256). Strictly extracts authorization roles (`admin`, `seller`, `buyer`) from administrative `app_metadata`. |
| **Buyer-Seller Messaging** | Direct contextual messaging service (`/messages`) linked to specific vehicle listings, featuring unread count tracking, thread history, and participant-restricted read acknowledgments. |
| **Verified Post-Sale Reviews** | Rating system (`/sellers/{id}/reviews`) restricted strictly to confirmed buyers of sold vehicles (`status = sold`), with database constraints preventing self-reviews and duplicate submissions. |
| **Impression Analytics** | Impression tracking service (`/listings/{id}/view`) utilizing client IP hashing to record unique visitor metrics and 7-day view trends without storing raw PII. |
| **Pro Search Alerts** | Saved search alert engine (`/search-alerts`) storing buyer vehicle search criteria and providing query matching endpoints against active catalog inventory. |
| **Platform Subscriptions** | Subscription tier structure (`user_subscriptions`) supporting commercial listing plans (`seller_unlimited_listings`, `pro_buyer_alerts`, `ai_inspection_bundle`) with payment confirmation hooks. |

---

## 🗄 Database Architecture & Migrations

All database schemas, constraints, RLS policies, and triggers are version-controlled in `supabase/migrations/`:

```
supabase/migrations/
├── 001_profiles.sql                     # Profiles table, role checks, auth trigger, RLS
├── 002_listings.sql                     # Listings, photos, documents, submit triggers
├── 003_assessments.sql                  # AI assessment outputs, overrides audit log, RLS
├── 004_storage_and_messages.sql         # Storage buckets and buyer-seller chat system
├── 005_marketplace_extensions.sql       # Saved listings, views, subscriptions, reviews, alerts
├── 006_sold_tracking.sql                # Post-sale buyer attribution schema
├── 007_verification_telemetry_and_catalog.sql # VLM verification fields, vehicle catalog table & indexes
├── 008_vehicle_catalog_seed.sql         # 284 researcher-verified Indian vehicle variants
└── seed_admin.sql                       # Administrative role bootstrap utility script
```

### PostgreSQL Row Level Security (RLS) Standards
- **Public Visibility:** Active listings, catalog entries, aggregate seller reviews, and public profile handles are world-readable (`SELECT true`).
- **Owner-Restricted Mutation:** Draft listings, bookmarks, subscriptions, search alerts, and message threads can only be viewed or modified by the authenticated user (`auth.uid() = user_id`).
- **Administrative Access:** Admin endpoints operate via Supabase `service_role` client with comprehensive role enforcement at the FastAPI dependency boundary (`require_role(["admin"])`).

---

## 🚀 Prerequisites & Installation

### Prerequisites
- **Python:** `>= 3.12`
- **Supabase Project:** Cloud instance or local Supabase CLI
- **OpenRouter API Key:** For multimodal Gemma 4 31B VLM verification and Docling LLM fallback

### 1. Clone the repository
```bash
git clone https://github.com/ahmadsurti/FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System.git
cd FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System
```

### 2. Configure Python Virtual Environment
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Execute Database Migrations
In your Supabase SQL Editor, execute the migrations in `supabase/migrations/` sequentially (`001` through `008`).

### 5. Launch the Backend Server
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation is immediately available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## ⚙ Configuration & Environment Variables

Create a `backend/.env` file based on the template below:

```env
# ── Supabase Configuration ───────────────────────────────────────────────
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET=YOUR_JWT_SECRET

# ── Computer Vision / ML Configuration ────────────────────────────────────
CONFIDENCE_THRESHOLD=0.25
MODEL_PATH=./models/best.pt

# ── API Server Configuration ──────────────────────────────────────────────
PORT=8000
CORS_ORIGIN=http://localhost:5173

# ── Multimodal VLM & LLM Configuration (OpenRouter) ────────────────────────
LLM_ENABLED=1
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-YOUR_OPENROUTER_KEY
LLM_MODEL=google/gemma-4-31b-it:free
```

---

## 🔌 API Reference

### Automated Intake & Listings
- `POST /listings/auto-extract` — One-shot intake: upload 360° photos and RC document; executes Gate 0, Docling parsing, VLM verification, and YOLOv8 triage.
- `GET /listings` — Search active marketplace inventory with faceted filters.
- `GET /listings/{id}` — Retrieve full vehicle specification, photos, and verification badges.
- `GET /listings/{id}/assessment` — Fetch latest AI damage assessment, bounding boxes, and policy trace.
- `POST /listings/{id}/submit` — Transition draft listing to `active`, `pending`, or `escalated` with anti-fraud odometer validation.
- `POST /listings/{id}/sell` — Record vehicle sale with optional buyer attribution.

### Vehicle Catalog
- `GET /listings/catalog/makes` — Retrieve distinct verified vehicle manufacturers.
- `GET /listings/catalog/models?make=Hyundai` — Retrieve models for a given make.
- `GET /listings/catalog/variants?make=Hyundai&model=Creta` — Retrieve all variants, production years, transmissions, and OEM color palettes.

### Review Queue (Admins)
- `GET /queue` — Retrieve triage queue of vehicles awaiting human review.
- `POST /queue/{listing_id}/override` — Execute auditable human-in-the-loop approval or rejection override.

### Marketplace Extensions
- `POST /messages` & `GET /messages` — Contextual listing inquiries and buyer-seller chat threads.
- `POST /listings/{id}/save` & `GET /saved-listings` — Buyer listing bookmarks.
- `POST /listings/{id}/view` — Record unique visitor impression (IP-hashed).
- `POST /listings/{id}/reviews` — Submit verified post-sale review (buyer-only constraint).
- `POST /search-alerts` — Create saved search criteria alert.
- `POST /subscriptions` & `PATCH /subscriptions/{id}/confirm` — Commercial tier management.

---

## 🧪 Automated Testing & Performance

FyndCars includes a comprehensive automated test suite covering authentication, damage inference, marketplace search, messaging, review gating, and administrative workflows.

```bash
cd backend
python -m pytest tests/ -v -p no:langsmith -p no:logfire
```

### Benchmark Results
- **Pytest Suite:** **87 passed in 8.25s** (>12x speedup via batching and zero-allocation triage)
- **Linter & Type Checks:** **`ruff check .` — All checks passed! (0 errors, 0 warnings)**

---

## 📄 License & Notice

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) and [NOTICE](NOTICE) files for details.

```
Copyright 2026 Ahmad Surti

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

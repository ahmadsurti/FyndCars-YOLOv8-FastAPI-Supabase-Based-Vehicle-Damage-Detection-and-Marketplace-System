# FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-ultralytics-FE5F50?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square)

> **Project Status: Under Active Development.** Backend services, database migrations, and ML inference pipelines are implemented. Frontend interface is currently in progress.

An AI-powered automotive marketplace platform and triage backend. When sellers list vehicles and upload inspection imagery, every photo is processed through a computer vision damage detection pipeline (YOLOv8) paired with a deterministic rule engine (`policies/rules.yaml`). The system automatically classifies vehicle damage, calculates affected surface area and repair estimates, and triages listings into `AUTO_APPROVE`, `HUMAN_REVIEW`, or `ESCALATE` status. Listings requiring review are queued for administrative oversight with an immutable audit log recorded directly in Supabase PostgreSQL under strict Row Level Security (RLS).

---

## Features

| Module | What it does |
| --- | --- |
| **YOLOv8 Damage Detection** | Processes vehicle images using PyTorch/Ultralytics to detect 10 distinct damage classes (`crack`, `crash`, `dent`, `dislocated_part`, `glass_shatter`, `lamp_broken`, `no_part`, `rub`, `scratch`, `tire_flat`). Calculates bounding boxes, percentage surface area affected, spatial location, severity classification, and preliminary repair cost estimation. |
| **Deterministic Policy Engine** | Evaluates damage signals (`damage_type`, `severity`, `confidence`) against a declarative YAML ruleset (`policies/rules.yaml`). Maps detections to actionable operational decisions (`AUTO_APPROVE`, `HUMAN_REVIEW`, `ESCALATE`) backed by standard operating procedure (SOP) references (`damage_triage.md`). |
| **Unified Assessment Pipeline** | Integrates computer vision inference, policy triage, damage statistical aggregation, and contextual expert commentary into a reusable service layer (`assessment.py`) shared by both standalone and listing-associated endpoints. |
| **Expert Commentary & Knowledge Base** | Generates structured diagnostic insights and verification checklists using keyword-retrieved SOP playbooks (`repair_playbook.md`, `sla_notes.md`). Includes optional fallback to OpenRouter LLM completions when enabled via configuration. |
| **Marketplace Listings Service** | Complete CRUD operations for vehicle inventory supporting multi-attribute faceted search (make, model, city, price range, year range, fuel type, transmission, body type, mileage, equipment tags, and title search). Generates standardized listing titles via PostgreSQL computed columns (`year make model variant`). |
| **Multi-Image Lifecycle Triage** | Evaluates overall vehicle condition upon submission (`POST /listings/{id}/submit`) using a "worst-decision-wins" heuristic across all uploaded image assessments. Prevents premature listing state changes during incremental draft uploads. |
| **Admin Review Queue & Overrides** | Dedicated review portal endpoints (`/queue`) enabling administrators to inspect pending/escalated vehicles, analyze model detections, and execute auditable approval/rejection overrides with mandatory justification logs stored in `assessment_overrides`. |
| **Supabase JWT Authentication** | Custom authentication middleware (`middleware/auth.py`) verifying Supabase access tokens using `PyJWT` (HS256). Strictly extracts authorization roles from administrative `app_metadata` to prevent privilege escalation from user-editable metadata. |
| **Role-Based Access Control (RBAC)** | Enforces hierarchical permissions across three primary roles (`admin`, `seller`, `buyer`) across both the FastAPI application dependency layer (`require_role`) and PostgreSQL database policies. |
| **PostgreSQL Row Level Security (RLS)** | Comprehensive RLS enforcement across all 12 platform tables ensuring strict data isolation, owner-restricted mutations, public catalog visibility, and admin-only administrative actions. |
| **Automated Database Triggers** | PostgreSQL triggers manage automated profile provisioning upon user registration (`handle_new_user`), timestamp updates (`set_updated_at`), and enforce listing validation (minimum 3 photos and 1 ownership document) prior to review submission. |
| **Storage Bucket Security** | Granular storage policies managing three distinct Supabase Storage buckets: `car-images` (seller vehicle photos), `annotated-images` (detection bounding box outputs), and `car-documents` (private ownership titles, road inspections, and insurance records). |
| **Buyer-Seller Messaging** | Direct contextual messaging service (`/messages`) linked to specific vehicle listings, featuring unread count tracking, thread history, and participant-restricted read acknowledgments. |
| **Verified Post-Sale Reviews** | Trust and rating system (`/sellers/{id}/reviews`) restricted strictly to confirmed buyers of sold vehicles (`status = sold`), with database constraints preventing self-reviews and duplicate submissions. |
| **Pro Search Alerts** | Saved search alert engine (`/search-alerts`) storing buyer vehicle search criteria and providing query matching endpoints against active catalog inventory. |
| **Platform Subscription Management** | Subscription tier structure (`user_subscriptions`) supporting commercial listing plans (`seller_unlimited_listings`, `pro_buyer_alerts`, `ai_inspection_bundle`) with payment confirmation hooks. |
| **Impression Analytics** | Impression tracking service (`/listings/{id}/view`) utilizing client IP hashing to record unique visitor metrics and 7-day view trends without collecting personally identifiable information. |
| **Administrative Governance** | Centralized admin portal for profile management, role assignment, legal document verification/rejection with feedback notes, and platform health telemetry. |

---

## Prerequisites

| Dependency | Minimum Version | Verification Command |
| --- | --- | --- |
| Python | `>= 3.12` | `python --version` |
| Pip | Latest | `pip --version` |
| Docker & Docker Compose | Modern | `docker --version` |
| Supabase Project | Cloud / Self-Hosted | Check [Supabase Dashboard](https://supabase.com) |

---

## Setup from Scratch

### 1. Clone the repository

```bash
git clone https://github.com/Ahmad/FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System.git
cd FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System
```

### 2. Configure Python virtual environment

```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Populate `backend/.env` with your Supabase credentials and model configurations (see [Configuration / Environment Variables](#configuration--environment-variables)).

### 5. Execute database migrations

In your Supabase SQL Editor, execute the migration scripts located in `supabase/migrations/` sequentially:

1. `001_profiles.sql` — Profiles schema, role checks, trigger on user creation, and RLS policies.
2. `002_listings.sql` — Listings, listing photos, document management, and submission validation triggers.
3. `003_assessments.sql` — AI assessment outputs, decision traces, and override audit logs.
4. `004_storage_and_messages.sql` — Storage bucket access policies and buyer-seller chat system.
5. `005_marketplace_extensions.sql` — Saved listings, view metrics, subscriptions, verified reviews, and search alerts.
6. `006_sold_tracking.sql` — Post-sale buyer attribution schema.

Initialize your admin account using `seed_admin.sql` by updating your registered user email.

### 6. Verify or supply model weights

Ensure the trained YOLOv8 model weights file is present at `backend/models/best.pt`. If no custom checkpoint is present, the service automatically falls back to `yolov8n.pt`.

### 7. Run the development server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

API documentation will be accessible at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 8. (Optional) Run with Docker

```bash
docker compose up --build
```

---

## Configuration / Environment Variables

The backend relies on environment variables defined in `backend/.env`. Never commit actual `.env` secret files to version control.

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

# ── LLM Service Configuration (Optional) ──────────────────────────────────
LLM_ENABLED=0
LLM_API_KEY=your_api_key_here
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1
```

### Configuration Reference

| Variable | Default | Description |
| --- | --- | --- |
| `SUPABASE_URL` | None | Base URL for your Supabase project instance. |
| `SUPABASE_SERVICE_ROLE_KEY` | None | Privileged service role key for administrative database transactions. |
| `SUPABASE_JWT_SECRET` | None | Secret key used to decode and cryptographically verify Supabase JWTs. |
| `CONFIDENCE_THRESHOLD` | `0.25` | Minimum confidence score threshold for YOLOv8 bounding box predictions. |
| `MODEL_PATH` | `./models/best.pt` | Local file path to the YOLOv8 PyTorch weights file. |
| `PORT` | `8000` | Port on which the Uvicorn web server listens. |
| `CORS_ORIGIN` | `http://localhost:5173` | Allowed origin for Cross-Origin Resource Sharing. |
| `LLM_ENABLED` | `0` | Flag (`1` or `0`) to toggle optional LLM-generated expert commentary. |
| `LLM_API_KEY` | None | API authorization key for LLM gateway service. |
| `LLM_MODEL` | `openai/gpt-4o-mini` | Model identifier string for completions. |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Base endpoint URL for LLM provider API. |

---

## How to Use

### 1. Seller: Create Listing & Upload Inspection Data
1. Authenticate with an account assigned the `seller` role.
2. Submit vehicle details to `POST /listings` to initialize a draft record.
3. Upload at least 3 car inspection images to `POST /listings/{id}/images` (triggers automated YOLOv8 inference and returns damage diagnostics per photo).
4. Upload proof of ownership to `POST /listings/{id}/documents` (`document_type: ownership_title`).
5. Finalize submission via `POST /listings/{id}/submit`. The backend evaluates all damage detections: clean/minor damage transitions directly to `active`, while moderate or severe damage is routed to `pending` or `escalated`.

### 2. Administrator: Queue Review & Human-in-the-Loop Override
1. Authenticate with an `admin` account.
2. Query `GET /queue` to retrieve all listings requiring human verification.
3. Review detected damages, confidence values, SOP policy evidence, and uploaded title documents.
4. Execute an override decision via `POST /queue/{listing_id}/override` (`override_decision: APPROVE` or `REJECT`) with auditable rationale.
5. The listing status is updated to `active` or `rejected`, and an audit record is permanently appended to `assessment_overrides`.

### 3. Buyer: Browse, Inquire & Transact
1. Query `GET /listings` to search active vehicles using multi-parameter filters.
2. Fetch complete vehicle history and AI damage assessment via `GET /listings/{id}` and `GET /listings/{id}/assessment`.
3. Initiate direct communication with the seller via `POST /messages`.
4. Once the deal concludes and the seller flags the vehicle as sold (`POST /listings/{id}/sell`), the recorded buyer submits a verified rating via `POST /listings/{id}/reviews`.

---

## Project Structure

```
FyndCars-YOLOv8-FastAPI-Supabase-Based-Vehicle-Damage-Detection-and-Marketplace-System/
├── .gitignore                      # Git ignore specifications (ignores .env, virtual environments)
├── implementation_plan.md          # Comprehensive architectural specification document
├── yolov8n.pt                      # YOLOv8 base model weights
├── supabase/
│   └── migrations/
│       ├── 001_profiles.sql        # Profiles schema, role checks, auth triggers, RLS
│       ├── 002_listings.sql        # Listings, images, documents schema, submit verification trigger
│       ├── 003_assessments.sql     # AI assessment results, overrides table, RLS
│       ├── 004_storage_and_messages.sql # Storage buckets security policies and buyer-seller chat
│       ├── 005_marketplace_extensions.sql # Saved listings, view metrics, subscriptions, reviews, alerts
│       ├── 006_sold_tracking.sql   # Post-sale buyer assignment and transaction timestamping
│       └── seed_admin.sql          # Administrative role bootstrap utility script
└── backend/
    ├── api.py                      # FastAPI application entrypoint, middleware, and route mounting
    ├── assessment.py               # Central assessment orchestrator (Detection -> Policy -> Commentary)
    ├── car_damage_detector.py      # YOLOv8 inference wrapper, severity classifier, cost estimator
    ├── db.py                       # Supabase client initializer (service-role context)
    ├── utils.py                    # Statistical aggregation utilities for damage reports
    ├── Dockerfile                  # Container definition for Python 3.12 backend
    ├── docker-compose.yml          # Container orchestration service definition
    ├── requirements.txt            # Production runtime dependencies
    ├── requirements-dev.txt        # Development and testing requirements
    ├── pytest.ini                  # Pytest execution configuration
    ├── .env.example                # Template for environment configuration
    ├── agentic/
    │   ├── decision_agent.py       # Rule-matching engine evaluating signals against rules.yaml
    │   ├── policy_loader.py        # YAML policy ingestion and dataclass mapping
    │   ├── expert_ai.py            # Diagnostic commentary builder with RAG retrieval
    │   ├── adapters.py             # Schema conversion utilities for detection structures
    │   ├── sop_retriever.py        # Markdown parser extracting standard operating procedures
    │   ├── schemas.py              # Strongly-typed assessment data definitions
    │   ├── _utils.py               # Internal utility functions
    │   ├── llm/                    # Providers, prompts, and interfaces for optional LLM completions
    │   └── rag/                    # Simple keyword retriever for knowledge base chunks
    ├── middleware/
    │   └── auth.py                 # JWT decoding, signature verification, and RBAC dependencies
    ├── routes/
    │   ├── listings.py             # Vehicle listing CRUD, media uploads, submission, and sale status
    │   ├── queue.py                # Admin review queue retrieval and override execution
    │   ├── admin.py                # User profile management, role assignment, document verification
    │   └── marketplace.py          # Messaging, bookmarks, view analytics, reviews, alerts, subscriptions
    ├── policies/
    │   ├── rules.yaml              # Declarative triage rules and threshold definitions
    │   └── damage_triage.md        # SOP reference text for triage decision paths
    ├── knowledge/
    │   ├── repair_playbook.md      # Domain guidelines for automotive repair recommendations
    │   └── sla_notes.md            # Operational resolution targets
    ├── tests/                      # Automated test suite
    └── notebooks/                  # Model evaluation and experimentation notebooks
```

---

## Deployment

The backend service is containerized for deployment on any standard virtual private server (VPS) or container runtime.

### Docker Container Deployment

1. Build and run the image using Docker Compose:
   ```bash
   cd backend
   docker compose up -d --build
   ```
2. Configure a reverse proxy (e.g., NGINX or Caddy) to handle SSL termination and route requests to `http://127.0.0.1:8000`.
3. Set `CORS_ORIGIN` in production `.env` to match the client web application domain.

---

## Troubleshooting

| Problem | Root Cause | Resolution |
| --- | --- | --- |
| `503 CV model not available` | Model file missing or corrupt at specified `MODEL_PATH`. | Verify that `backend/models/best.pt` exists or fallback `yolov8n.pt` is in the working path. |
| `401 Unauthorized: Invalid or expired token` | Provided JWT token is invalid, expired, or failed signature check. | Verify client passed a valid Supabase access token in `Authorization: Bearer <token>` and `SUPABASE_JWT_SECRET` is correctly configured. |
| `403 Forbidden: Requires role: ['admin']` | User's JWT does not contain the required role in `app_metadata`. | Ensure the user account role has been properly updated in `auth.users.raw_app_meta_data` via Supabase SQL or admin endpoints. |
| `503 Database client unavailable` | Supabase credentials missing in backend environment. | Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are populated in `backend/.env`. |
| `400 A minimum of 3 vehicle photos are required...` | Database trigger `trg_validate_listing_submission` blocked submission. | Upload at least 3 photos via `POST /listings/{id}/images` prior to calling `/submit`. |
| `400 Mandatory proof of ownership document... must be uploaded` | Listing lacks an `ownership_title` document in `listing_documents`. | Upload ownership verification via `POST /listings/{id}/documents` prior to submission. |

---

## What I Learned from Building This

### Decoupling Heavy ML Inference from Web/Data Services
One fundamental engineering constraint addressed in this project is that deep learning frameworks (PyTorch, Ultralytics YOLOv8) are incompatible with lightweight serverless functions due to substantial memory footprints and execution overhead. Architecting the application around a dedicated FastAPI service layer while offloading relational state, authentication, and file storage to Supabase allowed the platform to maintain high computational performance without sacrificing managed cloud infrastructure benefits.

### Multi-Layered Security & Dual-Boundary RBAC
Implementing security across both the API gateway layer and the database layer highlighted the importance of defense-in-depth:
1. **API Layer (`FastAPI`):** Enforces token validity, extracts identity from `app_metadata` (preventing tampering of roles by users), and restricts route execution.
2. **Database Layer (`Supabase PostgreSQL`):** Restricts row access using PostgreSQL RLS policies, ensuring that even if direct client connections or alternative access channels are established, data boundaries cannot be breached.

### Declarative Policy-Driven Automation
Rather than embedding brittle conditional statements throughout the business logic, extracting triage thresholds into a declarative configuration (`rules.yaml`) paired with standard operating procedures (`damage_triage.md`) created an inspectable decision engine. Every AI assessment produces an explainable `decision_trace` referencing exact policy rules and SOP evidence, providing an auditable human-in-the-loop workflow.

### Heuristic State Evaluation in Multi-Image Pipelines
Managing draft lifecycle transitions required careful synchronization between incremental client uploads and overall evaluation. By storing individual image detections immutably in `assessments` while maintaining the listing in `draft`, the system avoids erratic state oscillation. Only upon explicit submission does the aggregator evaluate all related assessments using a conservative "worst-decision-wins" rule to establish the final listing status.

### Biggest Takeaway
Modern AI-enabled web systems require clear separation between probabilistic model outputs and deterministic business logic. Machine learning models should generate structured, observable signals, but platform state transitions, access control, and compliance policies must remain strictly governed by deterministic rules, database constraints, and auditable governance logs.

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

Copyright 2026 Ahmad

# fynd(cars) — Complete Technical Blueprint

> **AI-Powered Car Marketplace with YOLOv8 Damage Assessment**  
> Status: Portfolio/University Project → Production-Pathway Architecture  
> Budget: $0 (free tiers) | Local-first development | Windows OS

---

## 1. PROJECT UNDERSTANDING

### What fynd(cars) Actually Is

A **car buy/sell marketplace** where every listing is backed by an AI damage assessment.  
When a seller uploads photos of their car, the YOLOv8 model runs and produces a structured damage report.  
The system then **automatically decides** whether the listing can go live immediately, or must be routed for admin review — all traceable, auditable, and explainable.

### Core Purpose
- Sellers list cars with photos → AI assesses damage → listing goes live or goes to review
- Buyers browse verified listings with transparent damage reports attached
- Admin handles review queue overrides + platform management
- Three roles only: **admin, seller, buyer** (assessor collapsed into admin)

### Core Workflows
1. **Seller flow**: Register → Create listing → Upload photos + documents → Submit → AI evaluates worst assessment → Listing live or queued for admin review
2. **Buyer flow**: Browse listings → View car details + damage report → Contact seller or make offer
3. **Admin flow**: Review pending/escalated listings → Override AI decisions → Log reasoning → Manage users, roles, policies, audit logs

### Decision Logic (built in Python)
- `AUTO_APPROVE` → listing goes live automatically
- `HUMAN_REVIEW` → routed to admin review queue
- `ESCALATE` → routed to admin review queue (higher priority)
- Triggered by: damage severity, confidence score, damage class
- **Worst decision wins**: when a listing has multiple image assessments, the most severe decision determines listing status

---

## 2. ARCHITECTURE DECISION

### Why NOT a pure SPA + serverless

The Python backend (`api.py`, `car_damage_detector.py`, `agentic/`) runs YOLOv8 inference locally.  
YOLOv8 requires PyTorch + ultralytics — **this cannot run in a browser, in Vercel edge functions, or in any serverless Node environment.**  
Therefore the Python FastAPI server is a **hard requirement** as a local backend process.

### Why NOT Supabase Functions for ML

Supabase edge functions run Deno (TypeScript). You cannot import PyTorch in them.  
Supabase is perfect for: database, auth, storage, realtime. Not for ML inference.

### Final Architecture Choice: **Monorepo — React Frontend + Python FastAPI Backend + Supabase**

```
SELLER/BUYER/ADMIN (Browser)
          ↓
  React 19 + Vite SPA (localhost:5173)
  [Claymorphism UI, Tailwind v4, Shadcn/ui]
          ↓
  ┌───────────────────────────────────────┐
  │  Python FastAPI (localhost:8000)      │
  │  • POST /assess — YOLOv8 inference    │
  │  • POST /listings — create listing    │
  │  • GET  /listings — browse (public)  │
  │  • POST /listings/{id}/submit — eval  │
  │  • GET  /listings/{id}/assessment    │
  │  • GET  /queue — admin review queue  │
  │  • POST /queue/{id}/override         │
  │  • GET  /health, /policy              │
  └───────────────┬───────────────────────┘
                  │
         ┌────────┴────────┐
         ↓                 ↓
  Supabase PostgreSQL   Supabase Storage
  (users, listings,     (car images,
   assessments,          documents)
   overrides, audit)
         ↑
  Supabase Auth
  (email/password + magic link)
  RBAC via custom claims / RLS
```

**Why this wins over alternatives:**
- Python stays Python — no rewriting ML inference
- Supabase free tier is genuinely useful (500MB DB, 1GB storage, 50K monthly active users)
- React frontend is already set up — no migration cost
- Monorepo means one git repo, one dev server command pair
- Production path is clear: swap localhost:8000 for a cloud VM, no code changes

---

## 3. FINAL TECH STACK

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React 19 + Vite 8 + TypeScript | Already set up. Fast HMR, tree-shaking, modern. |
| **UI** | Tailwind v4 + Shadcn/ui + Claymorphism | Already configured. Your brand identity. |
| **Icons** | Lucide React | Already installed. |
| **Backend** | Python FastAPI + Uvicorn | ML inference requires Python. FastAPI is production-ready. |
| **Testing (Python)** | pytest (22 tests) | Already wired, all passing. |
| **Database** | Supabase PostgreSQL | Free tier. Managed. RLS. Great DX. |
| **Auth** | Supabase Auth | Free. Email/password + magic link. JWT. |
| **Storage** | Supabase Storage | Free 1GB. Car images + annotated outputs. |
| **State (Frontend)** | React Context + useState | No Redux needed for this scale. |
| **API Client** | fetch / axios | Simple. No extra complexity. |
| **Payments** | Razorpay (future phase) | Indian payment gateway. Free to integrate in test mode. |
| **LLM (optional)** | OpenRouter API | Free tier available. Multiple models. Your key. |
| **Testing (Python)** | pytest (22 tests already exist) | Already wired. |
| **Testing (Frontend)** | Vitest | Same toolchain as Vite. |
| **Linting** | Oxlint (already configured) | Fast, already set up. |
| **Version Control** | Git + GitHub | Standard. |
| **CI/CD** | GitHub Actions (later) | Free. Already a ci.yml skeleton in the repo. |
| **Monitoring** | None for MVP | Not needed for portfolio phase. |

---

## 4. RBAC — ROLES & PERMISSIONS

### Three Roles

| Role | Who | What they can do |
|---|---|---|
| **Admin** | Platform owner (you) | Everything. Review queue, override AI decisions, manage users, roles, policies, audit logs, analytics. |
| **Seller** | Car owner listing a car | Create listings, upload photos + documents, submit listings, manage their own listings. |
| **Buyer** | Person browsing/buying | Browse verified listings, view damage reports, contact sellers. Cannot list cars. |

### Implementation

- Role stored as a `role` column in `profiles` table (Supabase PostgreSQL)
- Supabase RLS policies enforce role-based data access at the DB layer
- FastAPI reads the JWT from Supabase Auth, extracts the role claim, enforces it on endpoints
- React reads role from auth context and renders role-appropriate UI

### Decision Routing

```
Seller uploads images (per-image assessments saved, listing stays "draft")
         ↓
Seller submits listing → draft → pending (DB trigger validates 3 images + doc)
         ↓
Backend fetches ALL assessments for listing → picks worst decision:
  ESCALATE      → listing.status = "escalated"  → admin review queue
  HUMAN_REVIEW  → listing.status = "pending"     → admin review queue
  AUTO_APPROVE  → listing.status = "active"      → visible to buyers
  (none)        → listing.status = "pending"     → admin review queue
         ↓
Admin reviews → approves / rejects → listing.status updated → audit log entry created
```

---

## 5. DATABASE SCHEMA

### Tables

#### `profiles` (extends Supabase auth.users)
```sql
id            uuid PRIMARY KEY REFERENCES auth.users(id)
role          text NOT NULL CHECK (role IN ('admin','seller','buyer'))
full_name     text
phone         text
avatar_url    text
created_at    timestamptz DEFAULT now()
updated_at    timestamptz DEFAULT now()
```

#### `listings`
```sql
id              uuid PRIMARY KEY DEFAULT gen_random_uuid()
seller_id       uuid REFERENCES profiles(id)
title           text NOT NULL
description     text
make            text NOT NULL          -- e.g. "Toyota"
model           text NOT NULL          -- e.g. "Camry"
year            int NOT NULL
price_usd       numeric(10,2)
mileage_km      int
status          text DEFAULT 'draft'   -- draft | pending | active | rejected | sold | escalated
city            text
created_at      timestamptz DEFAULT now()
updated_at      timestamptz DEFAULT now()
```

#### `listing_images`
```sql
id              uuid PRIMARY KEY DEFAULT gen_random_uuid()
listing_id      uuid REFERENCES listings(id) ON DELETE CASCADE
storage_url     text NOT NULL           -- Supabase Storage URL
is_primary      boolean DEFAULT false
order_index     int DEFAULT 0
uploaded_at     timestamptz DEFAULT now()
```

#### `assessments`
```sql
id                  uuid PRIMARY KEY DEFAULT gen_random_uuid()
listing_id          uuid REFERENCES listings(id)
image_id            uuid REFERENCES listing_images(id)
assessment_id_ext   text                -- UUID from FastAPI /assess response
damages_detected    jsonb               -- full damages array from API
total_damages       int
decision            text NOT NULL       -- AUTO_APPROVE | HUMAN_REVIEW | ESCALATE
decision_confidence float
decision_trace      jsonb               -- full trace array
model_version       text
policy_version      text
cv_backend          text
processing_time_ms  int
annotated_image_url text                -- Supabase Storage URL of bbox image
created_at          timestamptz DEFAULT now()
```

#### `assessment_overrides` (audit log)
```sql
id              uuid PRIMARY KEY DEFAULT gen_random_uuid()
assessment_id   uuid REFERENCES assessments(id)
listing_id      uuid REFERENCES listings(id)
assessor_id     uuid REFERENCES profiles(id)
original_decision   text
override_decision   text NOT NULL      -- APPROVE | REJECT
reason          text NOT NULL
created_at      timestamptz DEFAULT now()
```

#### `messages` (buyer ↔ seller contact — optional for MVP)
```sql
id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
listing_id  uuid REFERENCES listings(id)
sender_id   uuid REFERENCES profiles(id)
receiver_id uuid REFERENCES profiles(id)
body        text NOT NULL
read        boolean DEFAULT false
created_at  timestamptz DEFAULT now()
```

### Key Indexes
```sql
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_listings_seller ON listings(seller_id);
CREATE INDEX idx_assessments_listing ON assessments(listing_id);
CREATE INDEX idx_overrides_assessment ON assessment_overrides(assessment_id);
```

---

## 6. API ARCHITECTURE

### Existing Python FastAPI endpoints
- `POST /assess` — ML inference. Accepts image, returns full damage JSON.
- `GET /health` — health check
- `GET /policy` — current policy rules

### Listing endpoints (`routes/listings.py`)

```
GET  /listings              — browse active listings (public, paginated, filterable)
GET  /listings/{id}         — single listing with images (no assessment data)
POST /listings              — seller creates listing (auth: seller)
PATCH /listings/{id}        — seller updates draft (auth: owner | admin)
DELETE /listings/{id}       — seller removes listing (auth: owner | admin)

POST /listings/{id}/images  — seller uploads image → per-image assessment saved
POST /listings/{id}/documents — seller uploads ownership document (draft only)
POST /listings/{id}/submit  — seller submits → backend evaluates worst assessment decision
GET  /listings/{id}/assessment — public: get full assessment details for a listing
```

### Review queue endpoints (`routes/queue.py` — admin only)

```
GET  /queue                 — admin review queue (HUMAN_REVIEW + ESCALATE, paginated)
POST /queue/{listing_id}/override  — admin submits override decision
GET  /queue/audit-log       — full audit log
```

### Admin endpoints (`routes/admin.py`)

```
GET  /admin/users           — all users + roles
PATCH /admin/users/{id}/role — change user role
GET  /admin/analytics       — platform analytics
```

### Auth Flow
- React calls Supabase Auth → gets JWT
- JWT sent in `Authorization: Bearer <token>` header to FastAPI
- FastAPI verifies JWT using Supabase secret → extracts `role` from user metadata
- FastAPI enforces role on each endpoint via a dependency

---

## 7. FRONTEND PAGES & COMPONENTS

### Pages / Routes

```
/                       → Landing page (hero, how it works, CTA)
/auth/login             → Login (email/password + magic link)
/auth/register          → Register (choose role: buyer or seller)

/listings               → Browse all active listings (public)
/listings/:id           → Single listing detail + damage report

/seller/dashboard       → My listings overview
/seller/listings/new    → Create new listing (multi-step form)
/seller/listings/:id/edit → Edit draft listing

/admin/queue            → HUMAN_REVIEW + ESCALATE review queue (was /assessor/queue)
/admin/queue/:id        → Review single listing — AI report + override form

/admin/dashboard        → Platform analytics
/admin/users            → User management

/profile                → User profile settings
```

### Key Components
- `DamageReport` — renders detected damages with severity badges, confidence scores, decision trace
- `ListingCard` — card with car photo, price, damage badge (AI verified / pending / clean)
- `AssessmentBadge` — AUTO_APPROVE (green) / HUMAN_REVIEW (amber) / ESCALATE (red)
- `ImageUploader` — drag-drop, triggers assessment on upload
- `OverrideForm` — admin approve/reject + required reasoning text
- `AuditLog` — paginated table of all decisions and overrides
- `PolicyViewer` — renders current rules.yaml in human-readable form
- `RoleGuard` — wraps routes, redirects unauthorized users

---

## 8. MONOREPO FOLDER STRUCTURE

```
fynd(cars)/                          ← Git root
├── frontend/                       ← React + Vite (currently at root, move here)
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                 ← Shadcn primitives
│   │   │   ├── listing/            ← ListingCard, ListingDetail
│   │   │   ├── assessment/         ← DamageReport, AssessmentBadge
│   │   │   └── admin/              ← OverrideForm, ReviewQueue, UserTable, AuditLog
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   ├── supabase.ts         ← Supabase client
│   │   │   ├── api.ts              ← FastAPI client (fetch wrapper)
│   │   │   └── utils.ts
│   │   ├── context/
│   │   │   └── AuthContext.tsx
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                        ← Python FastAPI
│   ├── api.py                      ← Main FastAPI app + CORS + router mounting
│   ├── assessment.py               ← Unified assessment pipeline (detect→decide→commentary)
│   ├── car_damage_detector.py      ← YOLOv8 inference
│   ├── utils.py                    ← Damage stats + helpers
│   ├── agentic/                    ← Policy engine + LLM integration
│   ├── policies/
│   ├── knowledge/
│   ├── models/
│   │   └── best.pt                 ← YOLOv8n weights (5.9MB)
│   ├── routes/
│   │   ├── listings.py             ← CRUD + image upload + submit + assessment
│   │   ├── queue.py                ← Admin review queue + overrides
│   │   └── admin.py                ← User management + analytics
│   ├── middleware/
│   │   └── auth.py                 ← Supabase JWT verification + RBAC
│   ├── requirements.txt
│   └── .env
│
├── supabase/                       ← Database migrations + RLS policies
│   └── migrations/
│       ├── 001_profiles.sql
│       ├── 002_listings.sql
│       ├── 003_assessments.sql
│       └── 004_rls_policies.sql
│
├── docs/
│   └── architecture.md
│
├── .gitignore
└── README.md
```

---

## 9. ENVIRONMENT VARIABLES

### Frontend (`frontend/.env.local`) — CLIENT-SAFE
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
VITE_API_URL=http://localhost:8000
```

> ⚠️ VITE_ prefix exposes to browser. NEVER put service_role key or API secrets here.

### Backend (`backend/.env`) — SERVER-ONLY
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key   ← NEVER expose to frontend
SUPABASE_JWT_SECRET=your-jwt-secret               ← from Supabase dashboard

# ML
CONFIDENCE_THRESHOLD=0.25
MODEL_PATH=./models/best.pt

# LLM (optional)
LLM_ENABLED=0
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-openrouter-key
LLM_MODEL=openai/gpt-4o-mini

# API
PORT=8000
CORS_ORIGIN=http://localhost:5173
```

---

## 10. INTEGRATION: REACT ↔ FastAPI ↔ SUPABASE

### Auth Flow (critical to understand)
```
1. User logs in via Supabase Auth (React)
2. Supabase returns a JWT (access_token)
3. React stores JWT in memory (NOT localStorage for security)
4. Every API call to FastAPI includes: Authorization: Bearer <jwt>
5. FastAPI verifies the JWT using SUPABASE_JWT_SECRET
6. FastAPI extracts user ID + role from JWT claims
7. FastAPI checks role before processing the request
8. FastAPI uses SUPABASE_SERVICE_ROLE_KEY to read/write to DB (bypasses RLS)
9. Frontend NEVER touches the service_role key
```

### Image Upload Flow
```
1. Seller selects image in React ImageUploader component
2. React calls POST /listings/{id}/images with the image file
3. FastAPI saves to Supabase Storage, runs YOLOv8 → DecisionAgent per-image
4. Assessment saved to DB (listing stays "draft" — no status flip)
5. FastAPI returns per-image assessment result to React
6. React renders per-image DamageReport component
7. After all images + documents uploaded, seller clicks "Submit"
8. POST /listings/{id}/submit → backend evaluates worst assessment decision
9. ESCALATE → escalated, HUMAN_REVIEW → pending, AUTO_APPROVE → active
```

---

## 11. PAYMENTS (Razorpay — Future Phase)

> ⚠️ NOT for MVP. Implement in Phase 4.

Razorpay is a perfect fit for India:
- Free to integrate in **test mode** (no credit card required to test)
- Simple API: create order (backend) → checkout (frontend) → verify signature (backend)
- Cannot be deployed publicly without Razorpay business KYC
- For portfolio: run in test mode with test card numbers — it will demo perfectly

**What requires payment (suggested model):**
- Sellers: pay a small listing fee per car (e.g. ₹99 per listing)
- Or: 3 free listings/month, then paid
- Buyers: free to browse, contact, buy

**Integration when ready:**
1. Create Razorpay account → get test API keys
2. Backend: `POST /payments/create-order` → Razorpay creates order → returns order_id
3. Frontend: load Razorpay checkout script → user pays
4. Backend: `POST /payments/verify` → verify webhook signature → mark listing as paid

---

## 12. LLM INTEGRATION

**Provider recommendation: OpenRouter** (not direct OpenAI)
- Free credits on signup ($1 which is significant for gpt-4o-mini at $0.15/1M tokens)
- Single API, access to 100+ models
- If your key runs out → swap model to a free one (e.g. `mistral/mistral-7b-instruct:free`)

**What the LLM does (non-critical per the system design):**
- Generates human-readable repair guidance ("Here is why we recommend PDR for this dent...")
- Answers operator questions about a specific assessment
- Provides customer-facing explanation of the damage report

**What the LLM NEVER does:**
- Makes the `AUTO_APPROVE / HUMAN_REVIEW / ESCALATE` decision — that is always policy-driven
- If LLM is down → system works perfectly, LLM section just shows "unavailable"

---

## 13. FREE-TIER ANALYSIS

| Service | Free Tier | Usable? | Notes |
|---|---|---|---|
| **Supabase** | 500MB DB, 1GB storage, 50K MAU, 5GB bandwidth | 🟢 GENUINELY USEFUL | Perfect for portfolio scale |
| **Supabase Auth** | Included in free tier | 🟢 GENUINELY USEFUL | Magic link + email/password |
| **Supabase Storage** | 1GB included | 🟢 GENUINELY USEFUL | More than enough for car images at demo scale |
| **Vercel (frontend)** | Unlimited static deployments | 🟢 GENUINELY USEFUL | React SPA deploys perfectly |
| **Python backend** | LOCAL ONLY at $0 | 🟡 FREE BUT LIMITED | For production: needs a VPS ($5/mo on Hetzner/DigitalOcean) |
| **OpenRouter** | Free credits + free models | 🟢 GENUINELY USEFUL | `mistral-7b-instruct:free` always available |
| **Razorpay test mode** | Free | 🟢 GENUINELY USEFUL | Test cards work, no real money |
| **GitHub Actions** | 2,000 min/month free | 🟢 GENUINELY USEFUL | CI/CD is fine |
| **Docker** | Free | 🟢 GENUINELY USEFUL | Useful for Python backend consistency |

---

## 14. INTEGRATION STRATEGY — HOW TO GO FROM PORTFOLIO → PRODUCTION

> This is the answer to your A6 question. Read this carefully.

### Right Now (Local / Portfolio)
- React runs on `localhost:5173`
- FastAPI runs on `localhost:8000`
- Supabase is already cloud (free tier)
- All image storage goes to Supabase Storage

### The Critical Design Decision That Makes This Production-Ready From Day 1

**Never hardcode `localhost:8000` in the React source code.**

Instead, use the env variable `VITE_API_URL` everywhere. When you're local, it's `http://localhost:8000`. When you're in production, it's `https://api.yourplatform.com`. You change ONE env variable, not hundreds of files.

### Path to Production

```
STAGE 1 — LOCAL (now)
  - React: localhost:5173
  - FastAPI: localhost:8000
  - DB/Auth/Storage: Supabase cloud (free)

STAGE 2 — SOFT LAUNCH (when ready)
  - React → Deploy to Vercel (free, one git push)
  - FastAPI → Deploy to a $5/mo VPS (Hetzner, DigitalOcean, Render)
    • Run: uvicorn api:app --host 0.0.0.0 --port 8000
    • Use nginx as reverse proxy → https://api.yourplatform.com
    • Add SSL via Let's Encrypt (free, Certbot)
  - DB → Supabase (same free tier, just change nothing)
  - Change VITE_API_URL in Vercel dashboard → done

STAGE 3 — SCALE (if users come)
  - Supabase → upgrade to Pro ($25/mo) for more storage/connections
  - VPS → upgrade CPU tier if inference is slow under load
  - Consider: load balancer, multiple FastAPI workers
  - Consider: GPU VPS for faster YOLOv8 inference

STAGE 4 — ENTERPRISE (optional)
  - Migrate to Kubernetes if multiple services needed
  - Add Redis for caching hot listings
  - Add CDN (Cloudflare free) in front of everything
```

### Why NOT Serverless for FastAPI

Serverless (Vercel functions, AWS Lambda, Supabase edge) **cannot** run PyTorch. The model is 5.9MB but ultralytics + torch is 500MB+. That exceeds every serverless function limit. A VPS is the correct and only viable path.

### Why NOT Docker for local dev

Docker adds complexity. For local development, run the two processes directly:
```bash
# Terminal 1
cd backend && uvicorn api:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```
Docker becomes useful for **deployment** consistency — package the Python backend in a Docker container so your VPS runs it identically to your local machine.

---

## 15. SECURITY CHECKLIST

- [ ] `SUPABASE_SERVICE_ROLE_KEY` → ONLY in backend `.env`, never in frontend
- [ ] `VITE_SUPABASE_ANON_KEY` → safe for frontend (Supabase RLS protects data)
- [ ] FastAPI JWT verification → every protected endpoint verifies the token
- [ ] CORS → restrict to `VITE_API_URL` domain in production (not `*`)
- [ ] File upload validation → type (JPEG/PNG/WebP only), size (max 20MB — already implemented)
- [ ] RLS policies → every table has Row Level Security enabled in Supabase
- [ ] `.env` files → in `.gitignore` (already is)
- [ ] Model weights (`best.pt`) → include in repo (it's only 5.9MB, MIT-adjacent dataset)
- [ ] Razorpay → NEVER log full payment data, verify webhook signature server-side
- [ ] Admin routes → protected by role check in FastAPI AND by RLS in Supabase

---

## 16. THINGS THAT WILL ABSOLUTELY BITE YOU LATER

| Risk | Prevention |
|---|---|
| Hardcoding `localhost:8000` in React | Always use `VITE_API_URL` env variable |
| CORS errors when deploying | FastAPI CORS must list production frontend URL, not `*` |
| JWT verification failure | Ensure `SUPABASE_JWT_SECRET` matches your project |
| YOLOv8 cold start (first request is slow) | Load model at startup, not per-request — done in `CarDamageDetector.__init__` |
| Supabase storage URL expiry | Use signed URLs with appropriate expiry for private images |
| React sending ANON_KEY to FastAPI | FastAPI should only accept Supabase JWTs, not the anon key |
| Model file missing on VPS | Model weights (`best.pt`) must be included in deployment |
| Razorpay signature verification skipped | ALWAYS verify Razorpay webhook signature before marking payment as successful |
| ESCALATE during upload trapping listing | Status decisions happen only at submit time, not per-image — already fixed |

---

## 17. COST BREAKDOWN

| Scenario | Cost | What you get |
|---|---|---|
| **$0 / month** | $0 | Full local dev, Supabase free tier, no public deployment |
| **$5 / month** | $5 | Hetzner CX11 VPS for FastAPI, Vercel for React, Supabase free |
| **$30 / month** | $30 | Hetzner VPS + Supabase Pro ($25) — handles ~1,000 MAU |
| **Production** | ~$80-150/mo | Larger VPS + Supabase Pro + CDN + monitoring |

> Everything in this blueprint works at $0 locally. The Python backend is the ONLY thing that costs money when going public, because serverless cannot run PyTorch.

---

## 18. MVP vs FUTURE

### MUST HAVE (Phase 2 — frontend build)
- [ ] Seller: create listing + upload images + documents + submit → see AI damage report
- [ ] AI: YOLOv8 runs per-image → submit evaluates worst → listing status set
- [ ] Admin: review queue view + override form + audit log entry
- [ ] Buyer: browse active listings + view damage report (via separate endpoint)
- [ ] Admin: user management + role assignment
- [ ] Supabase Auth: email/password login for 3 roles (admin, seller, buyer)
- [ ] Supabase Storage: car images + documents stored

### SHOULD HAVE (Phase 3)
- [ ] Annotated image (bounding boxes rendered client-side on detected damage)
- [ ] Listing search + filters (make, model, year, price, damage severity)
- [ ] Buyer ↔ Seller messaging
- [ ] Policy viewer (show current rules.yaml in UI)
- [ ] Mobile-responsive design
- [ ] LLM-powered repair guidance

### NICE TO HAVE (Phase 4)
- [ ] Razorpay listing fee payment
- [ ] PDF report export
- [ ] Email notifications (Supabase has SMTP support)

### FUTURE (Phase 4+)
- [ ] Video ingestion
- [ ] Public deployment on VPS
- [ ] YOLOv8m (medium) model for better accuracy
- [ ] Analytics dashboard with Plotly charts

---

## 19. IMPLEMENTATION ROADMAP

### Phase 0 — Repo Setup [DONE]
1. Reorganized: React → `frontend/`, Python → `backend/`
2. Created `backend/.env` from `.env.example`
3. Created Supabase project → migrations 001–005
4. Fixed double `_load_model()` bug in `car_damage_detector.py`
5. Unified assessment pipeline into `assessment.py`
6. Removed assessor role — 3-role system (admin, seller, buyer)

### Phase 1 — Backend & DB [DONE]
1. Supabase: all tables + RLS policies via versioned migrations
2. Backend: JWT middleware, `/listings`, `/queue`, `/admin`, `/assess` routes
3. Backend: unified assessment pipeline with submit-time decision evaluation
4. Frontend: AuthContext + RoleGuard + demo role switcher
5. 22/22 tests passing, all Python files compile clean

### Phase 2 — Frontend Core [CURRENT]
1. Seller: listing form + image upload → per-image assessment display → submit
2. `DamageReport` component: renders detection results
3. `AssessmentBadge` component with claymorphic styling
4. Buyer: listing browse page + detail page (assessment via separate endpoint)
5. Admin: review queue page + override form
6. Admin: user management table

### Phase 3 — Polish (Week 4)
1. Annotated image display (bounding boxes overlaid on car photo)
2. LLM repair guidance integration (OpenRouter)
3. Mobile responsiveness audit
4. Listing search + filters
5. Loading states, error states, empty states
6. Accessibility pass

### Phase 4 — Deployment Prep (When ready)
1. Docker-compose for Python backend
2. Vercel deployment for React
3. VPS setup for FastAPI (if going public)
4. CORS update for production URLs
5. Razorpay test mode integration

---

## 20. "START HERE" CHECKLIST

- [x] Create Supabase project at supabase.com → note URL + anon key + service_role key + JWT secret
- [x] Create `backend/.env` and `frontend/.env.local` from templates
- [x] Install Python deps: `pip install -r requirements.txt -r requirements-dev.txt`
- [x] Test FastAPI locally: `uvicorn api:app --reload` → `curl http://localhost:8000/health`
- [x] Run migrations 001–005 in Supabase SQL Editor
- [x] Seed admin user via `seed_admin.sql`
- [x] Run frontend: `npm run dev` → confirm it loads
- [ ] Build seller listing creation flow with image upload + submit
- [ ] Build admin review queue page
- [ ] Build buyer browse + detail pages
- [ ] Verify full flow: login → create listing → upload images → submit → see decision → admin reviews
- [ ] Get OpenRouter API key → test LLM integration
- [ ] Do a design pass: ensure claymorphism theme is applied consistently

---

## 21. FINAL MASTER STACK

```
PROJECT:      fynd(cars)
ARCHITECTURE: React SPA + Python FastAPI (local) + Supabase (cloud)

ROLES:        admin | seller | buyer (3 roles, no assessor)

FRONTEND:     React 19 + Vite 8 + TypeScript
STYLING:      Tailwind CSS v4 + Shadcn/ui + Claymorphism
BACKEND:      Python 3.12 + FastAPI + Uvicorn
ML MODEL:     YOLOv8n (ultralytics) — trained, 5.9MB, CPU-capable
ASSESSMENT:   Unified pipeline in assessment.py (detect → decide → commentary)
DATABASE:     Supabase PostgreSQL (free tier)
AUTH:         Supabase Auth (email/password + magic link)
STORAGE:      Supabase Storage (car images, documents)
PAYMENTS:     Razorpay test mode (future phase)
LLM:          OpenRouter API (optional, non-critical)
HOSTING:      Local → Vercel (frontend) + Hetzner/DO VPS (backend)
TESTING:      pytest (22 tests passing) + Vitest (frontend)

ESTIMATED COST: $0/month (local dev) → $5/month (when public)
```

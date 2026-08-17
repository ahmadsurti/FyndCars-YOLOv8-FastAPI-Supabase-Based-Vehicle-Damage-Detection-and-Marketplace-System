# fynd(cars) — Master Task Tracker

## Phase 0 — Repo Setup & Architecture [COMPLETED]
- [x] Monorepo structure organized: React (`frontend/`) + FastAPI YOLOv8 (`backend/`)
- [x] Fixed YOLOv8 duplicate model loader in `car_damage_detector.py`
- [x] Created root `package.json` with concurrent dev execution (`npm run dev`)
- [x] Standardized `@` path aliases in `vite.config.ts` and `tsconfig.app.json`
- [x] Configured environment variable templates (`.env.example`)
- [x] Supabase versioned migrations (001–005) as the single source of truth (000_full_schema.sql removed as duplicate)

## Phase 1 — Database, Auth & Foundation [COMPLETED]
- [x] Supabase versioned migrations with strict RLS & performance indexes:
  - `001_profiles.sql` — 3 roles (admin, seller, buyer) + region selector
  - `002_listings.sql` — Auto-generated title, vehicle specs, mandatory 3-photo + document trigger
  - `003_assessments.sql` — YOLOv8 append-only damage reports + human override audit logs
  - `004_storage_and_messages.sql` — Storage bucket RLS for images, documents, overlays + messages
  - `005_marketplace_extensions.sql` — Saved listings, views, reviews, subscriptions, search alerts, features
- [x] Backend auth middleware (`backend/middleware/auth.py`) with Supabase JWT & RBAC role guards
- [x] Backend routers: `/listings`, `/queue`, `/admin`, `/assess`, `/health`, `/policy`
- [x] Unified assessment pipeline (`backend/assessment.py`) — single source of truth for detect→decide→commentary
- [x] Frontend AuthContext with 1-click role switcher for demo
- [x] Frontend RoleGuard for client route protection
- [x] Claymorphic Navbar, Footer, Login, Register, Home feed
- [x] Verified clean TypeScript build (0 errors)

## Codebase Optimization [COMPLETED]
- [x] Removed assessor role — collapsed to 3-role system (admin, seller, buyer)
- [x] Deduplicated assessment pipeline into `assessment.py` (eliminated circular import)
- [x] Fixed ESCALATE-during-upload trapping bug — status decisions now only at submit time
- [x] Fixed `damage_type` key mismatch in `calculate_damage_stats`
- [x] Fixed LLM prompt fallback for normalized damage keys
- [x] Public feed no longer leaks assessment data — separate `/assessment` endpoint
- [x] Review queue pagination (`limit`/`offset`) and admin-only access
- [x] Document/image upload guards — only draft listings for seller
- [x] Deleted 6 dead modules (explainer, trace, inpaint, vision init, full_schema, enhance_image)
- [x] 22/22 tests pass, all 18 Python files compile clean
- [x] Repo reduced ~30% (6,700 → 4,700 lines)

---

## Phase 2 — Frontend Build (NEXT)
> Backend and DB are locked. Only build frontend now.

### Roles: admin | seller | buyer (no assessor)

### Assessment Flow (backend handles this — frontend just displays results)
1. Seller uploads image → per-image assessment saved (no listing status change)
2. Seller submits listing → backend picks worst decision across all assessments
3. ESCALATE → escalated, HUMAN_REVIEW → pending, AUTO_APPROVE → active, none → pending
4. Admin reviews pending/escalated listings via `/queue` — can override

### Pages to Build
- [ ] **Seller: New Listing (`NewListing.tsx`)**
  - [ ] Auto-computed title preview (`[Year] [Make] [Model] [Variant]`)
  - [ ] Vehicle specs (fuel, transmission, owners, odometer, price, city)
  - [ ] Feature toggle pills
  - [ ] Mandatory 3+ photo uploader with per-image assessment display
  - [ ] Mandatory document uploader (RC / Title / Insurance)
  - [ ] Submit button → calls `POST /listings/{id}/submit`
- [ ] **Damage & Inspection Components**
  - [ ] `DamageReport.tsx` — defect badges, severity tags, repair cost estimates
  - [ ] `AssessmentBadge.tsx` — AUTO_APPROVE (green) / HUMAN_REVIEW (amber) / ESCALATE (red)
  - [ ] `AnnotatedImageOverlay.tsx` — bounding boxes on car photos (client-side rendering)
- [ ] **Buyer: Listing Detail (`ListingDetail.tsx`)**
  - [ ] Photo gallery + features + specs
  - [ ] AI inspection summary + decision trace (from `GET /listings/{id}/assessment`)
  - [ ] Document status badge
  - [ ] Save to Favorites, view logger, seller trust card, contact button
- [ ] **Admin: Review Queue (`ReviewQueue.tsx`)**
  - [ ] Pending + escalated listings tabbed view
  - [ ] Side-by-side image inspection with YOLOv8 bboxes
  - [ ] Document verification viewer
  - [ ] Override modal with mandatory audit reason
- [ ] **Seller: My Listings (`SellerListings.tsx`)**
  - [ ] Dashboard: draft, pending, active, sold tabs
  - [ ] Mark as Sold → triggers buyer review modal

---

## Phase 3 — Extended Features & Polish
- [ ] Direct messaging (buyer ↔ seller via Supabase `messages`)
- [ ] Pro search alerts wired to `search_alerts`
- [ ] Admin analytics dashboard (view counts, approval rates, conversion)
- [ ] Mobile responsiveness + micro-animations

---

## Phase 4 — Monetization & Deployment
- [ ] Razorpay paywalls (seller quotas, pro buyer subscriptions)
- [ ] Docker Compose for FastAPI + YOLOv8 CPU backend
- [ ] Vercel production build for React frontend

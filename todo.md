# fynd(cars) — Master Roadmap & Task Breakdown (`todo.md`)

---

## Phase 0: Prerequisites & Environment Setup
- [x] **Git Backup & Commit**: Completed & pushed.
- [x] **Supabase Database Provisioning**: Project provisioned (`iguprpfxdqvqsyeedftd.supabase.co`).
- [x] **Configure Environment Variables**:
  - `backend/.env` populated with live credentials & verified via live DB test.
  - `frontend/.env` populated with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- [x] **Execute Supabase SQL Migrations (In Order)**:
  - [x] `001_profiles.sql` — Ran with no errors & verified by backend test.
  - [x] `002_listings.sql` — Ran with no errors.
  - [x] `003_assessments.sql` — Ran with no errors.
  - [x] `004_storage_and_messages.sql` — Ran with no errors (storage buckets auto-created).
  - [x] `005_marketplace_extensions.sql` — Ran with no errors.
  - [x] `006_sold_tracking.sql` — Ran with no errors.
  - [x] `007_verification_telemetry_and_catalog.sql` — Ran with no errors.
  - [x] `008_vehicle_catalog_seed.sql` — Ran with no errors.
  - [x] `seed_admin.sql` — Ran with no errors.

---

## Phase 1: Authentication & Entry Modal
- [x] **Implement Login / Sign-In Modal**:
  - Triggered by clean white CTA button below Feature Cards.
  - High-end dual banner crossfade (`welcometothecult.jpg` / `welcomeback.jpg`).
  - Hero-matched rotating `DiaText` with 0.25em word spacing and baseline alignment.
  - Interactive draggable/slideable spring-physics mode toggle with 45° hover tilt CTA.
  - 1-click Demo accounts for Admin, Seller, and Buyer.
- [/] **Session & Role Provider**:
  - [x] Supabase Auth client session listener & Zustand store initialized.
  - [ ] Auto-route user post-auth to unified dashboard (`/app`) or admin portal (`/admin`).

---

## Phase 2: Design System & Unified Dashboard Shell Integration (`/app`)
- [x] **Universal Dashboard Shell Integration (`dashboard-shell`)**:
  - Replaced ad-hoc layout wrappers with `<DashboardLayout>` from `dashboard-shell/components/layout/DashboardLayout`.
  - Wrapped application in `<ThemeProvider>` from `dashboard-shell/context/theme-provider`.
  - Imported `dashboard-shell/styles/theme.css` in `frontend/src/index.css`.
  - Configured `sidebarProps` with clean, Lucide React navigation groups (Marketplace, Selling, Inbox, Admin Operations).
  - Streamlined `DashboardOverview` and placeholder screens: eliminated duplicate headers and redundant icon clutter.
  - Resolved all TypeScript indexing and module resolution errors across `dashboard-shell`.
- [x] **Unified App Shell (`/app`)**:
  - Responsive collapsible sidebar with active indicator, unread badges, and user profile pill (`NavUser`).
  - Header with `Cmd+K` trigger, unread messages badge, quick list button, and `ConfigDrawer` trigger.
- [x] **Sidebar Navigation Hierarchy**:
  - **Marketplace**: *Command Center* (`/app`), *Explore Inventory* (`/app/explore`), *Saved Shortlist* (`/app/saved`), *Search Alerts* (`/app/alerts`).
  - **Selling**: *+ Sell a Car* (`/app/sell`), *My Listings* (`/app/my-listings`), *Reputation & Reviews* (`/app/reviews`).
  - **Inbox**: *Messages* (`/app/messages` with live unread count).
  - *(If Admin)*: *Admin Operations* section (`/admin/queue`, `/admin/stats`, `/admin/audit`).
- [x] **Starting Screen — Unified Command Center (`/app`)**:
  - Personalized Greeting banner (*"Welcome back, [Name]"*) with dual primary CTAs (*"Explore Marketplace"* & *"+ List a Car"*).
  - Live KPI Telemetry Cards: Saved cars count (`/saved-listings`), active alerts (`/search-alerts`), active listings (`/listings/mine`), inspection trust score (`99.4%` / `5.0`).
  - Quick Garage Shelf: 4-gate AI multi-modal engine tracker & 1-click resume card for draft listings.
  - Curated Marketplace Feed Preview: Latest verified-clean inventory preview (`/listings?status_filter=active&sort=newest&limit=6`) with interactive specs and damage badges.
- [x] **Post-Auth Routing & Role Redirection**:
  - Wire landing page login button to immediately navigate to `/app` upon successful session.
  - Route demo role triggers (Admin, Seller, Buyer) directly to `/app`.

---

## Phase 3: Seller Flow — AI-Powered Intake Pipeline
- [ ] **Multi-Step Vehicle Intake Stepper (`/app/sell`)**:
  - **Step 1: Upload Dropzone**:
    - 3 to 15 vehicle photos (enforcing 25MB backend limit per file).
    - 1 Registration Certificate (RC) PDF or image.
    - Drag-and-drop ordering and primary image selector (`is_primary`).
  - **Step 2: Live 4-Gate AI Scan Animation (`POST /listings/auto-extract`)**:
    - Real-time animated progress steps with checkmarks:
      - *Gate 0*: Image clarity & luminance check (OpenCV).
      - *Gate 1a*: YOLOv8 defect inspection (scratches, dents, cracks bounding boxes).
      - *Gate 1b*: Docling OCR & entity extraction (Make, Model, Year, Fuel, VIN, Plate).
      - *Gate 1c*: Gemma VLM verification (odometer readout & document cross-match).
      - *Gate 2*: Draft listing created in DB with telemetry metadata.
  - **Step 3: Autofilled Specs & Pricing Review (`PATCH /listings/{id}`)**:
    - Pre-filled specs from RC & VLM (Make, Model, Year, Variant, Fuel, Owners, Plate, Mileage).
    - Seller inputs missing fields: `price`, `city`, `transmission`, `description`, `features` tags.
    - Detected damage preview with estimated repair costs.
  - **Step 4: Submission & Anti-Fraud Guard (`POST /listings/{id}/submit`)**:
    - Odometer delta guard (flagged if >1500 km delta) & plate mismatch verification.
    - Triage outcome feedback card: `AUTO_APPROVE` (`active`), `HUMAN_REVIEW` (`pending`), or `ESCALATE` (`escalated`).
- [ ] **My Listings & Inventory Manager (`/app/my-listings`)**:
  - Filter tabs: **All**, **Active**, **Pending Review**, **Drafts**, **Sold** (`GET /listings/mine`).
  - Listing view analytics card: Total views, unique viewers, 7-day trend (`GET /listings/{id}/views`).
  - Edit draft (`PATCH /listings/{id}`), Delete draft (`DELETE /listings/{id}`).
  - Mark as Sold modal (`POST /listings/{id}/sell`) with buyer ID selection to unlock buyer review.

---

## Phase 4: Buyer Flow — Marketplace & Vehicle Experience
- [ ] **Marketplace Feed & Discovery (`/app/explore`)**:
  - Infinite-scroll vehicle feed with offset pagination (`GET /listings?status=active`).
  - Catalog-driven cascading filters (Make, Model, Variant, Year range, Price range, Fuel, Transmission, Mileage, City, Feature tags).
  - Vehicle Card component with photo gallery, `verified_clean` badge, YOLO damage summary badge, and 1-click bookmark.
- [ ] **Vehicle Deep-Dive & Inspection Report (`/app/listings/$listingId`)**:
  - High-res photo gallery with thumbnail strip.
  - **Interactive YOLO Damage Inspector**: Toggle between clean photo and bounding box overlays (scratch, dent, crack tags, confidence %, repair estimates).
  - Docling verified document status strip (RC, ownership title, plate readout).
  - Verified seller profile card (`GET /sellers/{id}/reviews`) with star rating.
  - Inquire / Message seller modal (`POST /messages`).
  - Bookmark listing (`POST /saved-listings` / `DELETE /saved-listings/{id}`).
- [ ] **Saved Shortlist & Comparison (`/app/saved`)**:
  - Bookmarked vehicles grid.
  - Side-by-side comparison drawer (compare price, mileage, year, and YOLO defect count).
- [ ] **Search Alerts & Inventory Drops (`/app/alerts`)**:
  - Create, edit, toggle, and delete search criteria (`GET /search-alerts`, `POST /search-alerts`).
  - View live inventory matches in real time (`GET /search-alerts/{id}/matches`).
- [ ] **Inquiries & Conversations (`/app/messages`)**:
  - Split-view message thread grouped by listing.
  - Real-time chat stream with unread badge synchronization.
- [ ] **Verified Post-Purchase Review**:
  - Modal triggered for recorded buyer of sold listing (`POST /listings/{id}/reviews`).

---

## Phase 5: Admin Operations Portal (`/admin`)
- [ ] **Moderation & Review Queue (`/admin/queue`)**:
  - Feed of listings in `pending` and `escalated` status (`GET /queue`).
  - Side-by-side comparison: Seller photos with YOLO boxes vs RC document vs VLM odometer readout.
  - Override action: `APPROVE` (`active`) or `REJECT` with mandatory auditable reasoning (`POST /queue/{id}/override`).
- [ ] **Document Verification Console (`/admin/documents`)**:
  - Inspect and verify or reject legal documents (`PATCH /admin/documents/{id}/verify`).
- [ ] **Platform Telemetry & KPIs (`/admin/stats`)**:
  - Executive dashboard: Status distribution counts, auto-approval rate %, total users, total overrides.
- [ ] **User & Role Governance (`/admin/users`)**:
  - User profiles table (`GET /admin/users`) with role update action (`PATCH /admin/users/{id}/role`).
- [ ] **Auditable Override Log (`/admin/audit`)**:
  - Immutable audit trail of every assessor override decision (`GET /admin/audit`).

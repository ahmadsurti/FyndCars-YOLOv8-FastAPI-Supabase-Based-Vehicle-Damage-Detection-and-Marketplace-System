# fynd(cars) — Master Roadmap & Task Breakdown (`todo.md`)

---

## Phase 0: Prerequisites & Environment Setup (Your Actions)
- [ ] **Git Backup & Commit**:
  - `git add .`
  - `git commit -m "feat(landing): complete animated hero, narrative reveal, and features"`
  - `git push origin main` (or current branch) to preserve current baseline.
- [ ] **Supabase Database Provisioning**:
  - Create a new project in [Supabase Dashboard](https://supabase.com/dashboard).
  - Copy API credentials:
    - Project URL (`SUPABASE_URL`)
    - Anon / Public Key (`SUPABASE_ANON_KEY`)
    - Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`)
    - JWT Secret (`SUPABASE_JWT_SECRET`)
- [ ] **Execute Supabase SQL Migrations (In Order)**:
  - Run via Supabase SQL Editor:
    1. `001_profiles.sql` (auth.users extension, role check, triggers)
    2. `002_listings.sql` (listings table, status machine, RLS)
    3. `003_assessments.sql` (YOLO detection traces, damage storage)
    4. `004_storage_and_messages.sql` (storage buckets `car-images`, `car-documents`, messaging table)
    5. `005_marketplace_extensions.sql` (reviews, saved listings, alerts, subscriptions)
    6. `006_sold_tracking.sql` (sale confirmation & buyer verification)
    7. `007_verification_telemetry_and_catalog.sql` (vehicle catalog & telemetry indices)
    8. `008_vehicle_catalog_seed.sql` (catalog data)
    9. `seed_admin.sql` (initial admin user bootstrap)
- [ ] **Configure Environment Variables**:
  - `backend/.env` (FastAPI keys, Supabase URLs, secrets)
  - `frontend/.env` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`)

---

## Phase 1: Authentication & Entry Modal
- [ ] **Implement Login / Sign-In Modal**:
  - Triggered by the clean white CTA button below Feature Cards.
  - Integrate user-provided login modal code & design.
  - Support email/password, magic link, and demo roles (`admin`, `seller`, `buyer`).
- [ ] **Session & Role Provider**:
  - Initialize Supabase Auth client session listener.
  - Route user post-auth to unified dashboard or admin portal based on role.

---

## Phase 2: Design System & Dashboard Shell Integration (from `shadcn-admin-main`)
- [ ] **Adopt Shadcn Dashboard Architecture**:
  - Integrate core components: `Sidebar`, `Sheet`, `Dialog`, `Table`, `Tabs`, `CommandMenu`.
  - Port **`ConfigDrawer`** customization feature:
    - Theme switching (Dark, Light, System) with `#08090c` dark palette.
    - Layout switcher (Default, Compact, Full).
    - Sidebar modes (Sidebar, Floating, Inset).
    - Direction (LTR, RTL).
- [ ] **Unified App Shell (`/app`)**:
  - Persistent floating/inset sidebar with user profile badge, mode switch, and quick actions.
  - Top header with search command menu (`Cmd+K`), notification bell, theme trigger, and `ConfigDrawer`.

---

## Phase 3: Seller Flow — AI-Powered Intake Pipeline
- [ ] **Vehicle Intake Interface (`/app/sell`)**:
  - Multi-file image dropzone (3–15 car photos, quality validation).
  - Registration Certificate (RC) upload (PDF/image).
- [ ] **Realtime Processing Status**:
  - Visual feedback for pipeline execution:
    - *Gate 0*: Image clarity/luminance check.
    - *Gate 1a*: YOLOv8 damage inspection (scratches, dents, cracks).
    - *Gate 1b*: Docling RC entity extraction (Make, Model, Year, Fuel, Plate).
    - *Gate 1c*: Gemma multimodal VLM verification & odometer reading.
- [ ] **Autofilled Listing Review & Pricing**:
  - Display extracted car specs & detected damages overlay.
  - Allow seller to review/edit pricing, city, description.
  - Submit listing (`POST /listings/{id}/submit`) triggering policy triage (`AUTO_APPROVE` vs `HUMAN_REVIEW`).

---

## Phase 4: Buyer Flow — Marketplace & Discovery
- [ ] **Marketplace Grid & Search (`/app/explore` or `/app/browse`)**:
  - Infinite scroll vehicle feed with dynamic catalog filters (Make, Model, Year, Price, Damage status).
  - Vehicle detail card with YOLO damage badges and Docling verified badge.
- [ ] **Listing Detail View**:
  - High-res photo gallery with damage overlay pins.
  - Assessment report & VLM inspection breakdown.
  - Messaging trigger to contact seller (`POST /messages`).
  - Save listing (`POST /saved-listings`) & Search alert creation.

---

## Phase 5: Admin Flow — Operational Moderation & Queue
- [ ] **Inspection & Triage Queue (`/admin/queue`)**:
  - Human review queue for `HUMAN_REVIEW` and `ESCALATE` listings.
  - Side-by-side comparison of seller photos, RC document, and AI damage detections.
  - Admin override action (Approve / Reject with notes).
- [ ] **System Analytics & User Control (`/admin`)**:
  - Platform statistics (Active listings, triage volume, turnaround times).
  - User role management & audit log table.

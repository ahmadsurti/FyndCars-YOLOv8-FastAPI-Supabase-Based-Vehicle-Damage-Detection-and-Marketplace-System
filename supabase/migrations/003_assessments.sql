-- ============================================================
-- Migration 003: assessments + assessment_overrides
-- AI damage assessment results and human override audit log
-- ============================================================

-- assessments table
create table public.assessments (
  id                   uuid primary key default gen_random_uuid(),
  listing_id           uuid not null references public.listings (id) on delete cascade,
  image_id             uuid references public.listing_images (id) on delete set null,
  -- External ID from FastAPI /assess response
  assessment_id_ext    text,
  -- Full detection array as returned by YOLOv8 + policy engine
  damages_detected     jsonb not null default '[]'::jsonb,
  total_damages        smallint not null default 0,
  -- Decision output
  decision             text not null
                         constraint assessments_decision_check
                         check (decision in ('AUTO_APPROVE', 'HUMAN_REVIEW', 'ESCALATE')),
  decision_confidence  numeric(4, 3),    -- 0.000–1.000
  decision_trace       jsonb not null default '[]'::jsonb,
  -- Model metadata
  model_version        text,
  policy_version       text,
  cv_backend           text,
  processing_time_ms   integer,
  -- Annotated image (bounding boxes) stored in Supabase Storage
  annotated_image_path text,
  -- Timestamp
  created_at           timestamptz not null default now()
);

comment on table public.assessments is 'Immutable record of every AI damage assessment. One row per image assessed. Never update — append only.';
comment on column public.assessments.decision is 'AUTO_APPROVE | HUMAN_REVIEW | ESCALATE — output of the policy engine.';
comment on column public.assessments.damages_detected is 'Raw array of damage detections from YOLOv8 + policy normalization.';
comment on column public.assessments.decision_trace is 'Audit trace: which rules fired and why.';

-- assessment_overrides table (human audit log — append-only)
create table public.assessment_overrides (
  id                  uuid primary key default gen_random_uuid(),
  assessment_id       uuid not null references public.assessments (id) on delete cascade,
  listing_id          uuid not null references public.listings (id) on delete cascade,
  assessor_id         uuid not null references public.profiles (id) on delete restrict, -- reviewer (now always admin)
  original_decision   text not null,
  override_decision   text not null
                        constraint overrides_decision_check
                        check (override_decision in ('APPROVE', 'REJECT')),
  reason              text not null,    -- required — reviewer must explain every override
  created_at          timestamptz not null default now()
);

comment on table public.assessment_overrides is 'Append-only audit log of every human override. Never update or delete rows.';

-- Enable RLS
alter table public.assessments enable row level security;
alter table public.assessment_overrides enable row level security;

-- Grant Data API access
grant select, insert on public.assessments to authenticated;
grant select, insert on public.assessment_overrides to authenticated;
-- anon cannot see assessment details (contains internal AI signals)

-- ============================================================
-- assessments RLS Policies
-- ============================================================

-- SELLER: read assessments for their own listings
create policy "assessments: seller read own"
  on public.assessments
  for select
  to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id
        and l.seller_id = (select auth.uid())
    )
  );

-- ASSESSOR + ADMIN: read all assessments
create policy "assessments: admin read all"
  on public.assessments
  for select
  to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- INSERT: only via backend service_role (FastAPI) — no direct frontend insert
-- The FastAPI backend uses service_role which bypasses RLS.
-- Frontend inserts are blocked unless the user is admin (safety net).
create policy "assessments: admin insert"
  on public.assessments
  for insert
  to authenticated
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- ============================================================
-- assessment_overrides RLS Policies
-- ============================================================

-- ASSESSOR + ADMIN: read all overrides
create policy "overrides: admin read"
  on public.assessment_overrides
  for select
  to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- SELLER: read overrides for their own listings
create policy "overrides: seller read own"
  on public.assessment_overrides
  for select
  to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id
        and l.seller_id = (select auth.uid())
    )
  );

-- INSERT: admin can submit overrides (service_role bypasses RLS; this policy is for direct client access)
create policy "overrides: admin insert"
  on public.assessment_overrides
  for insert
  to authenticated
  with check (
    (select auth.uid()) = assessor_id
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- ============================================================
-- Indexes
-- ============================================================

create index idx_assessments_listing    on public.assessments (listing_id);
create index idx_assessments_decision   on public.assessments (decision);
create index idx_assessments_created    on public.assessments (created_at desc);

create index idx_overrides_assessment   on public.assessment_overrides (assessment_id);
create index idx_overrides_listing      on public.assessment_overrides (listing_id);
create index idx_overrides_assessor     on public.assessment_overrides (assessor_id);
create index idx_overrides_created      on public.assessment_overrides (created_at desc);

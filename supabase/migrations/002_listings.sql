-- ============================================================
-- Migration 002: listings, listing_images, listing_documents
-- Complete Car marketplace listings with auto-generated title,
-- multi-region specs, mandatory document uploads, and min-3-photo rule.
-- ============================================================

-- listings table
create table public.listings (
  id                   uuid primary key default gen_random_uuid(),
  seller_id            uuid not null references public.profiles (id) on delete cascade,
  
  -- Mandatory Vehicle Identity
  make                 text not null,
  model                text not null,
  year                 smallint not null
                         constraint listings_year_check check (year >= 1900 and year <= 2100),
  variant              text, -- e.g. 'Asta 1.0 Turbo DCT'
  
  -- Auto-generated Standardized Title: [Year] [Make] [Model] [Variant]
  title                text generated always as (
                         year::text || ' ' || make || ' ' || model || coalesce(' ' || nullif(variant, ''), '')
                       ) stored,

  -- Mandatory Commercial & Specs
  price                numeric(12, 2) not null constraint listings_price_check check (price > 0),
  currency             text not null default 'INR'
                         constraint listings_currency_check check (currency in ('INR', 'USD', 'GBP', 'EUR')),
  fuel_type            text not null
                         constraint listings_fuel_check check (fuel_type in ('petrol', 'diesel', 'electric', 'cng', 'hybrid')),
  transmission         text not null
                         constraint listings_transmission_check check (transmission in ('manual', 'automatic')),
  mileage_km           integer not null
                         constraint listings_mileage_check check (mileage_km >= 0),
  owner_count          smallint not null default 1
                         constraint listings_owner_check check (owner_count >= 1 and owner_count <= 10),
  city                 text not null,
  
  -- Optional Vehicle Specs
  body_type            text constraint listings_body_check check (body_type in ('hatchback', 'sedan', 'suv', 'muv', 'coupe', 'convertible', 'wagon', 'other')),
  color                text,
  insurance_valid_until date,
  insurance_type       text constraint listings_insurance_check check (insurance_type in ('comprehensive', 'third_party', 'zero_dep', 'none')),
  description          text,
  
  -- Listing Lifecycle Status
  status               text not null default 'draft'
                         constraint listings_status_check
                         check (status in ('draft', 'pending', 'active', 'rejected', 'sold', 'escalated')),
  
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

comment on table public.listings is 'Car listings created by sellers. Title is auto-computed from specs for unified search.';
comment on column public.listings.title is 'Auto-computed: [Year] [Make] [Model] [Variant]';
comment on column public.listings.status is 'draft=not submitted | pending=awaiting AI/human review | active=live for buyers | rejected=not approved | sold=deal closed | escalated=needs senior review';

-- listing_images table (Minimum 3 images enforced on submit)
create table public.listing_images (
  id           uuid primary key default gen_random_uuid(),
  listing_id   uuid not null references public.listings (id) on delete cascade,
  storage_path text not null,
  is_primary   boolean not null default false,
  order_index  smallint not null default 0,
  uploaded_at  timestamptz not null default now()
);

comment on table public.listing_images is 'Car photos attached to a listing. Must have >= 3 images before submitting for review.';

-- listing_documents table (Mandatory legal documentation: RC/Title/V5C, Insurance, etc.)
create table public.listing_documents (
  id                  uuid primary key default gen_random_uuid(),
  listing_id          uuid not null references public.listings (id) on delete cascade,
  document_type       text not null
                        constraint doc_type_check check (
                          document_type in ('ownership_title', '-- RC (India') | Title/Pink Slip (USA) | V5C (UK) | Carte Grise (EU)
                            'road_inspection',    -- PUC (India) | Smog/Inspection (USA) | MOT (UK) | TÜV (EU)
                            'insurance_proof',    -- Comprehensive / Third-party policy
                            'loan_clearance',     -- Bank NOC / Form 35 / Lien release
                            'service_history'     -- Periodic maintenance records
                          )
                        ),
  document_name       text, -- Friendly user label (e.g. 'Registration Certificate (RC)')
  storage_path        text not null, -- Supabase Storage object path in 'car-documents' bucket
  verification_status text not null default 'pending'
                        constraint doc_verif_check check (verification_status in ('pending', 'verified', 'rejected')),
  rejection_reason    text,
  uploaded_at         timestamptz not null default now()
);

comment on table public.listing_documents is 'Mandatory legal proof files (RC/Title, Insurance, Inspection) required per vehicle.';

-- Enable RLS on all tables
alter table public.listings enable row level security;
alter table public.listing_images enable row level security;
alter table public.listing_documents enable row level security;

-- Grant Data API access
grant select, insert, update, delete on public.listings to authenticated;
grant select, insert, update, delete on public.listing_images to authenticated;
grant select, insert, update, delete on public.listing_documents to authenticated;
grant select on public.listings to anon;           -- buyers can browse without login
grant select on public.listing_images to anon;

-- ============================================================
-- listings RLS Policies
-- ============================================================

-- PUBLIC: anyone (including anon) can view active listings
create policy "listings: public read active"
  on public.listings for select to anon, authenticated
  using ( status = 'active' );

-- SELLER: can read their own listings (all statuses)
create policy "listings: seller read own"
  on public.listings for select to authenticated
  using ( (select auth.uid()) = seller_id );

-- ASSESSOR + ADMIN: can read all non-draft listings
create policy "listings: admin read all"
  on public.listings for select to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- SELLER: can insert their own listing
create policy "listings: seller insert"
  on public.listings for insert to authenticated
  with check (
    (select auth.uid()) = seller_id
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role in ('seller', 'admin')
    )
  );

-- SELLER: can update their own DRAFT listing only
create policy "listings: seller update draft"
  on public.listings for update to authenticated
  using ( (select auth.uid()) = seller_id and status = 'draft' )
  with check ( (select auth.uid()) = seller_id and status in ('draft', 'pending') );

-- ASSESSOR + ADMIN: can update listing status (approve, reject, escalate from queue)
create policy "listings: admin update status"
  on public.listings for update to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  )
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- ADMIN: can update any listing
create policy "listings: admin update all"
  on public.listings for update to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  )
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- SELLER: can delete own draft listing
create policy "listings: seller delete draft"
  on public.listings for delete to authenticated
  using ( (select auth.uid()) = seller_id and status = 'draft' );

-- ============================================================
-- listing_images RLS Policies
-- ============================================================

create policy "listing_images: public read active"
  on public.listing_images for select to anon, authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.status = 'active'
    )
  );

create policy "listing_images: seller read own"
  on public.listing_images for select to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid())
    )
  );

create policy "listing_images: admin read all"
  on public.listing_images for select to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

create policy "listing_images: seller insert"
  on public.listing_images for insert to authenticated
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid())
    )
  );

create policy "listing_images: seller delete"
  on public.listing_images for delete to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid()) and l.status = 'draft'
    )
  );

-- ============================================================
-- listing_documents RLS Policies (Private legal files)
-- ============================================================

-- SELLER: read documents for own listings
create policy "listing_docs: seller read own"
  on public.listing_documents for select to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid())
    )
  );

-- ASSESSOR + ADMIN: read all documents to verify legal authenticity
create policy "listing_docs: admin read all"
  on public.listing_documents for select to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- SELLER: upload documents to own draft listing
create policy "listing_docs: seller insert"
  on public.listing_documents for insert to authenticated
  with check (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid()) and l.status = 'draft'
    )
  );

-- SELLER: delete documents from own draft listing
create policy "listing_docs: seller delete"
  on public.listing_documents for delete to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid()) and l.status = 'draft'
    )
  );

-- ASSESSOR + ADMIN: update document verification status
create policy "listing_docs: admin update status"
  on public.listing_documents for update to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  )
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- ============================================================
-- Triggers & Validation Enforcements
-- ============================================================

-- Auto-update updated_at for listings
create trigger listings_updated_at
  before update on public.listings
  for each row execute function public.set_updated_at();

-- Enforcement Trigger: Minimum 3 photos + 1 ownership title doc required before submitting to 'pending'
create or replace function public.validate_listing_submission()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  img_count integer;
  doc_count integer;
begin
  -- Only validate when transitioning from draft -> pending
  if old.status = 'draft' and new.status = 'pending' then
    -- 1. Check >= 3 images
    select count(*) into img_count
    from public.listing_images
    where listing_id = new.id;

    if img_count < 3 then
      raise exception 'A minimum of 3 vehicle photos are required to submit for assessment (Found: %)', img_count;
    end if;

    -- 2. Check >= 1 ownership_title document (RC / Title / V5C)
    select count(*) into doc_count
    from public.listing_documents
    where listing_id = new.id and document_type = 'ownership_title';

    if doc_count < 1 then
      raise exception 'Mandatory proof of ownership document (RC / Title / V5C) must be uploaded before submission.';
    end if;
  end if;

  return new;
end;
$$;

create trigger trg_validate_listing_submission
  before update on public.listings
  for each row execute function public.validate_listing_submission();

-- ============================================================
-- Indexes
-- ============================================================
create index idx_listings_status       on public.listings (status);
create index idx_listings_seller_id    on public.listings (seller_id);
create index idx_listings_make_model   on public.listings (make, model);
create index idx_listings_fuel_trans   on public.listings (fuel_type, transmission);
create index idx_listing_images_listing on public.listing_images (listing_id);
create index idx_listing_images_primary on public.listing_images (listing_id) where is_primary = true;
create index idx_listing_docs_listing   on public.listing_documents (listing_id);
create index idx_listing_docs_type      on public.listing_documents (document_type);

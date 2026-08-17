-- ============================================================
-- Migration 007: verification_telemetry_and_catalog
-- Production-hardened per Supabase + Postgres best practices:
--   • RLS with (select auth.uid()) subquery (security-rls-performance)
--   • TO authenticated / TO anon (never deprecated auth.role())
--   • UPDATE policies enforce both USING + WITH CHECK (IDOR defence)
--   • GIN jsonb_path_ops index (2-3x smaller for containment @> queries)
--   • FK index on all referencing columns (schema-foreign-key-indexes)
--   • security invoker + set search_path = '' (security-privileges)
-- ============================================================

-- ------------------------------------------------------------
-- 1. EXTEND LISTINGS TABLE WITH TELEMETRY & VERIFICATION
-- ------------------------------------------------------------
alter table public.listings
  add column if not exists verification_status text not null default 'unverified'
    constraint listings_verif_status_check
    check (verification_status in ('unverified', 'verified_clean', 'flagged_discrepancy', 'admin_override')),
  add column if not exists vlm_report jsonb not null default '{}'::jsonb,
  add column if not exists ocr_odometer_km integer
    constraint listings_odometer_check check (ocr_odometer_km is null or ocr_odometer_km >= 0),
  add column if not exists plate_number text;

comment on column public.listings.verification_status is 'unverified | verified_clean | flagged_discrepancy | admin_override';
comment on column public.listings.vlm_report         is 'Raw structured payload from one-shot multimodal VLM verification.';
comment on column public.listings.ocr_odometer_km    is 'Telemetry extracted from dashboard cluster photo via VLM (km).';
comment on column public.listings.plate_number       is 'Normalized registration plate string extracted from vehicle photos.';

-- High-performance partial and expression indexes
create index if not exists idx_listings_verif_status
  on public.listings (verification_status);

create index if not exists idx_listings_plate_number
  on public.listings (plate_number)
  where plate_number is not null;

-- JSONB Path Ops GIN Index (2-3x smaller & faster for @> containment queries)
create index if not exists idx_listings_vlm_report_gin
  on public.listings using gin (vlm_report jsonb_path_ops);

-- Expression index for VLM verdict equality lookups
create index if not exists idx_listings_vlm_verdict
  on public.listings (((vlm_report->>'verdict')));


-- ------------------------------------------------------------
-- 2. VEHICLE CATALOG TABLE (CASCADING DROPDOWNS / AUTOFILL)
-- ------------------------------------------------------------
create table if not exists public.vehicle_catalog (
  id           uuid        primary key default gen_random_uuid(),
  make         text        not null,
  model        text        not null,
  variant      text        not null,
  year_start   smallint    not null
                 constraint catalog_year_start_check check (year_start >= 1990 and year_start <= 2100),
  year_end     smallint    not null
                 constraint catalog_year_end_check check (year_end >= year_start and year_end <= 2100),
  body_type    text        not null
                 constraint catalog_body_check check (body_type in ('hatchback','sedan','suv','muv','coupe','convertible','wagon','other')),
  fuel_type    text        not null
                 constraint catalog_fuel_check check (fuel_type in ('petrol','diesel','electric','cng','hybrid')),
  transmission text        not null
                 constraint catalog_trans_check check (transmission in ('manual','automatic')),
  features     text[]      not null default '{}',
  colors       text[]      not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint unique_make_model_variant_years unique (make, model, variant, year_start, year_end)
);

comment on table  public.vehicle_catalog        is 'Standardized vehicle taxonomy for intake auto-completion and cascading dropdowns.';
comment on column public.vehicle_catalog.make   is 'Manufacturer name, e.g. Maruti Suzuki, Hyundai.';
comment on column public.vehicle_catalog.model  is 'Model name, e.g. Swift, i20.';
comment on column public.vehicle_catalog.variant is 'Trim level, e.g. ZXi AMT, Asta 1.0 Turbo DCT.';

-- Optimised composite index for hierarchical lookup (make → model → variant)
create index if not exists idx_catalog_hierarchy
  on public.vehicle_catalog (make, model, variant);

create index if not exists idx_catalog_features_gin
  on public.vehicle_catalog using gin (features);

-- Enable RLS
alter table public.vehicle_catalog enable row level security;

-- Explicit Data API Grants
grant select on public.vehicle_catalog to anon, authenticated;
grant insert, update, delete on public.vehicle_catalog to authenticated;

-- RLS Policies
-- Public Read: every visitor can read catalog taxonomy
create policy "catalog: public read"
  on public.vehicle_catalog
  for select
  to anon, authenticated
  using ( true );

-- Admin Write: only platform admins may modify reference data
create policy "catalog: admin insert"
  on public.vehicle_catalog
  for insert
  to authenticated
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

create policy "catalog: admin update"
  on public.vehicle_catalog
  for update
  to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  )
  with check (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

create policy "catalog: admin delete"
  on public.vehicle_catalog
  for delete
  to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- Trigger: auto-update updated_at with search_path hardening
create or replace function public.set_catalog_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_vehicle_catalog_updated_at
  before update on public.vehicle_catalog
  for each row execute function public.set_catalog_updated_at();


-- ------------------------------------------------------------
-- 3. SEED DATA — Representative Indian passenger cars
--    make + model in Title Case (catalogue convention).
--    rc_extractor normalizes OCR output to .title() before lookup,
--    so HYUNDAI / hyundai / Hyundai all resolve correctly.
--    Expand progressively as researcher delivers batches.
-- ------------------------------------------------------------
insert into public.vehicle_catalog (make, model, variant, year_start, year_end, body_type, fuel_type, transmission, features, colors)
values
  -- Maruti Suzuki Swift
  ('Maruti Suzuki', 'Swift', 'LXi', 2018, 2024, 'hatchback', 'petrol', 'manual', '{}', '{"Pearl Arctic White","Magma Grey","Lucent Orange"}'),
  ('Maruti Suzuki', 'Swift', 'VXi', 2018, 2024, 'hatchback', 'petrol', 'manual', '{"Rear Parking Sensor","USB Charger"}', '{"Pearl Arctic White","Magma Grey","Midnight Black"}'),
  ('Maruti Suzuki', 'Swift', 'ZXi AMT', 2018, 2024, 'hatchback', 'petrol', 'automatic', '{"Cruise Control","Rear Parking Camera","Apple CarPlay"}', '{"Pearl Arctic White","Magma Grey"}'),
  -- Hyundai i20
  ('Hyundai', 'i20', 'Era 1.2 MT', 2020, 2024, 'hatchback', 'petrol', 'manual', '{}', '{"Polar White","Titan Grey","Fiery Red"}'),
  ('Hyundai', 'i20', 'Sportz 1.2 MT', 2020, 2024, 'hatchback', 'petrol', 'manual', '{"Rear AC Vents","Wireless Charger","Apple CarPlay"}', '{"Polar White","Titan Grey","Starry Night"}'),
  ('Hyundai', 'i20', 'Asta 1.0 Turbo DCT', 2020, 2024, 'hatchback', 'petrol', 'automatic', '{"Sunroof","Bose Sound System","Cruise Control","Apple CarPlay"}', '{"Polar White","Titan Grey","Fiery Red"}'),
  -- Tata Nexon
  ('Tata', 'Nexon', 'XE 1.2T Petrol', 2019, 2024, 'suv', 'petrol', 'manual', '{}', '{"Calgary White","Foliage Green","Flame Red"}'),
  ('Tata', 'Nexon', 'XZ+ 1.5 Diesel', 2019, 2024, 'suv', 'diesel', 'manual', '{"Sunroof","Harman Kardon Audio","Apple CarPlay"}', '{"Calgary White","Foliage Green"}'),
  ('Tata', 'Nexon', 'XZ+ DCA Petrol', 2021, 2024, 'suv', 'petrol', 'automatic', '{"Sunroof","Harman Kardon Audio","Cruise Control"}', '{"Calgary White","Foliage Green","Flame Red"}'),
  -- Hyundai Creta
  ('Hyundai', 'Creta', 'E 1.5 Petrol MT', 2020, 2024, 'suv', 'petrol', 'manual', '{}', '{"Atlas White","Typhoon Silver","Galaxy Grey"}'),
  ('Hyundai', 'Creta', 'SX 1.5 Diesel MT', 2020, 2024, 'suv', 'diesel', 'manual', '{"Bose Sound System","Sunroof","Apple CarPlay"}', '{"Atlas White","Typhoon Silver"}'),
  ('Hyundai', 'Creta', 'SX(O) 1.5 Diesel AT', 2020, 2024, 'suv', 'diesel', 'automatic', '{"Sunroof","Ventilated Seats","360 Camera","ADAS"}', '{"Atlas White","Typhoon Silver","Crimson Red"}'),
  -- Honda City
  ('Honda', 'City', 'V 1.5 MT', 2020, 2024, 'sedan', 'petrol', 'manual', '{"Lane Watch Camera","Apple CarPlay"}', '{"Lunar Silver","Platinum White Pearl","Golden Brown"}'),
  ('Honda', 'City', 'ZX CVT', 2020, 2024, 'sedan', 'petrol', 'automatic', '{"Sunroof","Honda Sensing ADAS","Wireless Charger","Apple CarPlay"}', '{"Lunar Silver","Platinum White Pearl"}'),
  -- Maruti Suzuki Baleno
  ('Maruti Suzuki', 'Baleno', 'Sigma', 2022, 2024, 'hatchback', 'petrol', 'manual', '{}', '{"Splendid Silver","Grandeur Grey","Opulent Red"}'),
  ('Maruti Suzuki', 'Baleno', 'Alpha MT', 2022, 2024, 'hatchback', 'petrol', 'manual', '{"Heads-Up Display","360 Camera","Apple CarPlay","Sunroof"}', '{"Splendid Silver","Grandeur Grey","Sizzling Red"}'),
  ('Maruti Suzuki', 'Baleno', 'Alpha AMT', 2022, 2024, 'hatchback', 'petrol', 'automatic', '{"Heads-Up Display","360 Camera","Apple CarPlay","Sunroof"}', '{"Splendid Silver","Grandeur Grey"}'),
  -- Kia Seltos
  ('Kia', 'Seltos', 'HTE 1.5 MT', 2019, 2024, 'suv', 'petrol', 'manual', '{}', '{"Aurora Black Pearl","Glacier White Pearl","Gravity Grey"}'),
  ('Kia', 'Seltos', 'GTX+ 1.4 DCT', 2019, 2024, 'suv', 'petrol', 'automatic', '{"Panoramic Sunroof","Bose Sound System","360 Camera","ADAS"}', '{"Aurora Black Pearl","Imperial Blue"}'),
  -- Toyota Innova Crysta
  ('Toyota', 'Innova Crysta', 'GX MT 8-Seater', 2016, 2024, 'muv', 'diesel', 'manual', '{"Captain Seats","Rear AC","USB Charger"}', '{"Super White","Silver Metallic","Bronze Mica"}'),
  ('Toyota', 'Innova Crysta', 'ZX AT 7-Seater', 2016, 2024, 'muv', 'diesel', 'automatic', '{"Captain Seats","360 Camera","JBL Audio","Ventilated Seats"}', '{"Super White","Silver Metallic"}')
on conflict (make, model, variant, year_start, year_end) do nothing;


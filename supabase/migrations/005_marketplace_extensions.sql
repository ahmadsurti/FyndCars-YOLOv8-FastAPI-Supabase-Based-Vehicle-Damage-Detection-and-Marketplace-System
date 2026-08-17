-- ============================================================
-- Migration 005: marketplace extensions
-- Favorites, Listing Analytics, Subscriptions (Platform Fees Only),
-- Seller Reviews & Ratings, Pro Search Alerts, and Features Tags.
-- ============================================================

-- ------------------------------------------------------------
-- 1. ADD EQUIPMENT / FEATURE TAGS TO LISTINGS
-- ------------------------------------------------------------
alter table public.listings
  add column if not exists features text[] not null default '{}';

comment on column public.listings.features is 'Equipment tags (e.g. Sunroof, 360 Camera, Touchscreen, Cruise Control).';

-- GIN index for ultra-fast array subset filtering (e.g. features @> ARRAY['Sunroof'])
create index if not exists idx_listings_features
  on public.listings using gin (features);

-- ------------------------------------------------------------
-- 2. SAVED LISTINGS (FAVORITES / BOOKMARKS)
-- ------------------------------------------------------------
create table if not exists public.saved_listings (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  listing_id  uuid not null references public.listings (id) on delete cascade,
  created_at  timestamptz not null default now(),
  constraint unique_user_listing_favorite unique (user_id, listing_id)
);

comment on table public.saved_listings is 'Buyer vehicle bookmarks / favorites.';

alter table public.saved_listings enable row level security;
grant select, insert, delete on public.saved_listings to authenticated;

-- Users can read their own saved listings
create policy "saved_listings: own read"
  on public.saved_listings for select to authenticated
  using ( (select auth.uid()) = user_id );

-- Users can save listings for themselves
create policy "saved_listings: own insert"
  on public.saved_listings for insert to authenticated
  with check ( (select auth.uid()) = user_id );

-- Users can remove their own saved listings
create policy "saved_listings: own delete"
  on public.saved_listings for delete to authenticated
  using ( (select auth.uid()) = user_id );

create index if not exists idx_saved_listings_user on public.saved_listings (user_id);
create index if not exists idx_saved_listings_listing on public.saved_listings (listing_id);

-- ------------------------------------------------------------
-- 3. LISTING VIEWS & ANALYTICS
-- ------------------------------------------------------------
create table if not exists public.listing_views (
  id          uuid primary key default gen_random_uuid(),
  listing_id  uuid not null references public.listings (id) on delete cascade,
  viewer_id   uuid references public.profiles (id) on delete set null,
  ip_hash     text,
  viewed_at   timestamptz not null default now()
);

comment on table public.listing_views is 'Vehicle impressions & view counters for seller analytics and admin KPIs.';

alter table public.listing_views enable row level security;
grant select, insert on public.listing_views to anon, authenticated;

-- Public & Authenticated can log an impression/view
create policy "listing_views: insert all"
  on public.listing_views for insert to anon, authenticated
  with check ( true );

-- Sellers can see view analytics for their own listings
create policy "listing_views: seller read own"
  on public.listing_views for select to authenticated
  using (
    exists (
      select 1 from public.listings l
      where l.id = listing_id and l.seller_id = (select auth.uid())
    )
  );

-- Admins can see all analytics
create policy "listing_views: admin read all"
  on public.listing_views for select to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

create index if not exists idx_listing_views_listing on public.listing_views (listing_id);
create index if not exists idx_listing_views_time on public.listing_views (viewed_at desc);

-- ------------------------------------------------------------
-- 4. USER SUBSCRIPTIONS & PLATFORM PAYWALLS
-- (Strictly Platform Fees / Listing Quotas — ZERO Car Funds)
-- ------------------------------------------------------------
create table if not exists public.user_subscriptions (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.profiles (id) on delete cascade,
  plan_type           text not null
                        constraint sub_plan_check
                        check (plan_type in ('seller_unlimited_listings', 'pro_buyer_alerts', 'ai_inspection_bundle')),
  status              text not null default 'pending'
                        constraint sub_status_check
                        check (status in ('pending', 'active', 'expired', 'canceled')),
  razorpay_order_id   text,
  razorpay_payment_id text,
  amount_paid         numeric(10, 2) not null,
  currency            text not null default 'INR',
  valid_until         timestamptz not null,
  created_at          timestamptz not null default now()
);

comment on table public.user_subscriptions is 'Platform subscription tier & listing quota unlocks (Razorpay). Strictly platform fees.';

alter table public.user_subscriptions enable row level security;
grant select, insert, update on public.user_subscriptions to authenticated;

-- Users can read their own subscriptions
create policy "subscriptions: own read"
  on public.user_subscriptions for select to authenticated
  using ( (select auth.uid()) = user_id );

-- Admins can read all subscriptions
create policy "subscriptions: admin read all"
  on public.user_subscriptions for select to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

-- Users can insert subscription orders for themselves
create policy "subscriptions: own insert"
  on public.user_subscriptions for insert to authenticated
  with check ( (select auth.uid()) = user_id );

create index if not exists idx_subs_user on public.user_subscriptions (user_id);
create index if not exists idx_subs_status on public.user_subscriptions (status);

-- ------------------------------------------------------------
-- 5. SELLER REVIEWS & RATINGS (Post-Sale Verified Feedback)
-- ------------------------------------------------------------
create table if not exists public.seller_reviews (
  id          uuid primary key default gen_random_uuid(),
  seller_id   uuid not null references public.profiles (id) on delete cascade,
  buyer_id    uuid not null references public.profiles (id) on delete cascade,
  listing_id  uuid not null references public.listings (id) on delete cascade,
  rating      smallint not null
                constraint review_rating_check check (rating >= 1 and rating <= 5),
  comment     text,
  created_at  timestamptz not null default now(),
  constraint unique_buyer_deal_review unique (buyer_id, listing_id),
  -- Prevent seller from rating themselves
  constraint check_no_self_review check (seller_id <> buyer_id)
);

comment on table public.seller_reviews is 'Verified buyer reviews on sellers linked to closed vehicle deals.';

alter table public.seller_reviews enable row level security;
grant select, insert on public.seller_reviews to authenticated;
grant select on public.seller_reviews to anon; -- Public trust ratings

-- Anyone (including anon) can read seller reviews to build trust
create policy "seller_reviews: public read"
  on public.seller_reviews for select to anon, authenticated
  using ( true );

-- Buyers can insert review only on sold listings
create policy "seller_reviews: buyer insert"
  on public.seller_reviews for insert to authenticated
  with check (
    (select auth.uid()) = buyer_id
    and exists (
      select 1 from public.listings l
      where l.id = listing_id
        and l.seller_id = seller_id
        and l.status = 'sold'
    )
  );

create index if not exists idx_reviews_seller on public.seller_reviews (seller_id);
create index if not exists idx_reviews_listing on public.seller_reviews (listing_id);

-- ------------------------------------------------------------
-- 6. PRO SEARCH ALERTS
-- ------------------------------------------------------------
create table if not exists public.search_alerts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles (id) on delete cascade,
  make        text,
  model       text,
  max_price   numeric(12, 2),
  min_year    smallint,
  city        text,
  is_active   boolean not null default true,
  created_at  timestamptz not null default now()
);

comment on table public.search_alerts is 'Pro buyer automated inventory alerts. Match engine notifies buyer on matching listing.';

alter table public.search_alerts enable row level security;
grant select, insert, update, delete on public.search_alerts to authenticated;

-- Users can manage their own search alerts
create policy "search_alerts: own read"
  on public.search_alerts for select to authenticated
  using ( (select auth.uid()) = user_id );

create policy "search_alerts: own insert"
  on public.search_alerts for insert to authenticated
  with check ( (select auth.uid()) = user_id );

create policy "search_alerts: own update"
  on public.search_alerts for update to authenticated
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );

create policy "search_alerts: own delete"
  on public.search_alerts for delete to authenticated
  using ( (select auth.uid()) = user_id );

create index if not exists idx_search_alerts_user on public.search_alerts (user_id);
create index if not exists idx_search_alerts_active on public.search_alerts (is_active) where is_active = true;

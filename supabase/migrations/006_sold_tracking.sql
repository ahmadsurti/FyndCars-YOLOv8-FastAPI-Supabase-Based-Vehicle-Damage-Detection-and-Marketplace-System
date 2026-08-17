-- ============================================================
-- Migration 006: sold tracking
-- Closes the lifecycle gap: active → sold had no endpoint or
-- buyer record. buyer_id + sold_at make seller_reviews
-- verifiable post-sale ("who actually bought this car?").
-- ============================================================

alter table public.listings
  add column if not exists buyer_id uuid references public.profiles (id) on delete set null,
  add column if not exists sold_at  timestamptz;

comment on column public.listings.buyer_id is 'Buyer recorded when the seller marks the listing sold. Enables verified post-sale reviews.';
comment on column public.listings.sold_at is 'Timestamp when the deal was closed (status → sold).';

create index if not exists idx_listings_buyer_id on public.listings (buyer_id);
create index if not exists idx_listings_sold_at  on public.listings (sold_at desc);

-- The recorded buyer may read their purchased listing (any status,
-- e.g. to revisit it after it leaves the public feed).
create policy "listings: buyer read purchased"
  on public.listings for select to authenticated
  using ( (select auth.uid()) = buyer_id );

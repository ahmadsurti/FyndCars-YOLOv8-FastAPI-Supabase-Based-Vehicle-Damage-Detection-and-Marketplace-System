-- ============================================================
-- Migration 004: Supabase Storage buckets + storage policies + messages
-- Three buckets:
--   car-images       → original seller uploads (private)
--   annotated-images → YOLOv8 bounding-box overlays (private)
--   car-documents    → legal proof files: RC, Title, Insurance, PUC, NOC (private)
-- ============================================================

-- ============================================================
-- 1. car-images bucket policies
-- ============================================================

create policy "car-images: seller upload"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'car-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role in ('seller', 'admin')
    )
  );

create policy "car-images: seller read own"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'car-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "car-images: admin read all"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'car-images'
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

create policy "car-images: seller update own"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'car-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  )
  with check (
    bucket_id = 'car-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "car-images: seller delete own"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'car-images'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

-- ============================================================
-- 2. annotated-images bucket policies
-- ============================================================

create policy "annotated-images: admin read"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'annotated-images'
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

create policy "annotated-images: seller read own listing"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'annotated-images'
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role in ('seller', 'admin')
    )
  );

-- ============================================================
-- 3. car-documents bucket policies (Confidential Legal Proofs)
-- ============================================================

create policy "car-docs: seller upload"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'car-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role in ('seller', 'admin')
    )
  );

create policy "car-docs: seller read own"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'car-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "car-docs: admin read all"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'car-documents'
    and exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid()) and p.role = 'admin'
    )
  );

create policy "car-docs: seller update own"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'car-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  )
  with check (
    bucket_id = 'car-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "car-docs: seller delete own"
  on storage.objects for delete to authenticated
  using (
    bucket_id = 'car-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

-- ============================================================
-- 4. messages table (buyer ↔ seller)
-- ============================================================

create table if not exists public.messages (
  id           uuid primary key default gen_random_uuid(),
  listing_id   uuid not null references public.listings (id) on delete cascade,
  sender_id    uuid not null references public.profiles (id) on delete cascade,
  receiver_id  uuid not null references public.profiles (id) on delete cascade,
  body         text not null,
  read         boolean not null default false,
  created_at   timestamptz not null default now()
);

comment on table public.messages is 'Direct messages between buyers and sellers about a specific listing.';

alter table public.messages enable row level security;
grant select, insert, update on public.messages to authenticated;

create policy "messages: participant read"
  on public.messages for select to authenticated
  using (
    (select auth.uid()) = sender_id or (select auth.uid()) = receiver_id
  );

create policy "messages: sender insert"
  on public.messages for insert to authenticated
  with check (
    (select auth.uid()) = sender_id and sender_id <> receiver_id
  );

create policy "messages: receiver mark read"
  on public.messages for update to authenticated
  using  ( (select auth.uid()) = receiver_id )
  with check ( (select auth.uid()) = receiver_id );

create index if not exists idx_messages_listing  on public.messages (listing_id);
create index if not exists idx_messages_sender   on public.messages (sender_id);
create index if not exists idx_messages_receiver on public.messages (receiver_id);
create index if not exists idx_messages_created  on public.messages (created_at desc);
create index if not exists idx_messages_unread   on public.messages (receiver_id, listing_id) where read = false;

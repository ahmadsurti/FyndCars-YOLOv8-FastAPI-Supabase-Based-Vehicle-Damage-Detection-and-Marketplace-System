-- ============================================================
-- Migration 001: profiles
-- Extends Supabase auth.users with role-based access
-- ============================================================

-- profiles table
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  role        text not null default 'buyer'
                constraint profiles_role_check
                check (role in ('admin', 'seller', 'buyer')),
  region      text not null default 'India'
                constraint profiles_region_check
                check (region in ('India', 'USA', 'UK', 'EU')),
  full_name   text,
  phone       text,
  avatar_url  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.profiles is 'Extended user profile with fynd(cars) role and region assignment.';
comment on column public.profiles.role is 'admin | seller | buyer';
comment on column public.profiles.region is 'India | USA | UK | EU';

-- Enable RLS
alter table public.profiles enable row level security;

-- Grant access to Data API roles
grant select, insert, update on public.profiles to authenticated;

-- ---- RLS Policies ----

-- Users can read their own profile
create policy "profiles: own read"
  on public.profiles
  for select
  to authenticated
  using ( (select auth.uid()) = id );

-- Admins can read all profiles
create policy "profiles: admin read all"
  on public.profiles
  for select
  to authenticated
  using (
    exists (
      select 1 from public.profiles p
      where p.id = (select auth.uid())
        and p.role = 'admin'
    )
  );

-- Users can insert their own profile (called on signup)
create policy "profiles: own insert"
  on public.profiles
  for insert
  to authenticated
  with check ( (select auth.uid()) = id );

-- Users can update their own profile (but NOT their role — role is admin-only)
create policy "profiles: own update"
  on public.profiles
  for update
  to authenticated
  using  ( (select auth.uid()) = id )
  with check (
    (select auth.uid()) = id
    -- Prevent self-role escalation: role must match current DB value
    and role = (select role from public.profiles where id = (select auth.uid()))
  );

-- Admins can update any profile (including role changes)
create policy "profiles: admin update all"
  on public.profiles
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

-- ---- Trigger: auto-create profile on auth.users insert ----
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  default_role text;
  default_region text;
begin
  -- Extract and validate role from metadata if provided, otherwise default to 'buyer'
  default_role := coalesce(new.raw_user_meta_data->>'role', new.raw_app_meta_data->>'role', 'buyer');
  if default_role not in ('admin', 'seller', 'buyer') then
    default_role := 'buyer';
  end if;

  -- Extract and validate region from metadata if provided, otherwise default to 'India'
  default_region := coalesce(new.raw_user_meta_data->>'region', new.raw_app_meta_data->>'region', 'India');
  if default_region not in ('India', 'USA', 'UK', 'EU') then
    default_region := 'India';
  end if;

  insert into public.profiles (id, full_name, phone, role, region)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    coalesce(new.raw_user_meta_data->>'phone', ''),
    default_role,
    default_region
  )
  on conflict (id) do update
  set
    full_name = coalesce(excluded.full_name, profiles.full_name),
    phone = coalesce(excluded.phone, profiles.phone),
    region = coalesce(excluded.region, profiles.region);

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---- Trigger: auto-update updated_at ----
create or replace function public.set_updated_at()
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

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- ---- Index ----
create index idx_profiles_role on public.profiles (role);

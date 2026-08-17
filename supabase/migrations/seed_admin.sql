-- ============================================================
-- fynd(cars) — Admin User Seed
-- Run AFTER you create your admin account via Supabase Auth
-- (sign up normally via Supabase dashboard or Auth UI)
--
-- Then run this SQL in Supabase SQL Editor to promote yourself to admin.
-- Replace the email below with your actual admin email.
-- ============================================================

-- Step 1: Set app_metadata.role = 'admin' (this is what the JWT will carry)
-- Run this in Supabase SQL Editor → it calls the admin auth API internally
update auth.users
set raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
where email = 'YOUR_ADMIN_EMAIL@example.com';

-- Step 2: Update the profiles table to match
update public.profiles
set role = 'admin'
where id = (
  select id from auth.users where email = 'YOUR_ADMIN_EMAIL@example.com'
);

-- Verify:
select u.email, u.raw_app_meta_data->>'role' as app_role, p.role as profile_role
from auth.users u
join public.profiles p on p.id = u.id
where u.email = 'YOUR_ADMIN_EMAIL@example.com';

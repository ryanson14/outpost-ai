-- Run in Supabase SQL Editor AFTER page_snapshots exists.
-- Enables RLS: blocks anon/authenticated PostgREST access by default.
-- Your Python pipeline uses service_role, which bypasses RLS (server-side only).

alter table public.page_snapshots enable row level security;

-- Explicit deny for anon (defense in depth if anon key is ever exposed)
create policy "page_snapshots_deny_anon_select"
  on public.page_snapshots
  for select
  to anon
  using (false);

create policy "page_snapshots_deny_anon_insert"
  on public.page_snapshots
  for insert
  to anon
  with check (false);

create policy "page_snapshots_deny_anon_update"
  on public.page_snapshots
  for update
  to anon
  using (false)
  with check (false);

create policy "page_snapshots_deny_anon_delete"
  on public.page_snapshots
  for delete
  to anon
  using (false);

-- competitors table (run supabase/competitors.sql first)
alter table public.competitors enable row level security;

create policy "competitors_deny_anon_select"
  on public.competitors for select to anon using (false);

create policy "competitors_deny_anon_insert"
  on public.competitors for insert to anon with check (false);

create policy "competitors_deny_anon_update"
  on public.competitors for update to anon using (false) with check (false);

create policy "competitors_deny_anon_delete"
  on public.competitors for delete to anon using (false);

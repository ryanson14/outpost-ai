-- Step 7: Multi-tenant workspace migration.
-- Run once in Supabase SQL Editor after the existing schema files have been applied.
--
-- This keeps v1 simple: one owner user gets one workspace. Team invites can come later.

begin;

create extension if not exists pgcrypto;

create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'Outpost Workspace',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'owner' check (role in ('owner', 'admin', 'member')),
  created_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

-- Backfill one workspace per existing settings row. Existing workspace IDs intentionally
-- match user IDs so the migration is easy to reason about and debug.
insert into public.workspaces (id, name)
select
  ws.user_id,
  coalesce(nullif(trim(ws.product_name), ''), 'Outpost Workspace')
from public.workspace_settings ws
on conflict (id) do nothing;

insert into public.workspace_members (workspace_id, user_id, role)
select
  ws.user_id,
  ws.user_id,
  'owner'
from public.workspace_settings ws
on conflict (workspace_id, user_id) do nothing;

-- workspace_settings becomes workspace-scoped. Keep user_id for now as the owner/backfill
-- link while the Python code moves from user_id lookups to workspace_id lookups.
alter table public.workspace_settings
  add column if not exists workspace_id uuid;

update public.workspace_settings
set workspace_id = user_id
where workspace_id is null;

alter table public.workspace_settings
  alter column workspace_id set not null;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conrelid = 'public.workspace_settings'::regclass
      and conname = 'workspace_settings_pkey'
  ) then
    alter table public.workspace_settings drop constraint workspace_settings_pkey;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.workspace_settings'::regclass
      and conname = 'workspace_settings_workspace_id_pkey'
  ) then
    alter table public.workspace_settings
      add constraint workspace_settings_workspace_id_pkey primary key (workspace_id);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.workspace_settings'::regclass
      and conname = 'workspace_settings_workspace_id_fkey'
  ) then
    alter table public.workspace_settings
      add constraint workspace_settings_workspace_id_fkey
      foreign key (workspace_id) references public.workspaces(id) on delete cascade;
  end if;
end $$;

create unique index if not exists workspace_settings_user_id_idx
  on public.workspace_settings (user_id);

-- competitors was global. Duplicate the existing global list into every workspace,
-- then switch the primary key to (workspace_id, name).
create temp table _outpost_existing_competitors as
select name, changelog_url, pricing_url, active, created_at
from public.competitors;

alter table public.competitors
  add column if not exists workspace_id uuid;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conrelid = 'public.competitors'::regclass
      and conname = 'competitors_pkey'
  ) then
    alter table public.competitors drop constraint competitors_pkey;
  end if;
end $$;

delete from public.competitors;

insert into public.competitors (
  workspace_id,
  name,
  changelog_url,
  pricing_url,
  active,
  created_at
)
select
  w.id,
  c.name,
  c.changelog_url,
  c.pricing_url,
  c.active,
  c.created_at
from public.workspaces w
cross join _outpost_existing_competitors c
on conflict do nothing;

alter table public.competitors
  alter column workspace_id set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.competitors'::regclass
      and conname = 'competitors_workspace_id_fkey'
  ) then
    alter table public.competitors
      add constraint competitors_workspace_id_fkey
      foreign key (workspace_id) references public.workspaces(id) on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.competitors'::regclass
      and conname = 'competitors_workspace_id_name_pkey'
  ) then
    alter table public.competitors
      add constraint competitors_workspace_id_name_pkey primary key (workspace_id, name);
  end if;
end $$;

create index if not exists competitors_workspace_id_idx
  on public.competitors (workspace_id);

-- page_snapshots was also global. Duplicate existing hashes into each workspace so
-- today's dedupe state survives the tenant migration.
create temp table _outpost_existing_page_snapshots as
select competitor_name, page_type, content_hash, updated_at
from public.page_snapshots;

alter table public.page_snapshots
  add column if not exists workspace_id uuid;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conrelid = 'public.page_snapshots'::regclass
      and conname = 'page_snapshots_pkey'
  ) then
    alter table public.page_snapshots drop constraint page_snapshots_pkey;
  end if;
end $$;

delete from public.page_snapshots;

insert into public.page_snapshots (
  workspace_id,
  competitor_name,
  page_type,
  content_hash,
  updated_at
)
select
  w.id,
  s.competitor_name,
  s.page_type,
  s.content_hash,
  s.updated_at
from public.workspaces w
cross join _outpost_existing_page_snapshots s
on conflict do nothing;

alter table public.page_snapshots
  alter column workspace_id set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.page_snapshots'::regclass
      and conname = 'page_snapshots_workspace_id_fkey'
  ) then
    alter table public.page_snapshots
      add constraint page_snapshots_workspace_id_fkey
      foreign key (workspace_id) references public.workspaces(id) on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conrelid = 'public.page_snapshots'::regclass
      and conname = 'page_snapshots_workspace_competitor_page_pkey'
  ) then
    alter table public.page_snapshots
      add constraint page_snapshots_workspace_competitor_page_pkey
      primary key (workspace_id, competitor_name, page_type);
  end if;
end $$;

create index if not exists page_snapshots_workspace_id_updated_at_idx
  on public.page_snapshots (workspace_id, updated_at desc);

-- RLS: authenticated users can only access rows for workspaces they belong to.
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.workspace_settings enable row level security;
alter table public.competitors enable row level security;
alter table public.page_snapshots enable row level security;

drop policy if exists "workspace_settings_select_own" on public.workspace_settings;
drop policy if exists "workspace_settings_insert_own" on public.workspace_settings;
drop policy if exists "workspace_settings_update_own" on public.workspace_settings;
drop policy if exists "workspace_settings_delete_own" on public.workspace_settings;
drop policy if exists "workspace_settings_deny_anon" on public.workspace_settings;

drop policy if exists "competitors_deny_anon_select" on public.competitors;
drop policy if exists "competitors_deny_anon_insert" on public.competitors;
drop policy if exists "competitors_deny_anon_update" on public.competitors;
drop policy if exists "competitors_deny_anon_delete" on public.competitors;

drop policy if exists "page_snapshots_deny_anon_select" on public.page_snapshots;
drop policy if exists "page_snapshots_deny_anon_insert" on public.page_snapshots;
drop policy if exists "page_snapshots_deny_anon_update" on public.page_snapshots;
drop policy if exists "page_snapshots_deny_anon_delete" on public.page_snapshots;

create policy "workspaces_select_member"
  on public.workspaces for select to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspaces.id
        and wm.user_id = auth.uid()
    )
  );

create policy "workspace_members_select_own"
  on public.workspace_members for select to authenticated
  using (user_id = auth.uid());

create policy "workspace_settings_select_member"
  on public.workspace_settings for select to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspace_settings.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "workspace_settings_insert_owner"
  on public.workspace_settings for insert to authenticated
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspace_settings.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "workspace_settings_update_member"
  on public.workspace_settings for update to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspace_settings.workspace_id
        and wm.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspace_settings.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "workspace_settings_delete_owner"
  on public.workspace_settings for delete to authenticated
  using (
    user_id = auth.uid()
    and exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = workspace_settings.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "competitors_select_member"
  on public.competitors for select to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = competitors.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "competitors_insert_member"
  on public.competitors for insert to authenticated
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = competitors.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "competitors_update_member"
  on public.competitors for update to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = competitors.workspace_id
        and wm.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = competitors.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "competitors_delete_member"
  on public.competitors for delete to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = competitors.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "page_snapshots_select_member"
  on public.page_snapshots for select to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = page_snapshots.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "page_snapshots_insert_member"
  on public.page_snapshots for insert to authenticated
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = page_snapshots.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "page_snapshots_update_member"
  on public.page_snapshots for update to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = page_snapshots.workspace_id
        and wm.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = page_snapshots.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "page_snapshots_delete_member"
  on public.page_snapshots for delete to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = page_snapshots.workspace_id
        and wm.user_id = auth.uid()
    )
  );

commit;

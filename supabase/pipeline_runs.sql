-- Step 8: Track manual pipeline runs per workspace.
-- Run in Supabase SQL Editor after supabase/workspaces.sql.

create table if not exists public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued', 'running', 'succeeded', 'failed')),
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists pipeline_runs_workspace_created_at_idx
  on public.pipeline_runs (workspace_id, created_at desc);

alter table public.pipeline_runs enable row level security;

drop policy if exists "pipeline_runs_select_member" on public.pipeline_runs;
drop policy if exists "pipeline_runs_insert_member" on public.pipeline_runs;
drop policy if exists "pipeline_runs_update_member" on public.pipeline_runs;

create policy "pipeline_runs_select_member"
  on public.pipeline_runs for select to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = pipeline_runs.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "pipeline_runs_insert_member"
  on public.pipeline_runs for insert to authenticated
  with check (
    user_id = auth.uid()
    and exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = pipeline_runs.workspace_id
        and wm.user_id = auth.uid()
    )
  );

create policy "pipeline_runs_update_member"
  on public.pipeline_runs for update to authenticated
  using (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = pipeline_runs.workspace_id
        and wm.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.workspace_members wm
      where wm.workspace_id = pipeline_runs.workspace_id
        and wm.user_id = auth.uid()
    )
  );

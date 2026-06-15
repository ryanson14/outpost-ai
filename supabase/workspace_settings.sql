-- Run in Supabase SQL Editor (after auth is enabled on your project).
-- Per-user PM profile, Slack webhook, and backlog tickets for the web UI.

create table if not exists public.workspace_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  product_name text not null default '',
  product_description text not null default '',
  q3_goal text not null default '',
  roadmap_focus text not null default '',
  backlog_tickets jsonb not null default '[]'::jsonb,
  slack_webhook_url text,
  slack_team_id text,
  slack_team_name text,
  slack_channel_id text,
  slack_channel_name text,
  slack_connected_at timestamptz,
  threat_threshold int not null default 7 check (threat_threshold between 1 and 10),
  updated_at timestamptz not null default now()
);

alter table public.workspace_settings enable row level security;

-- Authenticated users can read/write only their own row (browser + anon key).
create policy "workspace_settings_select_own"
  on public.workspace_settings for select to authenticated
  using (auth.uid() = user_id);

create policy "workspace_settings_insert_own"
  on public.workspace_settings for insert to authenticated
  with check (auth.uid() = user_id);

create policy "workspace_settings_update_own"
  on public.workspace_settings for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "workspace_settings_delete_own"
  on public.workspace_settings for delete to authenticated
  using (auth.uid() = user_id);

-- Block anon direct access (defense in depth).
create policy "workspace_settings_deny_anon"
  on public.workspace_settings for all to anon
  using (false)
  with check (false);

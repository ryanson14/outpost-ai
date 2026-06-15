-- Run in Supabase SQL Editor (after workspace_settings exists).
-- Adds Slack OAuth metadata; webhook URL still stored in slack_webhook_url.

alter table public.workspace_settings
  add column if not exists slack_team_id text,
  add column if not exists slack_team_name text,
  add column if not exists slack_channel_id text,
  add column if not exists slack_channel_name text,
  add column if not exists slack_connected_at timestamptz;

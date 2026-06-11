-- Run in Supabase SQL Editor (after page_snapshots exists)

create table if not exists public.competitors (
  name text primary key,
  changelog_url text not null,
  pricing_url text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.competitors enable row level security;

-- Seed default competitors (safe to re-run)
insert into public.competitors (name, changelog_url, pricing_url, active)
values
  ('Linear', 'https://linear.app/changelog', 'https://linear.app/pricing', true),
  ('Jira', 'https://www.atlassian.com/software/jira/whats-new', 'https://www.atlassian.com/software/jira/pricing', true),
  ('Asana', 'https://asana.com/product/updates', 'https://asana.com/pricing', true)
on conflict (name) do nothing;

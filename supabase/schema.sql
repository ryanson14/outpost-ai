-- Run this in Supabase: SQL Editor → New query → Run

create table if not exists page_snapshots (
  competitor_name text not null,
  page_type text not null,
  content_hash text not null,
  updated_at timestamptz not null default now(),
  primary key (competitor_name, page_type)
);

-- Optional: index for debugging / audits
create index if not exists page_snapshots_updated_at_idx
  on page_snapshots (updated_at desc);

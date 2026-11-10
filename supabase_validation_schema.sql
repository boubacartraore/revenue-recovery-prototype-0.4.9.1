
create extension if not exists pgcrypto;
create table if not exists public.validation_submissions (
 submission_id uuid primary key default gen_random_uuid(),
 review_id uuid not null,
 submitted_at timestamptz not null default now(),
 prototype_version text not null,
 business_profile_id text not null,
 reviewer_role text,
 experience_band text,
 randomized_order jsonb not null,
 human_ranking_titles jsonb not null,
 human_ranking_ids jsonb not null,
 model_ranking_ids jsonb not null,
 model_confidence_top text,
 agreement_response text,
 override_top text,
 override_reason text,
 blind_comment text,
 post_model_comment text,
 synthetic_data_only boolean not null default true,
 created_at timestamptz not null default now()
);
alter table public.validation_submissions enable row level security;
revoke all on table public.validation_submissions from anon, authenticated;
grant insert on table public.validation_submissions to anon, authenticated;
create policy "validation_insert_only"
on public.validation_submissions
for insert to anon, authenticated
with check (prototype_version='0.4.9.1' and synthetic_data_only=true);
create index if not exists idx_validation_version on public.validation_submissions(prototype_version);
create index if not exists idx_validation_profile on public.validation_submissions(business_profile_id);

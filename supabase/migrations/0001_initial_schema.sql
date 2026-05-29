-- ============================================================================
-- SICA — Migración inicial
-- Crea el esquema base para pacientes, controles, RLS y storage policies.
--
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query → Run.
-- Idempotente: usa `if not exists` y `or replace` donde aplica.
--
-- Ver docs/decisions/0011-frontend-stack.md para el contexto de las decisiones
-- estructurales (Supabase como auth+db, JSONB para resumen_json, RLS por user_id).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Tablas
-- ---------------------------------------------------------------------------

create table if not exists public.pacientes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  nombre_completo text not null,
  dni text,
  hc_id text,
  fecha_nacimiento date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.controles (
  id uuid primary key default gen_random_uuid(),
  paciente_id uuid references public.pacientes(id) on delete cascade not null,
  user_id uuid references auth.users(id) on delete cascade not null,
  pdf_filename text not null,
  pdf_storage_path text,
  semanas_gestacion numeric,
  fecha_control date,
  resumen_json jsonb not null,
  extractor_version text,
  prompt_version text,
  provider_id text,
  confidence_score numeric,
  cost_usd numeric,
  latency_ms integer,
  trace_id text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Índices
-- ---------------------------------------------------------------------------

create index if not exists idx_pacientes_user_id on public.pacientes(user_id);
create index if not exists idx_pacientes_dni on public.pacientes(user_id, dni);
create index if not exists idx_controles_paciente_id on public.controles(paciente_id);
create index if not exists idx_controles_user_id on public.controles(user_id);
create index if not exists idx_controles_fecha on public.controles(fecha_control desc);

-- ---------------------------------------------------------------------------
-- 3. Trigger updated_at en pacientes
-- ---------------------------------------------------------------------------

create or replace function public.update_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_pacientes_updated_at on public.pacientes;
create trigger trg_pacientes_updated_at
  before update on public.pacientes
  for each row
  execute function public.update_updated_at();

-- ---------------------------------------------------------------------------
-- 4. Row Level Security
-- ---------------------------------------------------------------------------

alter table public.pacientes enable row level security;
alter table public.controles enable row level security;

drop policy if exists "users see own pacientes" on public.pacientes;
create policy "users see own pacientes"
  on public.pacientes
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "users see own controles" on public.controles;
create policy "users see own controles"
  on public.controles
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- 5. Storage bucket privado para PDFs
-- ---------------------------------------------------------------------------
--
-- Path convention: {user_id}/{paciente_id}/{control_id}.pdf
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public)
values ('pdfs', 'pdfs', false)
on conflict (id) do nothing;

drop policy if exists "users upload own pdfs" on storage.objects;
create policy "users upload own pdfs"
  on storage.objects
  for insert
  with check (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "users read own pdfs" on storage.objects;
create policy "users read own pdfs"
  on storage.objects
  for select
  using (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

drop policy if exists "users delete own pdfs" on storage.objects;
create policy "users delete own pdfs"
  on storage.objects
  for delete
  using (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

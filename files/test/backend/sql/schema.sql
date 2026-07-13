-- RAGnify Media — database schema (Postgres + pgvector, fully self-hosted)
--
-- Runs automatically on first container start when using docker-compose
-- (mounted into Postgres's /docker-entrypoint-initdb.d/). For a manual
-- setup, run this once against your database, e.g.:
--   psql "$DATABASE_URL" -f sql/schema.sql

create extension if not exists vector;
create extension if not exists pgcrypto; -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Users. This replaces a hosted auth provider — accounts, password hashes,
-- and email-verification codes all live in this one table. See
-- app/routers/auth.py and app/security.py for the logic.
-- ---------------------------------------------------------------------------
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null unique,
  password_hash text not null,
  verified boolean not null default false,
  verification_code text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Documents uploaded by a user
-- ---------------------------------------------------------------------------
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  name text not null,
  file_type text not null,
  char_count int not null default 0,
  chunk_count int not null default 0,
  created_at timestamptz not null default now()
);
create index if not exists documents_user_idx on documents(user_id);

-- ---------------------------------------------------------------------------
-- Chunks derived from documents. content_tsv powers the keyword/BM25-style
-- side of hybrid search via Postgres full-text search.
-- ---------------------------------------------------------------------------
create table if not exists chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  content_tsv tsvector generated always as (to_tsvector('english', content)) stored,
  created_at timestamptz not null default now()
);
create index if not exists chunks_tsv_idx on chunks using gin(content_tsv);
create index if not exists chunks_document_idx on chunks(document_id);
create index if not exists chunks_user_idx on chunks(user_id);

-- ---------------------------------------------------------------------------
-- Embeddings, one row per (chunk, embedding model). The `vector` column
-- has NO fixed dimension on purpose: the two Ollama models registered in
-- app/embeddings.py output different widths (all-minilm=384,
-- nomic-embed-text=768), and pgvector allows mixed-width columns as long
-- as you don't try to compare across widths (we never do — every query
-- filters to one model_name first). The tradeoff is no ANN index (ivfflat/
-- hnsw require a fixed width), so search is a sequential scan — completely
-- fine at personal/learning scale (milliseconds for thousands of rows).
-- If you outgrow this, pick one model and add a fixed-width column + index
-- for it specifically.
-- ---------------------------------------------------------------------------
create table if not exists chunk_embeddings (
  chunk_id uuid not null references chunks(id) on delete cascade,
  model_name text not null,
  embedding vector not null,
  primary key (chunk_id, model_name)
);

-- ---------------------------------------------------------------------------
-- Chat sessions & messages (feature: persistent chat history)
-- ---------------------------------------------------------------------------
create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null default 'New conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists chat_sessions_user_idx on chat_sessions(user_id);

create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  confidence text,
  created_at timestamptz not null default now()
);
create index if not exists chat_messages_session_idx on chat_messages(session_id);

-- ---------------------------------------------------------------------------
-- Per-user settings (embedding model choice, hybrid search balance, voice)
-- ---------------------------------------------------------------------------
create table if not exists user_settings (
  user_id uuid primary key references users(id) on delete cascade,
  embedding_model text not null default 'all-minilm',
  hybrid_weight float not null default 0.5,
  voice_enabled boolean not null default true
);

-- No row-level security here: there's no external auth provider setting
-- auth.uid() for Postgres to check. Every query in this app is filtered by
-- user_id at the application layer instead (see app/utils.py parse_uuid
-- and the `where user_id = $1` clause in every router query) — the
-- backend is the only thing with DB credentials, so that's sufficient for
-- a self-hosted, single-backend deployment.

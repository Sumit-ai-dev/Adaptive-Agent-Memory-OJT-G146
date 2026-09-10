-- ==============================================================================
-- Supabase PostgreSQL Schema for Adaptive AI Agent with Persistent Experience Memory
-- Group: G146 OJT Project
-- ==============================================================================

-- 1. Enable pgvector for semantic experience retrieval
create extension if not exists vector;

-- 2. Experiences Table (The Persistent Experience Store)
create table if not exists public.experiences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    task_domain text not null check (task_domain in ('research', 'coding', 'analysis', 'planning', 'general')),
    trigger_condition text not null,
    strategy_lesson text not null,
    trust_score numeric(4, 3) not null default 0.750 check (trust_score >= 0.0 and trust_score <= 1.0),
    uses_count integer not null default 0,
    successes_count integer not null default 0,
    failures_count integer not null default 0,
    status text not null default 'active' check (status in ('active', 'deprecated', 'candidate')),
    embedding vector(1536), -- Vector embeddings for semantic similarity search
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 3. Task Executions Table (Audit & Evaluation Log)
create table if not exists public.task_executions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    task_input text not null,
    task_domain text not null,
    memory_enabled boolean not null default true,
    status text not null default 'completed' check (status in ('pending', 'retrieving', 'reasoning', 'executing', 'reflecting', 'completed', 'failed')),
    final_output text,
    reflection_lesson text,
    tokens_used integer not null default 0,
    latency_ms integer not null default 0,
    outcome_quality text default 'positive' check (outcome_quality in ('positive', 'neutral', 'negative')),
    created_at timestamptz not null default now()
);

-- 4. Trust History Table (Reliability Tracking & Audit Trail)
create table if not exists public.trust_history (
    id uuid primary key default gen_random_uuid(),
    experience_id uuid references public.experiences(id) on delete cascade,
    execution_id text,
    old_trust numeric(4, 3) not null,
    new_trust numeric(4, 3) not null,
    delta numeric(4, 3) not null,
    reason text,
    created_at timestamptz not null default now()
);

-- 5. Execution Experiences Junction (M:N Relationship)
create table if not exists public.execution_experiences (
    execution_id uuid references public.task_executions(id) on delete cascade,
    experience_id uuid references public.experiences(id) on delete cascade,
    relevance_score numeric(4, 3) not null default 0.900,
    primary key (execution_id, experience_id)
);

-- ==============================================================================
-- Indexes for Sub-Millisecond Retrieval
-- ==============================================================================
create index if not exists idx_experiences_domain_status on public.experiences(task_domain, status);
create index if not exists idx_experiences_trust on public.experiences(trust_score desc);
create index if not exists idx_task_executions_user on public.task_executions(user_id, created_at desc);
create index if not exists idx_trust_history_exp on public.trust_history(experience_id, created_at desc);

-- HNSW Vector Index for Semantic Experience Search
create index if not exists idx_experiences_embedding on public.experiences
using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- ==============================================================================
-- Auto-update updated_at timestamp trigger
-- ==============================================================================
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create or replace trigger trg_experiences_updated_at
before update on public.experiences
for each row execute function public.handle_updated_at();

-- ==============================================================================
-- Row Level Security (RLS) Policies
-- ==============================================================================
alter table public.experiences enable row level security;
alter table public.task_executions enable row level security;
alter table public.trust_history enable row level security;
alter table public.execution_experiences enable row level security;

-- Experiences: Users can view active public experiences or their own private ones
create policy "Allow read active experiences"
on public.experiences for select
using (status = 'active' or auth.uid() = user_id or auth.uid() is null);

create policy "Allow user manage their experiences"
on public.experiences for all
using (auth.uid() = user_id or auth.uid() is null)
with check (auth.uid() = user_id or auth.uid() is null);

-- Executions: Users can manage their own executions
create policy "Allow user manage their executions"
on public.task_executions for all
using (auth.uid() = user_id or auth.uid() is null)
with check (auth.uid() = user_id or auth.uid() is null);

-- Trust History: Viewable by anyone with access to the experience
create policy "Allow read trust history"
on public.trust_history for select
using (true);

create policy "Allow insert trust history"
on public.trust_history for insert
with check (true);

-- ==============================================================================
-- Semantic Experience Search RPC Function (callable from Supabase Client / FastAPI)
-- ==============================================================================
create or replace function match_experiences(
    query_embedding vector(1536),
    match_threshold float default 0.70,
    match_count int default 3,
    filter_domain text default null
)
returns table (
    id uuid,
    task_domain text,
    trigger_condition text,
    strategy_lesson text,
    trust_score numeric,
    similarity float
)
language sql stable
as $$
    select
        e.id,
        e.task_domain,
        e.trigger_condition,
        e.strategy_lesson,
        e.trust_score,
        1 - (e.embedding <=> query_embedding) as similarity
    from public.experiences e
    where e.status = 'active'
      and (filter_domain is null or e.task_domain = filter_domain)
      and (1 - (e.embedding <=> query_embedding)) > match_threshold
    order by (1 - (e.embedding <=> query_embedding)) * (e.trust_score * 0.4 + 0.6) desc
    limit match_count;
$$;

-- Chat history for the IT KMITL chatbot (web/). Apply in the Supabase SQL editor.
-- Row Level Security: every user sees and edits only their own rows.

create table if not exists public.chats (
  id          uuid primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  title       text not null default '',
  scope       text[] not null default array['AIT','DSBA','BIT','IT'],
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists public.messages (
  id          uuid primary key,
  chat_id     uuid not null references public.chats (id) on delete cascade,
  user_id     uuid not null references auth.users (id) on delete cascade,
  role        text not null check (role in ('user', 'assistant')),
  content     text not null default '',
  sources     jsonb not null default '[]'::jsonb,
  status      text not null default 'done' check (status in ('streaming', 'done', 'stopped', 'error')),
  error       text,
  parent_id   uuid references public.messages (id) on delete set null,  -- reserved for branching
  created_at  timestamptz not null default now()
);

create index if not exists chats_user_updated_idx on public.chats (user_id, updated_at desc);
create index if not exists messages_chat_created_idx on public.messages (chat_id, created_at);

alter table public.chats enable row level security;
alter table public.messages enable row level security;

drop policy if exists "chats: owner" on public.chats;
create policy "chats: owner" on public.chats
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists "messages: owner" on public.messages;
create policy "messages: owner" on public.messages
  for all to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and exists (select 1 from public.chats c where c.id = chat_id and c.user_id = auth.uid())
  );

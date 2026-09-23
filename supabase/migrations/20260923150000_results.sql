-- One row per device, game and day: what a device scored. No logins, the device id is a random
-- UUID the page keeps in localStorage. Rows are write-only for the public key; the page reads
-- aggregates through daily_stats() only.

create table if not exists public.results (
  day        date        not null,
  game       text        not null,                 -- e.g. 'blind-f1', 'rankle-sports', 'sort-ski'
  device     uuid        not null,
  score      integer     not null check (score >= 0),
  max        integer     not null check (max >= score),
  created_at timestamptz not null default now(),
  primary key (day, game, device)
);

create index if not exists results_day_game on public.results (day, game);

alter table public.results enable row level security;

-- Anyone may record a result for today (give or take a day for time zones); nobody may read rows.
create policy "record a result" on public.results
  for insert to anon
  with check (day between current_date - 1 and current_date + 1 and game ~ '^(rankle|blind|sort)-[a-z0-9]+$');

-- Score histogram of one game and day: [{score, n}, ...]. Runs as owner, so no select on the table is needed.
create or replace function public.daily_stats(p_day date, p_game text)
returns table (score integer, n bigint)
language sql
security definer
set search_path = public
stable
as $$
  select score, count(*) as n
  from public.results
  where day = p_day and game = p_game
  group by score
  order by score
$$;

revoke all on function public.daily_stats(date, text) from public;
grant execute on function public.daily_stats(date, text) to anon;

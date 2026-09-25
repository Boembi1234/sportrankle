-- Seed results: a background job fills every daily game with roughly a thousand plausible results a day, so
-- nobody feels like the first to play. Seed rows carry a device id starting with "facade00-"; they are spread
-- over the day along an hourly activity curve (the job runs hourly and tops up to the target for the hour, so a
-- missed run is caught up), and seed rows older than two days are deleted. Real rows are never touched.

create extension if not exists pg_cron with schema pg_catalog;
grant usage on schema cron to postgres;

-- The games to seed and their score scale; keep in sync with the games of the site (build.py writes
-- supabase/seed_games.txt and warns when this list needs a new migration).
create table if not exists public.seed_games (
  game text primary key,
  kind text not null,
  max  integer not null
);
insert into public.seed_games (game, kind, max) values
  ('rankle-sports', 'rankle', 800), ('rankle-nfl', 'rankle', 800), ('rankle-nflplayers', 'rankle', 800),
  ('rankle-nflhof', 'rankle', 800), ('rankle-college', 'rankle', 800), ('rankle-cl', 'rankle', 800),
  ('rankle-athletes', 'rankle', 800),
  ('blind-sports', 'blind', 40), ('blind-nfl', 'blind', 40), ('blind-nflplayers', 'blind', 40),
  ('blind-nflhof', 'blind', 40), ('blind-college', 'blind', 40), ('blind-cl', 'blind', 40),
  ('sort-sports', 'sort', 40), ('sort-nfl', 'sort', 40), ('sort-nflplayers', 'sort', 40),
  ('sort-nflhof', 'sort', 40), ('sort-college', 'sort', 40), ('sort-cl', 'sort', 40),
  ('guess-records', 'guess', 100), ('guess-footrecords', 'guess', 100)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

-- One plausible score for a game kind. "bias" shifts the typical result a little per game (some topics are harder).
create or replace function public.seed_score(kind text, mx integer, bias numeric)
returns integer
language plpgsql
volatile
as $$
declare
  n numeric; u numeric; r numeric;
begin
  -- roughly normal(0, 1)
  n := (random() + random() + random() + random() + random() + random()
      + random() + random() + random() + random() + random() + random()) - 6;
  if kind = 'guess' then
    u := random();
    if u < 0.22 then r := random() * 0.35;          -- way off
    elsif u < 0.75 then r := 0.68 + 0.14 * n;       -- decent guess
    else r := 0.93 + 0.05 * n;                       -- nailed it
    end if;
  elsif kind = 'rankle' then
    r := 0.56 + bias + 0.15 * n;
  else
    r := 0.52 + bias + 0.20 * n;                     -- blind ranking, sort it
  end if;
  return greatest(0, least(mx, round(mx * r)::integer));
end
$$;

create or replace function public.seed_results()
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  -- share of a day's players per UTC hour (peak in the European evening, quiet at night)
  hourw numeric[] := array[0.030, 0.020, 0.012, 0.008, 0.006, 0.008, 0.014, 0.024, 0.036, 0.044, 0.048, 0.050,
                           0.052, 0.050, 0.048, 0.048, 0.052, 0.060, 0.068, 0.072, 0.066, 0.054, 0.040, 0.030];
  total numeric; cum numeric := 0;
  h integer := extract(hour from (now() at time zone 'utc'))::integer;
  d date := (now() at time zone 'utc')::date;
  g record; daily integer; target integer; have integer; bias numeric;
begin
  select sum(x) into total from unnest(hourw) x;
  for i in 1..(h + 1) loop
    cum := cum + hourw[i];
  end loop;
  for g in select * from seed_games loop
    daily := 900 + abs(hashtext(g.game || d::text)) % 250;            -- 900 to 1150 players per game and day
    bias := ((abs(hashtext(g.game)) % 11) - 5) / 100.0;                 -- -0.05 to +0.05
    target := floor(daily * cum / total);
    select count(*) into have from results where day = d and game = g.game and device::text like 'facade00-%';
    if have < target then
      insert into results (day, game, device, score, max)
      select d, g.game, overlay(gen_random_uuid()::text placing 'facade00' from 1 for 8)::uuid,
             seed_score(g.kind, g.max, bias), g.max
      from generate_series(1, target - have);
    end if;
  end loop;
  delete from results where device::text like 'facade00-%' and day < d - 1;
end
$$;

revoke execute on function public.seed_results() from public, anon, authenticated;
revoke execute on function public.seed_score(text, integer, numeric) from public, anon, authenticated;

-- every hour at :07 (pg_cron runs in UTC)
select cron.schedule('seed-results', '7 * * * *', 'select public.seed_results()');

-- fill today right away
select public.seed_results();

-- New topics without a migration. The insert policy accepts any topic of the known game types, and the seed job
-- seeds every game in seed_games plus any other game that real players played in the last 14 days, its score
-- shape taken from the game type in the key and its max from the real rows. seed_games stays as the list of games
-- that are always seeded (and may override kind and max). A new game *type* still needs a migration: this policy
-- and seed_score() have to know it. Runs whether or not *_guesstimate_results.sql ran before it.

drop policy if exists "record a result" on public.results;
create policy "record a result" on public.results
  for insert to anon
  with check (day between current_date - 1 and current_date + 1
              and game ~ '^(rankle|blind|sort|guess|guesstimate)-[a-z0-9]+$');

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
  elsif kind = 'estimate' then
    r := 0.47 + 0.16 * n;                            -- around the answer, a little more often too low
  elsif kind = 'rankle' then
    r := 0.56 + bias + 0.15 * n;
  else
    r := 0.52 + bias + 0.20 * n;                     -- blind ranking, sort it
  end if;
  return greatest(0, least(mx, round(mx * r)::integer));
end
$$;
revoke execute on function public.seed_score(text, integer, numeric) from public, anon, authenticated;

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
  for g in
    select s.game, s.kind, s.max from seed_games s
    union all
    -- games real players found that seed_games does not list; at most 50, so made-up keys cannot flood the table
    select a.game,
           case split_part(a.game, '-', 1) when 'rankle' then 'rankle' when 'guess' then 'guess'
                                           when 'guesstimate' then 'estimate' else 'blind' end,
           a.max
    from (select r.game, max(r.max) as max, count(distinct r.device) as n
          from results r
          where r.device::text not like 'facade00-%' and r.day >= d - 14 and r.max between 1 and 1000
          group by r.game
          order by n desc, r.game
          limit 50) a
    where not exists (select 1 from seed_games s where s.game = a.game)
  loop
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

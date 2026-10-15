-- Guesstimate stores where the guess lies relative to the answer, on a log scale from 0 (ten times too low) over 50
-- (exact) to 100 (ten times too high), under one game key for all questions, "guesstimate-all". Its results screen
-- shows that spread with the axis in the units of the question at hand. The insert policy has to accept the key, and
-- the seed job fills it with guesses spread around the answer (a new seed kind, "estimate").
drop policy if exists "record a result" on public.results;
create policy "record a result" on public.results
  for insert to anon
  with check (day between current_date - 1 and current_date + 1
              and game ~ '^((rankle|blind|sort|guess)-[a-z0-9]+|guesstimate-all)$');

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

insert into public.seed_games (game, kind, max) values
  ('guesstimate-all', 'estimate', 100)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

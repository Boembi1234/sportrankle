-- Guesstimate stores its score (0-100, from how many times off the guess is) under one game key for all questions,
-- "guesstimate-all", so its results screen can show the same comparison as the other games. The insert policy has to
-- accept that key, and the seed job fills it like Guess the Record.
drop policy if exists "record a result" on public.results;
create policy "record a result" on public.results
  for insert to anon
  with check (day between current_date - 1 and current_date + 1
              and game ~ '^((rankle|blind|sort|guess)-[a-z0-9]+|guesstimate-all)$');

insert into public.seed_games (game, kind, max) values
  ('guesstimate-all', 'guess', 100)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

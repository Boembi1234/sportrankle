-- Hockey records (Hockey): seed results for its Guess the Record game, like the other topics (see *_seed_results.sql).
insert into public.seed_games (game, kind, max) values
  ('guess-hockeyrecords', 'guess', 100)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

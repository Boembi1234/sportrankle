-- NHL players (Hockey): seed results for its three games, like the other topics (see *_seed_results.sql).
insert into public.seed_games (game, kind, max) values
  ('rankle-nhlplayers', 'rankle', 800), ('blind-nhlplayers', 'blind', 40), ('sort-nhlplayers', 'sort', 40)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

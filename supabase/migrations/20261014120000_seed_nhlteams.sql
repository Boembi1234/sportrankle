-- NHL teams (Ice hockey): seed results for its three daily games, like the other topics (see *_seed_results.sql).
insert into public.seed_games (game, kind, max) values
  ('rankle-nhlteams', 'rankle', 800), ('blind-nhlteams', 'blind', 40), ('sort-nhlteams', 'sort', 40)
on conflict (game) do update set kind = excluded.kind, max = excluded.max;

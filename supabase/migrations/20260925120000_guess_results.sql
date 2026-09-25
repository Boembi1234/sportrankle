-- Guess the record stores its score (0-100) like the other games; the insert policy has to accept its game key.
drop policy if exists "record a result" on public.results;
create policy "record a result" on public.results
  for insert to anon
  with check (day between current_date - 1 and current_date + 1 and game ~ '^(rankle|blind|sort|guess)-[a-z0-9]+$');

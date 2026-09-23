# Sportrankle

Daily sports ranking puzzles, live at <https://sportrankle.netlify.app>.

Three games, five pools (team sports, F1 circuits, NFL teams, alpine skiers, Champions League players), one attempt per game and day. Every player gets the same cards; the daily draw is seeded by the date in the browser, so the site is a single static page with no backend.

| Game | Idea |
|---|---|
| **Rankle** | 8 categories, 8 items arriving one by one. Put each item in the category where it ranks highest among the whole pool. Each category can be used once. |
| **Blind ranking** | One attribute, 8 items arriving one by one. Place each on spot 1–8 without knowing what comes next. |
| **Sort it** | One attribute, all 8 items in view. Swap them into the right order, then reveal. |
| **Ringer** | Party game on one phone (3–12 players, not daily): everyone sees the same item from a pool except the ringer(s), who only learn the pool. Hints go round, the group votes, then the reveal. |

## How it is built

```
Mannschaftssportarten_20x15.xlsx ─┐
F1-Strecken_20x15.xlsx            ├─ build.py ─► sportrankle.html (dev copy)
NFL_Teams_Rankle_32x15.xlsx       │             dist/index.html  (deployed)
Ski_Alpin_Rankle_40x15.xlsx      ─┘             dist/img/        (photos)
template.html  (all HTML, CSS and JS)
photos/<pool>/ (own photos)   covers/ (tile pictures)
```

`build.py` reads each spreadsheet, computes the ranks from the values, translates names and categories to English, resizes pictures and writes the page with the data embedded. `template.html` is the whole app; `__DATA__` and `__KINDS__` are replaced at build time.

```sh
pip install -r requirements.txt
python build.py            # writes sportrankle.html, dist/
```

Open `sportrankle.html` in a browser (or `dist/index.html`). No server needed. The build log lists each pool with its item, category and photo counts and warns about anything it could not match.

## Spreadsheet format

Each pool is one workbook with three sheets:

1. **Values** – row 1 headers, column A the item name (German), then one column per category. Optional `Bild-URL` / `Bildquelle` columns give a photo URL and its credit page.
2. **Ränge** – ignored; ranks are recomputed from the values so the sheet can be saved without cached formulas.
3. **Kategorien** – `#`, `Kategorie`, `Einheit`, `Rang 1 =` (direction, e.g. `meiste`, `frühestes`, `nördlichstes`). Rows whose `#` is a number are used.

Values may be numbers or dates. Ties share a rank; empty cells get no rank and score 0 in Rankle.

**Wide format** (used by the Champions League players): one sheet, one row per item, the stats in named columns, rank columns optional (they are ignored and recomputed). The `GAMES` entry sets `"format": "wide"`, the name column, which columns become categories (with English name, unit, format and direction), optional `"sub"` columns shown under the name, and an optional `"filter"` column/value to keep a subset of rows.

## Adding a pool

1. Put the workbook next to the others.
2. Add an entry to `GAMES` in `build.py`: file pattern, tab name, noun/plural, a card word, optionally `"english": True` (names already English) and `"short": "last" | "surname"` (what goes on the title cards).
3. Add the category names and units to `CATS_EN`, item names to `NAMES_EN` unless English, new directions to `DIR_EN` (and to `LOW_FIRST` if the smallest value wins), new units to `UNIT_FMT` if they need a special format.
4. Run the build; it warns about anything untranslated.
5. Add the pool's game keys to `ORDER` in `template.html` so "Next game" cycles through it.

## Photos

Own photos go into `photos/<pool>/<item name>.jpg` (see `photos/README.txt`); the build resizes them into `dist/img/` and serves them as files. A `credits.txt` next to them turns each photo into a link to its source. Photos from spreadsheet URLs are downloaded once into `img-cache/` and embedded.

## Online results (optional)

There are no logins. When a game ends, the page records `day, game, score, max` under a random device id kept in `localStorage`, then shows how the score compares with everyone else's that day ("Better than 73 % of today's 1,204 players"). The schema and policies are in `supabase/migrations/`: the public key can only insert one row per device, game and day and call `daily_stats()`, which returns a score histogram — individual rows are never readable from the browser.

The build enables it when `supabase/anon.key` exists (the project's public "anon" key, one line). Without the file the page runs exactly the same, minus that one line on the results screen. To use your own project: `npx supabase link --project-ref <ref>`, `npx supabase db push`, then save the anon key to `supabase/anon.key` and rebuild.

## Deploying

The site is a Netlify project: `netlify deploy --prod --dir dist` after a build. Only maintainers with access to the Netlify site can deploy; contributions go through pull requests.

## Contributing

- Data fixes and new categories: edit the spreadsheet, run the build, check the warnings, open a PR describing the source of the numbers.
- Page changes: edit `template.html` (never the built files), run the build, test the finished states on desktop and phone widths (the results screens are the busiest).
- New pools or games: open an issue first so the daily-draw seeds and the `ORDER` list stay consistent.

`DESIGN.md` (German) describes the visual language: flip cards on rings, one accent colour, no scrolling on the play screen.

# Guesstimate questions

The questions come from `Guesstimate_Fragen*.xlsx` in the project folder (German, sheets "Fragen" and "Quellen", see
its sheet "Hinweise"). The site shows them in English: `guesstimate/en.json` holds the English texts per question id
(`question`, `context`, `unit`, `referencePeriod`, `explanation`, `introduction`, `steps`) and the worked calculation
shown under "How to get there": `calc` = {"rows": [{"label": "Matchdays", "v": 34}, {"label": "Matches per matchday", "op": "×", "v": 9}, …], "result": 459}
(the first row is the start value, every further row applies its operation `×`, `÷`, `+` or `−` in order). Numbers, answer type,
sources and difficulty always come from the Excel. A question without an entry in `en.json` is shown in German and
the build lists it, so a new row in the Excel needs its English text added there. Visitors who pick German see the
Excel's own texts.

Questions can also be written directly as JSON in `questions.json` (format below); both are used together.

`questions.json` holds extra questions written as JSON: a list, one object per question. `python3 build.py` checks every
question and leaves out (with a message) any that is incomplete. The game draws a random question from all of them
(no sport to pick, no repeat until all were played); with none at all it shows a "questions on their way" page.

`demo.json` holds three made-up demo questions for testing. They are only built in when the environment variable
`GUESSTIMATE_DEMO=1` is set (the local dev server `tools/dev.py` sets it), are not marked in the game and never
reach the live site. Don't put real questions there.

## One question

```json
{
  "id": "nhl-pucks-season",
  "sportCategory": "hockey",
  "question": "How many pucks are used in a full NHL regular season?",
  "context": "Count every puck that is put into play, including warm-ups.",
  "answer": 30000,
  "unit": "pucks",
  "answerType": "sourced",
  "referencePeriod": "2024/25 season",
  "explanation": "Short text shown after the guess: where the number comes from and why it is that size.",
  "napkinMath": {
    "introduction": "Where could you start? With the number of games.",
    "steps": [
      {"label": "Games", "assumption": "32 teams, 82 games each, two teams per game", "calculation": "32 × 82 ÷ 2", "result": "1,312"},
      {"label": "Pucks per game", "assumption": "about a dozen frozen pucks per game", "result": "≈ 12"},
      {"label": "Season", "calculation": "1,312 × 12", "result": "≈ 16,000"}
    ],
    "estimatedAnswer": 16000
  },
  "sources": [
    {"title": "Article title", "url": "https://example.com/article", "publisher": "Publisher", "date": "2025"}
  ],
  "difficulty": "medium",
  "i18n": {"de": {"question": "Wie viele Pucks …?", "context": "…", "explanation": "…", "unit": "Pucks"}}
}
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique, lowercase with dashes. Used in share links (`#guesstimate/q/<id>`), so don't change it later. |
| `sportCategory` | yes | Not shown in the game for now (it draws from all questions), kept for sorting later. A sport key from `SPORTS` in `build.py`: `mixed`, `soccer`, `hockey`, `basketball`, `football`, `baseball`, `tennis`, `motorsport`, `winter`. |
| `question` | yes | The question as shown. |
| `context` | no | Season, region or given assumptions. Not shown in the game for now. |
| `answer` | yes | A plain number above 0 (no units, no thousands separators): `30000`, `46.8`. |
| `unit` | yes | Shown inside the input box and after the numbers: `pucks`, `litres`, `km`, `years`. For a time use `min:s`, `h:min` or `h:min:s`: the game shows one box per part (like Guess the Record) and `answer` / `estimatedAnswer` are then given in **seconds** (e.g. 1 h 59 min = `7140`). |
| `answerType` | yes | `sourced` (a documented number, needs `sources`), `calculated` (worked out from documented numbers, shown as "Calculated") or `estimate` (shown as "Model estimate"). In the Excel: belegt / berechnet / Modellschätzung. |
| `referencePeriod` | no | E.g. `2024/25 season` or `2025`. |
| `explanation` | yes | Short text after the guess. |
| `napkinMath.introduction` | yes | One sentence: where to start. |
| `napkinMath.steps` | yes | 3 to 5 steps; each needs `label`, and can have `assumption`, `calculation` and `result` (free text). |
| `napkinMath.estimatedAnswer` | yes | The rough result of the steps (a number above 0). It may differ from `answer`. |
| `sources` | for `sourced` | Each with `title` and `url` (http/https), optional `publisher` and `date`. |
| `difficulty` | no | `easy`, `medium` or `hard`; shown as a chip. |
| `i18n` | no | Translations per language (`de`, `fr`, `es`, `it`) of `question`, `context`, `explanation`, `unit`, `referencePeriod`. The site is English; these are used when a visitor picks that language. |

Scoring: factor = max(guess / answer, answer / guess); 1× is perfect.

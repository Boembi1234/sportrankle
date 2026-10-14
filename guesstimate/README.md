# Guesstimate questions

`questions.json` holds the real questions: a JSON list, one object per question. `python3 build.py` checks every
question and leaves out (with a message) any that is incomplete. The game draws a random question from all of them
(no sport to pick, no repeat until all were played); with none at all it shows a "questions on their way" page.

`demo.json` holds three made-up demo questions for testing. They are only built in when the environment variable
`GUESSTIMATE_DEMO=1` is set (the local dev server `tools/dev.py` sets it), start with "DEMO:" and never
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
| `context` | no | Season, region or given assumptions, shown under the question. |
| `answer` | yes | A plain number above 0 (no units, no thousands separators): `30000`, `46.8`. |
| `unit` | yes | Shown next to the input and the numbers: `pucks`, `litres`, `km`, `years`. |
| `answerType` | yes | `sourced` (a documented number, needs `sources`) or `estimate` (shown as "Model estimate"). |
| `referencePeriod` | no | E.g. `2024/25 season` or `2025`. |
| `explanation` | yes | Short text after the guess. |
| `napkinMath.introduction` | yes | One sentence: where to start. |
| `napkinMath.steps` | yes | 3 to 5 steps; each needs `label`, and can have `assumption`, `calculation` and `result` (free text). |
| `napkinMath.estimatedAnswer` | yes | The rough result of the steps (a number above 0). It may differ from `answer`. |
| `sources` | for `sourced` | Each with `title` and `url` (http/https), optional `publisher` and `date`. |
| `difficulty` | no | `easy`, `medium` or `hard`; shown as a chip. |
| `i18n` | no | Translations per language (`de`, `fr`, `es`, `it`) of `question`, `context`, `explanation`, `unit`, `referencePeriod`. The site is English; these are used when a visitor picks that language. |

Scoring: factor = max(guess / answer, answer / guess); 1× is perfect.

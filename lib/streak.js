// ---- Daily puzzles and streaks (lib/streak.js, inlined into the page by build.py; tests: tests/streak.test.cjs) ----
// Every game (a game type on a topic, e.g. "rankle-nfl") has one daily puzzle: the same cards for everyone, drawn from
// a seed made of the date and the game. Days are the player's local calendar days (YYYY-MM-DD), like the rest of the
// site; puzzle #1 is the game's start date. Pure functions only: the page loads and stores the state itself.

// Days since 1970 of a YYYY-MM-DD string, in whole days (UTC arithmetic, so daylight saving never shifts it)
function dayNum(day){ const [y, m, d] = day.split('-').map(Number); return Math.round(Date.UTC(y, m - 1, d) / 864e5); }
// Puzzle number of a day for a game that started on `start` (#1 on the start day; never below 1)
function puzzleNo(start, day){ return Math.max(1, dayNum(day) - dayNum(start) + 1); }

// A 32-bit seed from a string (FNV-1a) and a small seeded random generator (mulberry32) with Math.random's interface
function seedOf(s){ let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); } return h >>> 0; }
function seededRandom(seed){
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
const dailySeed = (game, day) => seedOf(`${day}|${game}`);

// Streak state of one game, or of "any game" (then n is a day number and score/max may be left out):
// {cur, best, last, played, hist: {n: [score, max]}}. Only finished daily puzzles are recorded.
const STREAK_KEEP = 30;   // puzzles of score history kept
function streakNew(){ return {cur: 0, best: 0, last: 0, played: 0, hist: {}}; }
function streakOk(s){ return s && typeof s === 'object' && Number.isFinite(s.cur) && Number.isFinite(s.last) ? s : streakNew(); }
// Record a finished puzzle n. A second result for the same puzzle changes nothing (the first one counts).
// Returns {state, changed}.
function streakRecord(state, n, score, max){
  const s = streakOk(state);
  if (s.last === n || n < s.last) return {state: s, changed: false};
  const cur = s.last === n - 1 ? s.cur + 1 : 1;
  const hist = {...s.hist};
  if (score != null) hist[n] = [score, max];
  for (const k of Object.keys(hist)) if (+k <= n - STREAK_KEEP) delete hist[k];
  return {state: {cur, best: Math.max(s.best, cur), last: n, played: s.played + 1, hist}, changed: true};
}
// The streak as shown on puzzle `today`: it holds while today's or yesterday's puzzle is done, a missed day ends it
function streakNow(state, today){ const s = streakOk(state); return s.last >= today - 1 ? s.cur : 0; }
const streakDone = (state, today) => streakOk(state).last === today;
const STREAK_MILESTONES = [3, 7, 30];

if (typeof module === 'object' && module.exports) module.exports = {dayNum, puzzleNo, seedOf, seededRandom, dailySeed, streakNew, streakRecord, streakNow, streakDone, STREAK_MILESTONES};

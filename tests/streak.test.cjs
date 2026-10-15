// Daily puzzles, streaks and challenge links: node --test tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const {dayNum, puzzleNo, seedOf, seededRandom, dailySeed, streakRecord, streakNow, streakDone} = require('../lib/streak.js');
const {gridRankle, gridSpots, gridBar, encodeChallenge, decodeChallenge, shareLines, shareUrl} = require('../lib/share.js');

// The page's day key: the local calendar day of a Date (copied from template.html)
const dayKey = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const START = '2026-10-15';
// Play one daily puzzle on a local date/time: what the page does in newRound() and saveHistory()
function play(states, game, when, score = 10, max = 40){
  const day = dayKey(when), n = puzzleNo(START, day);
  const g = streakRecord(states[game], n, score, max), all = streakRecord(states.all, dayNum(day));
  return {...states, [game]: g.state, all: all.state};
}

test('puzzle numbers count local days from the start date', () => {
  assert.equal(puzzleNo(START, '2026-10-15'), 1);
  assert.equal(puzzleNo(START, '2026-10-16'), 2);
  assert.equal(puzzleNo(START, '2026-11-14'), 31);
  assert.equal(puzzleNo(START, '2027-10-15'), 366);
  assert.equal(puzzleNo(START, '2026-10-01'), 1, 'a clock before the start never gives #0 or less');
  // daylight saving (Europe: 25 Oct 2026, US: 1 Nov 2026) does not skip or repeat a number
  assert.equal(puzzleNo(START, '2026-10-26') - puzzleNo(START, '2026-10-25'), 1);
  assert.equal(puzzleNo(START, '2026-11-02') - puzzleNo(START, '2026-11-01'), 1);
});

test('day rollover at local midnight', () => {
  assert.equal(puzzleNo(START, dayKey(new Date(2026, 9, 20, 23, 59, 59))), 6);
  assert.equal(puzzleNo(START, dayKey(new Date(2026, 9, 21, 0, 0, 0))), 7);
});

test('the daily seed is the same for everyone on a day and differs between games and days', () => {
  assert.equal(dailySeed('rankle-nfl', '2026-10-20'), dailySeed('rankle-nfl', '2026-10-20'));
  assert.notEqual(dailySeed('rankle-nfl', '2026-10-20'), dailySeed('rankle-nfl', '2026-10-21'));
  assert.notEqual(dailySeed('rankle-nfl', '2026-10-20'), dailySeed('blind-nfl', '2026-10-20'));
  const a = seededRandom(seedOf('x')), b = seededRandom(seedOf('x'));
  const xs = Array.from({length: 1000}, () => a());
  assert.deepEqual(xs.slice(0, 5), Array.from({length: 5}, () => b()));
  assert.ok(xs.every(x => x >= 0 && x < 1));
});

test('consecutive days build the streak', () => {
  let s = {};
  for (let d = 15; d <= 19; d++) s = play(s, 'rankle-nfl', new Date(2026, 9, d, 18));
  assert.equal(s['rankle-nfl'].cur, 5);
  assert.equal(s['rankle-nfl'].best, 5);
  assert.equal(s['rankle-nfl'].played, 5);
  assert.equal(s.all.cur, 5);
  assert.equal(streakNow(s['rankle-nfl'], puzzleNo(START, '2026-10-19')), 5, 'today done');
  assert.equal(streakNow(s['rankle-nfl'], puzzleNo(START, '2026-10-20')), 5, 'today still open: the streak holds');
});

test('a missed day ends the streak; the next play starts at 1 and best stays', () => {
  let s = {};
  for (const d of [15, 16, 17]) s = play(s, 'rankle-nfl', new Date(2026, 9, d, 12));
  assert.equal(streakNow(s['rankle-nfl'], puzzleNo(START, '2026-10-19')), 0, 'the 18th was missed: shown as 0');
  s = play(s, 'rankle-nfl', new Date(2026, 9, 19, 12));
  assert.equal(s['rankle-nfl'].cur, 1);
  assert.equal(s['rankle-nfl'].best, 3);
  assert.equal(s.all.cur, 1);
});

test('two games on the same day: each counts once, the any-game streak once', () => {
  let s = {};
  s = play(s, 'rankle-nfl', new Date(2026, 9, 15, 9));
  s = play(s, 'blind-cl', new Date(2026, 9, 15, 10));
  s = play(s, 'rankle-nfl', new Date(2026, 9, 15, 11), 39);   // a second result for the same puzzle is ignored
  assert.equal(s['rankle-nfl'].played, 1);
  assert.deepEqual(s['rankle-nfl'].hist[1], [10, 40], 'the first result counts');
  assert.equal(s.all.cur, 1);
  assert.equal(s.all.played, 1);
  s = play(s, 'blind-cl', new Date(2026, 9, 16, 9));
  assert.equal(s['blind-cl'].cur, 2);
  assert.equal(s['rankle-nfl'].cur, 1);
  assert.equal(streakNow(s['rankle-nfl'], 2), 1, 'rankle not played yet on the 16th: still holds');
  assert.equal(s.all.cur, 2);
  assert.ok(streakDone(s['blind-cl'], 2) && !streakDone(s['rankle-nfl'], 2));
});

test('a puzzle started before midnight and finished after it counts for its own day', () => {
  let s = {};
  s = play(s, 'sort-nfl', new Date(2026, 9, 15, 20));
  const started = new Date(2026, 9, 16, 23, 59);   // puzzle #2 dealt at 23:59 ...
  const n = puzzleNo(START, dayKey(started));
  s = {...s, 'sort-nfl': streakRecord(s['sort-nfl'], n, 20, 40).state};   // ... recorded at 00:01 under #2
  assert.equal(s['sort-nfl'].cur, 2);
  const after = puzzleNo(START, dayKey(new Date(2026, 9, 17, 0, 1)));
  assert.equal(after, 3);
  assert.ok(!streakDone(s['sort-nfl'], after), "the new day's puzzle is open again");
  assert.equal(streakNow(s['sort-nfl'], after), 2);
});

test('score history keeps the last 30 puzzles', () => {
  let s;
  for (let n = 1; n <= 40; n++) s = streakRecord(s, n, n, 40).state;
  assert.equal(Object.keys(s.hist).length, 30);
  assert.ok(!s.hist[10] && s.hist[11] && s.hist[40]);
  assert.equal(s.cur, 40);
});

test('broken stored state is treated as empty', () => {
  for (const bad of [null, undefined, 'x', 42, {cur: 'a'}]) assert.equal(streakRecord(bad, 3, 1, 40).state.cur, 1);
});

test('emoji rows never carry answers', () => {
  assert.equal(gridRankle(['ideal', '', 'worst', 'ideal', '', '', 'ideal', 'worst']), '🟩🟨🟥🟩🟨🟨🟩🟥');
  assert.equal(gridSpots([5, 3, 1, 0, 5, 5, 0, 3], 5), '🟩🟨🟨🟥🟩🟩🟥🟨');
  assert.equal(gridBar(100), '🟩🟩🟩🟩🟩');
  assert.equal(gridBar(73), '🟩🟩🟩🟩⬛');
  assert.equal(gridBar(50), '🟨🟨🟨⬛⬛');
  assert.equal(gridBar(25), '🟥⬛⬛⬛⬛');
  assert.equal(gridBar(5), '⬛⬛⬛⬛⬛');
  assert.equal(gridBar(0), '⬛⬛⬛⬛⬛');
});

test('challenge links round-trip and reject junk', () => {
  const daily = {kind: 'rankle', pool: 'nfl', puzzle: 42, score: 612, max: 800, seed: null};
  assert.deepEqual(decodeChallenge(encodeChallenge(daily)), daily);
  const practice = {kind: 'blind', pool: 'cl', puzzle: 0, score: 31, max: 40, seed: 4294967295};
  assert.deepEqual(decodeChallenge(encodeChallenge(practice)), practice);
  assert.match(encodeChallenge(daily), /^[A-Za-z0-9_-]+$/, 'base64url, no padding');
  for (const bad of ['', 'abc', '%%%', encodeChallenge({...daily, score: 900}), encodeChallenge({...daily, puzzle: 0}),
    Buffer.from('rankle.nfl.1.2.3.4.5').toString('base64url'), Buffer.from('Rankle.nfl.1.2.3').toString('base64url'),
    Buffer.from('rankle.nfl.1.-2.3').toString('base64url')]) assert.equal(decodeChallenge(bad), null, bad);
  assert.equal(decodeChallenge(encodeChallenge(daily), () => false), null, 'unknown game on this site');
});

test('share text', () => {
  const url = shareUrl('https://sport-minigames.com', 'rankle', 'rankle', 'abc');
  assert.equal(url, 'https://sport-minigames.com/rankle?c=abc&utm_source=share&utm_medium=rankle');
  assert.equal(shareLines({brand: 'Sport Minigames', puzzle: 42, game: 'Rankle', topic: 'NFL teams', grid: '🟩🟨', score: 612, max: 800, streak: 5, url}),
    `Sport Minigames #42 · Rankle · NFL teams\n🟩🟨\n612/800 🔥5\n${url}`);
  assert.equal(shareLines({brand: 'Sport Minigames', puzzle: 0, game: 'Sort It', topic: 'NFL teams', grid: '🟩', score: 20, max: 40, streak: 5, url}),
    `Sport Minigames · Sort It · NFL teams (practice)\n🟩\n20/40\n${url}`);
});

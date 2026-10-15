// ---- Share text and challenge links (lib/share.js, inlined into the page by build.py; tests: tests/streak.test.cjs) ----
// The emoji row shows how each pick went, never what the answer was. A challenge link carries game, topic, puzzle
// number and score (base64url, nothing personal); a practice round carries its seed instead of a puzzle number, so the
// friend gets the same cards.

const SQ = {ok: '\u{1F7E9}', near: '\u{1F7E8}', off: '\u{1F7E5}', none: '⬛'};
// Rankle: per category green = placed ideally, red = the card's worst category, yellow = anything in between
const gridRankle = rows => rows.map(r => r === 'ideal' ? SQ.ok : r === 'worst' ? SQ.off : SQ.near).join('');
// Blind ranking and Sort it: per spot green = exact (full points), red = no points, yellow = close (some points)
const gridSpots = (points, full) => points.map(p => p >= full ? SQ.ok : p > 0 ? SQ.near : SQ.off).join('');
// One guess scored 0-100 (Guess the record, Guesstimate): five squares, one per 20 points, coloured by the score
function gridBar(score){
  const n = Math.max(0, Math.min(5, Math.round(score / 20))), c = score >= 70 ? SQ.ok : score >= 40 ? SQ.near : SQ.off;
  return c.repeat(n) + SQ.none.repeat(5 - n);
}

const b64url = s => btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64url = s => atob(s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4));
// {kind, pool, puzzle, score, max, seed?} <-> "rankle.nfl.12.612.800" (+ ".<seed in base 36>" for practice rounds, puzzle 0)
function encodeChallenge(c){
  return b64url([c.kind, c.pool, c.puzzle, c.score, c.max].concat(c.seed != null ? [c.seed.toString(36)] : []).join('.'));
}
// The decoded challenge or null; `known(kind, pool)` says whether the game exists on this site
function decodeChallenge(s, known = () => true){
  try {
    const p = unb64url(String(s)).split('.');
    if (p.length < 5 || p.length > 6) return null;
    const [kind, pool] = p, [puzzle, score, max] = p.slice(2, 5).map(Number);
    const seed = p[5] != null ? parseInt(p[5], 36) : null;
    if (!/^[a-z]+$/.test(kind) || !/^[a-z0-9]+$/.test(pool) || !known(kind, pool)) return null;
    if (![puzzle, score, max].every(Number.isInteger) || puzzle < 0 || max <= 0 || score < 0 || score > max) return null;
    if (puzzle === 0 ? !(Number.isInteger(seed) && seed >= 0 && seed <= 0xFFFFFFFF) : seed != null) return null;
    return {kind, pool, puzzle, score, max, seed};
  } catch (e) { return null; }
}

// The share text: title line, emoji row, score (with the streak on a daily puzzle), link
function shareLines({brand, puzzle, game, topic, grid, score, max, streak, url}){
  return [`${brand}${puzzle ? ` #${puzzle}` : ''} · ${game} · ${topic}${puzzle ? '' : ' (practice)'}`,
    grid, `${score}/${max}${puzzle && streak > 0 ? ` \u{1F525}${streak}` : ''}`, url].filter(Boolean).join('\n');
}
// The shared link: the game's own page with the challenge and where it came from
const shareUrl = (site, page, kind, c) => `${site}/${page}?c=${c}&utm_source=share&utm_medium=${kind}`;

if (typeof module === 'object' && module.exports) module.exports = {gridRankle, gridSpots, gridBar, encodeChallenge, decodeChallenge, shareLines, shareUrl};

// ---- Analytics (lib/analytics.js, inlined into the page by build.py) ----
// Plausible: no cookies, no personal data, no banner. Everything goes through track() and trackPage(), so the provider
// can be swapped here. The domain comes from the build (PLAUSIBLE_DOMAIN); events are sent only on that domain, anywhere
// else (local files, localhost, deploy previews) they are logged to the console.
const ANALYTICS_DOMAIN = __PLAUSIBLE__;
const ANALYTICS_LIVE = !!ANALYTICS_DOMAIN && typeof location === 'object' && [ANALYTICS_DOMAIN, `www.${ANALYTICS_DOMAIN}`].includes(location.hostname);
if (ANALYTICS_LIVE) {
  window.plausible = window.plausible || function(){ (window.plausible.q = window.plausible.q || []).push(arguments); };
  const s = document.createElement('script');
  s.defer = true; s.src = 'https://plausible.io/js/script.manual.js'; s.dataset.domain = ANALYTICS_DOMAIN;
  document.head.append(s);
}

// Where the visit came from: utm_source / utm_medium / utm_campaign of the first page of the session, sent with every
// event so finished games can be split by platform (tiktok, instagram, share ...)
const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign'];
function utmProps(){
  let u = null;
  try { u = JSON.parse(sessionStorage.getItem('utm') || 'null'); } catch (e) {}
  if (!u) {
    const q = new URLSearchParams(location.search);
    u = Object.fromEntries(UTM_KEYS.filter(k => q.get(k)).map(k => [k, q.get(k).slice(0, 60)]));
    try { sessionStorage.setItem('utm', JSON.stringify(u)); } catch (e) {}
  }
  return u;
}
utmProps();   // capture on the first page of the session, before any link rewrites the address

function track(event, props = {}){
  const p = {...utmProps(), ...props};
  if (ANALYTICS_LIVE) { try { window.plausible(event, {props: p}); } catch (e) {} }
  else console.log('[track]', event, p);
}
// Pageviews: the app changes views through the hash, so each view is sent as a clean path (/rankle/nfl, /topic/nfl ...)
let lastPage = null;
function trackPage(path){
  if (path === lastPage) return;   // Play again re-renders the same view: not a new pageview
  lastPage = path;
  if (ANALYTICS_LIVE) { try { window.plausible('pageview', {u: location.origin + path, props: utmProps()}); } catch (e) {} }
  else console.log('[pageview]', path, utmProps());
}
function pagePath(hash){
  const h = hash.replace(/^#/, '');
  if (!h) return '/';
  let m;
  if ((m = h.match(/^(rankle|blind|sort|guess)-([a-z0-9]+)$/))) return `/${m[1]}/${m[2]}`;
  if ((m = h.match(/^(rankle|blind|sort|guess)\/([a-z]+)$/))) return `/${m[1]}/sport/${m[2]}`;
  if ((m = h.match(/^s\/([a-z]+)$/))) return `/sport/${m[1]}`;
  if ((m = h.match(/^t\/([a-z0-9]+)$/))) return `/topic/${m[1]}`;
  if (h.startsWith('guesstimate')) return '/guesstimate';
  if (h === 'ringer') return '/impostor';
  return `/${h.split(/[/?]/)[0]}`;
}

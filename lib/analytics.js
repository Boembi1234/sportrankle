// ---- Analytics (lib/analytics.js, inlined into the page by build.py) ----
// Umami Cloud: no cookies, no personal data, no banner. Everything goes through track() and trackPage(), so the provider
// can be swapped here. The build passes {id, domain} (UMAMI_WEBSITE_ID in build.py); data is sent only on that domain,
// anywhere else (local files, localhost, deploy previews) it is logged to the console.
const ANALYTICS = __ANALYTICS__;
const ANALYTICS_LIVE = !!ANALYTICS && typeof location === 'object' && [ANALYTICS.domain, `www.${ANALYTICS.domain}`].includes(location.hostname);
// Calls made before the tracker has loaded wait in a queue
const umamiQueue = [];
const umamiSend = fn => { if (window.umami) { try { fn(window.umami); } catch (e) {} } else umamiQueue.push(fn); };
if (ANALYTICS_LIVE) {
  const s = document.createElement('script');
  s.defer = true; s.src = 'https://cloud.umami.is/script.js';
  s.dataset.websiteId = ANALYTICS.id;
  s.dataset.autoTrack = 'false'; s.dataset.autoPageview = 'false';   // pageviews are sent by trackPage(), one per view of the app
  s.dataset.domains = ANALYTICS.domain;
  s.onload = () => umamiQueue.splice(0).forEach(umamiSend);
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
  if (ANALYTICS_LIVE) umamiSend(u => u.track(event, p));
  else console.log('[track]', event, p);
}
// Pageviews: the app changes views through the hash, so each view is sent as a clean path (/rankle/nfl, /topic/nfl ...)
let lastPage = null;
function trackPage(path){
  if (path === lastPage) return;   // Play again re-renders the same view: not a new pageview
  // The first pageview carries the session's UTM tags in its address, so Umami's own UTM report sees them
  const first = lastPage === null, utm = utmProps(), q = first && Object.keys(utm).length ? `?${new URLSearchParams(utm)}` : '';
  lastPage = path;
  if (ANALYTICS_LIVE) umamiSend(u => u.track(props => ({...props, url: path + q})));
  else console.log('[pageview]', path + q, utm);
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

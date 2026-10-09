// Offline shell only. Never intercept meeting APIs, tokens, or evidence exports.
const CACHE = 'effmeet2-participant-shell-v1';
const BASE = '/app/';
const SHELL = [BASE, BASE + 'index.html', BASE + 'styles.css', BASE + 'app.js', BASE + 'state.js', BASE + 'manifest.json', BASE + 'assets/brand.svg', BASE + 'assets/enter.svg', BASE + 'assets/link.svg', BASE + 'assets/mic-white.svg', BASE + 'assets/mic.svg', BASE + 'assets/user.svg', BASE + 'assets/icon-192.png', BASE + 'assets/icon-512.png', BASE + 'assets/apple-touch-icon.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('effmeet2-participant-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  // API calls and authenticated evidence always use the network and existing server checks.
  if (req.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  event.respondWith(fetch(req).then(response => {
    if (response.ok && response.type === 'basic' && new URL(response.url).pathname.startsWith(BASE)) {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE).then(cache => cache.put(req, copy)));
    }
    return response;
  }).catch(async () => {
    const cache = await caches.open(CACHE);
    return (await cache.match(req)) || (req.mode === 'navigate' ? await cache.match(BASE + 'index.html') : Response.error());
  }));
});

// Static shell cache only. Meeting data lives in localStorage, never in the cache.
const CACHE = 'effmeet2-local-shell-v2';
const BASE = new URL('./', self.location).pathname;
const SHELL = [
  BASE,
  BASE + 'index.html',
  BASE + 'styles.css',
  BASE + 'app.js',
  BASE + 'store.js',
  BASE + 'state.js',
  BASE + 'manifest.json',
  BASE + 'assets/brand.svg',
  BASE + 'assets/enter.svg',
  BASE + 'assets/link.svg',
  BASE + 'assets/mic-white.svg',
  BASE + 'assets/mic.svg',
  BASE + 'assets/user.svg',
  BASE + 'assets/robot.svg',
  BASE + 'assets/capture-sketch.svg',
  BASE + 'assets/icon-192.png',
  BASE + 'assets/icon-512.png',
  BASE + 'assets/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key.startsWith('effmeet2-local-shell-') && key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  event.respondWith(
    fetch(request)
      .then(response => {
        if (response.ok && response.type === 'basic') {
          const copy = response.clone();
          event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy)));
        }
        return response;
      })
      .catch(async () => {
        const cache = await caches.open(CACHE);
        return (await cache.match(request))
          || (request.mode === 'navigate' ? await cache.match(BASE + 'index.html') : Response.error());
      })
  );
});

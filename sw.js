const CACHE = 'lgu-v1';
const ASSETS = [
  '/LGU-CHATBOT/',
  '/LGU-CHATBOT/index.html',
  '/LGU-CHATBOT/login.html',
  '/LGU-CHATBOT/manifest.json',
  '/LGU-CHATBOT/icon-192x192.png',
  '/LGU-CHATBOT/icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});

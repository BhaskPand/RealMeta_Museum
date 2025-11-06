const CACHE_NAME = 'scanart-cache-v1';
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/css/style.css',
  '/js/main.js',
  '/demo_mode_images/test1.jpg',
  '/artworks.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE_ASSETS);
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(k => { if (k !== CACHE_NAME) return caches.delete(k); }));
    self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // Cache-first for static assets and images
  if (url.pathname.startsWith('/images/') || url.pathname.startsWith('/demo_mode_images/') || CORE_ASSETS.includes(url.pathname)) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(event.request);
      if (cached) return cached;
      try {
        const resp = await fetch(event.request);
        cache.put(event.request, resp.clone());
        return resp;
      } catch (e) {
        return cached || Response.error();
      }
    })());
    return;
  }

  // Network-first for analytics endpoints
  if (url.pathname === '/analytics' || url.pathname === '/sync-analytics') {
    event.respondWith((async () => {
      try { return await fetch(event.request); }
      catch (e) { return new Response(JSON.stringify({ status: 'queued' }), { headers: { 'Content-Type': 'application/json' } }); }
    })());
    return;
  }
});



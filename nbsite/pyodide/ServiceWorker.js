const cacheName = '{{ name }}';

const preCacheFiles = [{{ pre_cache }}];

const cachePatterns = [{{ cache_patterns }}];

self.addEventListener('install', (e) => {
  console.log('[Service Worker] Install');
  e.waitUntil((async () => {
    const cache = await caches.open(cacheName);
    console.log('[Service Worker] Caching ');
    await cache.addAll(preCacheFiles);
  })());
});

self.addEventListener('activate', (event) => {
  return self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  let enableCache = e.request.url.startsWith(self.location.origin);
  for (const pattern of cachePatterns) {
    if (e.request.url.startsWith(pattern)) {
      enableCache = true
      break
    }
  }
  if (enableCache) {
    e.respondWith((async () => {
      const r = await caches.match(e.request);
      console.log(`[Service Worker] Fetching resource: ${e.request.url}`);
      if (r) { return r; }
      const response = await fetch(e.request);
      const cache = await caches.open(cacheName);
      console.log(`[Service Worker] Caching new resource: ${e.request.url}`);
      cache.put(e.request, response.clone());
      return response;
    })());
  }
});

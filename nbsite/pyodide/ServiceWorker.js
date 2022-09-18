const appName = '{{ project }}'
const appCache = '{{ project }}-{{ version }}';

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
  event.waitUntil(
    caches.forEach((cache, cacheName) => {
      if (cacheName.startsWith(appName) && cacheName !== appCache) {
        return caches.delete(cacheName);
      }
    })
  );
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
      const cache = await caches.open(appCache);
      let response = await cache.match(e.request);
      console.log(`[Service Worker] Fetching resource: ${e.request.url}`);
      if (response) { return response; }
      response = await fetch(e.request);
      console.log(`[Service Worker] Caching new resource: ${e.request.url}`);
      cache.put(e.request, response.clone());
      return response;
    })());
  }
});

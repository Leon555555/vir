/* VR Training – Service Worker
   Seguro para Flask (Render)
   Cachea SOLO assets estáticos
*/

const CACHE_NAME = "vr-training-static-v1";

const STATIC_ASSETS = [
  "/static/css/styles_v2.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/logo_blanco_vr_training.png",
  "/static/manifest.webmanifest"
];

// Detecta navegación HTML
function isNavigation(request) {
  return (
    request.mode === "navigate" ||
    (request.headers.get("accept") || "").includes("text/html")
  );
}

// Detecta asset estático
function isStatic(url) {
  return url.pathname.startsWith("/static/");
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  if (url.origin !== self.location.origin) return;

  // HTML → siempre red
  if (isNavigation(req)) {
    event.respondWith(fetch(req));
    return;
  }

  // Assets → cache first
  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return res;
        });
      })
    );
  }
});

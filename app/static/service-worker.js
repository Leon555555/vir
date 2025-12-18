const CACHE_VERSION = "v2"; // <- subí esto cada vez que quieras forzar limpieza
const CACHE_NAME = `vr-training-static-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  "/static/css/styles_v2.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.webmanifest",
  "/static/logo_negro_vr_training.png",
];

function isNavigation(request) {
  return (
    request.mode === "navigate" ||
    (request.headers.get("accept") || "").includes("text/html")
  );
}

function isStatic(url) {
  return url.pathname.startsWith("/static/");
}

function isVideo(url) {
  return url.pathname.startsWith("/static/videos/");
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
      await Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  if (url.origin !== self.location.origin) return;

  // HTML / rutas dinámicas -> siempre red
  if (isNavigation(req)) {
    event.respondWith(fetch(req));
    return;
  }

  // ✅ Videos -> siempre red (NO cache)
  if (isVideo(url)) {
    event.respondWith(fetch(req));
    return;
  }

  // Estáticos -> cache first
  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          // Si falla o no es OK, devolvés tal cual sin guardar
          if (!res || res.status !== 200) return res;

          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return res;
        });
      })
    );
  }
});

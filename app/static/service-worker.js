// static/service-worker.js

const CACHE_NAME = "vr-training-static-v1";
const STATIC_ASSETS = [
  "/",
  "/static/css/styles_v2.css",
  "/static/manifest.webmanifest",
  "/static/logo_negro_vr_training.png",
  "/static/logo_blanco_vr_training.png",
  "/static/icons/icon-192.png"
];

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

// ✅ NO cachear videos ni /media/
function isVideo(requestUrl) {
  return requestUrl.pathname.startsWith("/static/videos/") || requestUrl.pathname.startsWith("/media/");
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // videos: siempre network
  if (isVideo(url)) {
    event.respondWith(fetch(event.request));
    return;
  }

  // HTML navegación: network-first
  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/")));
    return;
  }

  // static: cache-first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // default
  event.respondWith(fetch(event.request));
});

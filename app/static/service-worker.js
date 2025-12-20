const CACHE_NAME = "vr-training-static-v2";

const STATIC_ASSETS = [
  "/static/css/styles_v2.css",
  "/static/icons/icon-192.png",
  "/static/manifest.webmanifest",
  "/static/logo_negro_vr_training.png",
  "/static/logo_blanco_vr_training.png"
];

// Detecta navegación (HTML)
function isNavigation(request) {
  return (
    request.mode === "navigate" ||
    (request.headers.get("accept") || "").includes("text/html")
  );
}

// Detecta si es video o si el navegador pide Range (muy común en <video>)
function isVideoRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname.toLowerCase();
  const range = request.headers.get("range");
  const dest = request.destination;

  return (
    dest === "video" ||
    !!range ||
    path.endsWith(".mp4") ||
    path.endsWith(".webm") ||
    path.endsWith(".mov") ||
    path.endsWith(".m4v")
  );
}

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
      await Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // ✅ 1) JAMÁS tocar videos / Range. Siempre ir a red directo.
  if (isVideoRequest(request)) {
    event.respondWith(fetch(request));
    return;
  }

  // ✅ 2) Navegación: network-first (si cae, cache)
  if (isNavigation(request)) {
    event.respondWith(
      (async () => {
        try {
          const network = await fetch(request);
          return network;
        } catch (e) {
          const cached = await caches.match(request);
          return cached || Response.error();
        }
      })()
    );
    return;
  }

  // ✅ 3) Static: cache-first
  if (isStatic(url)) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  // ✅ 4) Default: network-first
  event.respondWith(
    (async () => {
      try {
        return await fetch(request);
      } catch (e) {
        const cached = await caches.match(request);
        return cached || Response.error();
      }
    })()
  );
});

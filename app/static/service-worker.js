self.addEventListener('install', function (e) {
    console.log('Service Worker instalado');
    e.waitUntil(
      caches.open('urban-athletics-cache').then(function (cache) {
        return cache.addAll([
          '/',
          '/static/styles.css', // si tenés un css
          '/static/icons/icon-192.png',
          '/static/icons/icon-512.png'
        ]);
      })
    );
  });
  
  self.addEventListener('fetch', function (e) {
    e.respondWith(
      caches.match(e.request).then(function (response) {
        return response || fetch(e.request);
      })
    );
  });
  
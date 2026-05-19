const ADMIN_CACHE = "etisul-admin-v3";

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(ADMIN_CACHE).then((cache) => {
            return cache.addAll([
                "/login",
                "/static/css/style.css",
                "/static/js/scroll-effects.js",
                "/static/img/logo-grande.png",
                "/static/img/favicon-32.png",
                "/static/img/favicon-180.png",
                "/static/img/admin-icon-192.png",
                "/static/img/admin-icon-512.png"
            ]);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== ADMIN_CACHE).map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});

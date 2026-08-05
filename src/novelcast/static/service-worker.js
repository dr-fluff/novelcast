/* novelcast/src/novelcast/static/service-worker.js */

const CACHE_NAME = "novelcast-v1";

const FILES = [
    "/",
    "/static/style.css",
    "/static/app.js"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(FILES))
    );
});


self.addEventListener("fetch", event => {
    event.respondWith(
        caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
});
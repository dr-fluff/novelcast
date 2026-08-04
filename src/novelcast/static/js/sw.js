// novelcast/static/js/sw.js
//
// Service worker for the chapter reader. Two jobs:
//
// 1. Serve /chapter navigations cache-first. Once a chapter has been
//    downloaded, its content doesn't change, so there's no reason to
//    re-fetch it over the network every time — cache-first means an
//    already-cached chapter loads instantly even on a dead connection.
//
// 2. Precache upcoming chapters on request from the page, with retry +
//    backoff. This is what protects reading through a genuinely slow
//    or spotty connection: chapters get fetched and stored ahead of
//    time, with several attempts each, so a brief drop in connectivity
//    doesn't cost you a chapter you haven't reached yet.

const CACHE_NAME = 'novelcast-chapters-v1';
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1000;

self.addEventListener('install', () => {
    // Take over immediately rather than waiting for old tabs to close —
    // this is a caching helper, not something that needs strict version
    // gating between installs.
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

// ── Cache-first serving for chapter navigations ────────────────────────

self.addEventListener('fetch', (event) => {
    let url;
    try {
        url = new URL(event.request.url);
    } catch (e) {
        return;
    }

    if (event.request.method !== 'GET' || url.pathname !== '/chapter') return;

    event.respondWith(
        (async () => {
            const cache = await caches.open(CACHE_NAME);
            const cached = await cache.match(event.request);
            if (cached) return cached;

            // Not cached yet (e.g. jumping to a chapter that was never
            // precached) — fall through to a normal network fetch, and cache
            // the result so a repeat visit (or back navigation) is instant.
            const response = await fetch(event.request);
            if (response && response.ok) {
                cache.put(event.request, response.clone());
            }
            return response;
        })()
    );
});

// ── Precaching on request from the page ────────────────────────────────

async function fetchWithRetry(url) {
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        try {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (response && response.ok) return response;
        } catch (err) {
            // network error — fall through to retry/backoff below
        }
        if (attempt < MAX_RETRIES - 1) {
            await new Promise((resolve) => setTimeout(resolve, RETRY_BASE_DELAY_MS * (attempt + 1)));
        }
    }
    return null;
}

self.addEventListener('message', (event) => {
    const data = event.data || {};
    if (data.type !== 'PRECACHE_CHAPTERS' || !Array.isArray(data.urls)) return;

    const task = (async () => {
        const cache = await caches.open(CACHE_NAME);
        for (const url of data.urls) {
            const existing = await cache.match(url);
            if (existing) continue; // already have it — don't re-fetch or re-count retries
            const response = await fetchWithRetry(url);
            if (response) {
                await cache.put(url, response.clone());
            }
            // If a URL never succeeds after all retries, we just move on —
            // the reader will fall back to a normal (slower) network fetch
            // if/when the person actually reaches that chapter.
        }
    })();

    if (event.waitUntil) event.waitUntil(task);
});

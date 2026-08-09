// novelcast/static/sw.js


importScripts('/static/js/offline-db.js');

const CACHE_NAME = 'novelcast-chapters-v1';
const SHELL_CACHE_NAME = 'novelcast-shell-v1';
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1000;

const SHELL_ASSETS = [
    '/',
    '/static/css/tokens.css',
    '/static/css/base.css',
    '/static/css/layout.css',
    '/static/css/components/nav.css',
    '/static/css/components/grid.css',
    '/static/css/components/grid_toolbar.css',
    '/static/css/components/cards.css',
    '/static/css/components/forms.css',
    '/static/css/components/buttons.css',
    '/static/css/components/modal.css',
    '/static/css/components/notifications.css',
    '/static/css/components/pagination.css',
    '/static/css/components/unified-panel.css',
    '/static/js/unified-panel.js',
    '/static/js/offline-db.js',
    '/static/js/offline-sync.js',
    '/static/js/main.js',
    '/static/js/library_header.js',
    '/static/js/notifications.js',
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(SHELL_CACHE_NAME).then((cache) =>
            Promise.all(SHELL_ASSETS.map((url) => cache.add(url).catch(() => {})))
        )
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) =>
                Promise.all(
                    keys.filter((k) => k !== CACHE_NAME && k !== SHELL_CACHE_NAME).map((k) => caches.delete(k))
                )
            )
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    let url;
    try {
        url = new URL(event.request.url);
    } catch (e) {
        return;
    }
    if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (url.pathname === '/chapter') {
        const cacheUrl = new URL(url);
        cacheUrl.searchParams.delete('page');
        cacheUrl.searchParams.delete('anchor');
        cacheUrl.searchParams.delete('lastPage');
        const cacheKey = new Request(cacheUrl.toString(), { method: 'GET' });
        event.respondWith(cacheFirst(cacheKey, CACHE_NAME));
        return;
    }

    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(event.request, SHELL_CACHE_NAME, { revalidate: true }));
        return;
    }

    if (event.request.mode === 'navigate') {
        event.respondWith(networkFirstNavigation(event.request));
        return;
    }
});

async function cacheFirst(request, cacheName, { revalidate = false } = {}) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);

    if (cached) {
        if (revalidate) {
            fetch(request)
                .then((res) => res && res.ok && cache.put(request, res.clone()))
                .catch(() => {});
        }
        return cached;
    }
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
}

async function networkFirstNavigation(request) {
    const cache = await caches.open(SHELL_CACHE_NAME);
    try {
        const response = await fetch(request);
        if (response && response.ok) cache.put(request, response.clone());
        return response;
    } catch (e) {
        const cached = await cache.match(request);
        if (cached) return cached;
        throw e;
    }
}

async function fetchWithRetry(url) {
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        try {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (response && response.ok) return response;
        } catch (err) {
        }
        if (attempt < MAX_RETRIES - 1) {
            await new Promise((resolve) => setTimeout(resolve, RETRY_BASE_DELAY_MS * (attempt + 1)));
        }
    }
    return null;
}

self.addEventListener('message', (event) => {
    const data = event.data || {};

    if (data.type === 'PRECACHE_CHAPTERS' && Array.isArray(data.urls)) {
        const task = (async () => {
            const cache = await caches.open(CACHE_NAME);
            for (const url of data.urls) {
                const existing = await cache.match(url);
                if (existing) continue;
                const response = await fetchWithRetry(url);
                if (response) await cache.put(url, response.clone());
            }
        })();
        if (event.waitUntil) event.waitUntil(task);
        return;
    }

    if (data.type === 'MARK_STORY_OFFLINE') {
        const task = handleMarkStoryOffline(data, event);
        if (event.waitUntil) event.waitUntil(task);
        return;
    }

    if (data.type === 'REMOVE_STORY_OFFLINE') {
        const task = handleRemoveStoryOffline(data, event);
        if (event.waitUntil) event.waitUntil(task);
        return;
    }
});

// ── Explicit per-story offline download / removal ───────────────────────

async function handleMarkStoryOffline(data, event) {
    const port = event.ports && event.ports[0];
    try {
        const { storyId, meta } = data;
        const chapterIds = meta.chapterIds || [];
        const chapterUrls = chapterIds.map((cid) => `/chapter?story_id=${storyId}&chapter_id=${cid}`);
        const storyPageUrl = `/story?story_id=${storyId}`;

        const [chapterCache, shellCache] = await Promise.all([
            caches.open(CACHE_NAME),
            caches.open(SHELL_CACHE_NAME),
        ]);

        const existingRecord = await NovelcastOfflineDB.getOfflineStory(storyId);
        const isRefresh = !!existingRecord;

        const shellUrls = meta.coverUrl ? [storyPageUrl, meta.coverUrl] : [storyPageUrl];

        for (const url of shellUrls) {
            if (!isRefresh) {
                const existing = await shellCache.match(url);
                if (existing) continue;
            }
            const response = await fetchWithRetry(url);
            if (response) await shellCache.put(url, response.clone());
        }

        const previousChapterIds = new Set(existingRecord?.chapterIds || []);
        const currentChapterIds = new Set(chapterIds);

        const removedIds = [...previousChapterIds].filter((id) => !currentChapterIds.has(id));
        for (const cid of removedIds) {
            await chapterCache.delete(`/chapter?story_id=${storyId}&chapter_id=${cid}`);
        }

        for (const url of chapterUrls) {
            const existing = await chapterCache.match(url);
            if (existing) continue; 
            const response = await fetchWithRetry(url);
            if (response) await chapterCache.put(url, response.clone());
        }

        await NovelcastOfflineDB.putOfflineStory({
            storyId: Number(storyId),
            title: meta.title || '',
            coverUrl: meta.coverUrl || '',
            chapterIds,
            downloadedAt: Date.now(),
        });

        port?.postMessage({ ok: true, refreshed: isRefresh, addedChapters: chapterIds.length - previousChapterIds.size + removedIds.length, removedChapters: removedIds.length });
    } catch (err) {
        port?.postMessage({ error: err.message || 'Failed to mark story offline' });
    }
}

async function handleRemoveStoryOffline(data, event) {
    const port = event.ports && event.ports[0];
    try {
        const { storyId } = data;
        const record = await NovelcastOfflineDB.getOfflineStory(storyId);

        const [chapterCache, shellCache] = await Promise.all([
            caches.open(CACHE_NAME),
            caches.open(SHELL_CACHE_NAME),
        ]);

        if (record) {
            await shellCache.delete(`/story?story_id=${storyId}`);
            if (record.coverUrl) await shellCache.delete(record.coverUrl);
            for (const cid of record.chapterIds || []) {
                await chapterCache.delete(`/chapter?story_id=${storyId}&chapter_id=${cid}`);
            }
        }

        await NovelcastOfflineDB.deleteOfflineStory(storyId);
        port?.postMessage({ ok: true });
    } catch (err) {
        port?.postMessage({ error: err.message || 'Failed to remove offline story' });
    }
}

self.addEventListener('sync', (event) => {
    if (event.tag === 'flush-novelcast-queue') {
        event.waitUntil(NovelcastOfflineDB.flushSyncQueue());
    }
});
/* novelcast/static/js/offline-db.js
 *
 * Low-level IndexedDB access shared between page scripts (loaded as a
 * normal <script>, runs in `window`) and the service worker (loaded via
 * importScripts(), runs in the SW global scope). Both contexts expose a
 * `self` that this file attaches to, so the exact same code works in
 * both places with no build step or bundler.
 *
 * Two stores:
 *   - "stories": one record per story marked available offline, used to
 *     drive the offline badge/toggle UI and to know what to delete from
 *     the caches when a story is removed.
 *   - "queue": writes (progress, settings, preferences) that failed to
 *     reach the server — flushed again once back online.
 */
(function (global) {
    const DB_NAME = 'novelcast-offline';
    const DB_VERSION = 1;
    const STORIES_STORE = 'stories';
    const QUEUE_STORE = 'queue';

    let dbPromise = null;

    function openDB() {
        if (dbPromise) return dbPromise;
        dbPromise = new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains(STORIES_STORE)) {
                    db.createObjectStore(STORIES_STORE, { keyPath: 'storyId' });
                }
                if (!db.objectStoreNames.contains(QUEUE_STORE)) {
                    db.createObjectStore(QUEUE_STORE, { keyPath: 'id', autoIncrement: true });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
        return dbPromise;
    }

    async function store(storeName, mode) {
        const db = await openDB();
        return db.transaction(storeName, mode).objectStore(storeName);
    }

    function reqToPromise(req) {
        return new Promise((resolve, reject) => {
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    // ── Offline stories ──────────────────────────────────────────────

    async function getAllOfflineStories() {
        return reqToPromise((await store(STORIES_STORE, 'readonly')).getAll());
    }

    async function getOfflineStory(storyId) {
        return reqToPromise((await store(STORIES_STORE, 'readonly')).get(Number(storyId)));
    }

    async function putOfflineStory(record) {
        return reqToPromise((await store(STORIES_STORE, 'readwrite')).put(record));
    }

    async function deleteOfflineStory(storyId) {
        return reqToPromise((await store(STORIES_STORE, 'readwrite')).delete(Number(storyId)));
    }

    // ── Sync queue ────────────────────────────────────────────────────

    async function queueRequest(entry) {
        return reqToPromise((await store(QUEUE_STORE, 'readwrite')).add({ ...entry, createdAt: Date.now() }));
    }

    async function getQueue() {
        return reqToPromise((await store(QUEUE_STORE, 'readonly')).getAll());
    }

    async function removeQueueItem(id) {
        return reqToPromise((await store(QUEUE_STORE, 'readwrite')).delete(id));
    }

    // Flushes the queue in FIFO order. Stops at the first failure so
    // ordering is preserved (e.g. an earlier progress update shouldn't
    // land after a later one just because of retry timing) — whatever's
    // left stays queued for the next attempt.
    async function flushSyncQueue() {
        const items = await getQueue();
        let flushed = 0;
        for (const item of items) {
            try {
                const res = await fetch(item.url, {
                    method: item.method,
                    headers: item.headers,
                    body: item.body,
                });
                if (!res.ok) break;
                await removeQueueItem(item.id);
                flushed++;
            } catch (e) {
                break; // still offline, or a transient error — retry later
            }
        }
        return { flushed, remaining: items.length - flushed };
    }

    global.NovelcastOfflineDB = {
        openDB,
        getAllOfflineStories,
        getOfflineStory,
        putOfflineStory,
        deleteOfflineStory,
        queueRequest,
        getQueue,
        removeQueueItem,
        flushSyncQueue,
    };
})(self);
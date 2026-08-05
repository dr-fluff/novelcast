/* novelcast/static/js/offline-sync.js
 *
 * Page-side offline support. Depends on offline-db.js being loaded
 * first (see layouts/base.html).
 *
 * - Registers the service worker (idempotent -- chapter_paginated.js
 *   also registers it on the chapter page; registering twice with the
 *   same script URL is a no-op).
 * - queuedFetch(): wraps a write request; if it fails (offline, or a
 *   network/server error) the request is queued in IndexedDB instead
 *   of being lost, and retried once connectivity returns.
 * - markStoryOffline() / removeStoryOffline() / isStoryOffline():
 *   talk to the service worker to actually cache (or evict) a story's
 *   pages and chapters, and to know whether one is currently offline.
 *
 * NOTE on Background Sync: the Background Sync API (registration.sync)
 * is not supported on iOS Safari / any iOS browser (they're all
 * WebKit). Where it IS supported, it's used as a progressive
 * enhancement so the queue can flush even if the tab isn't open. Where
 * it isn't, the 'online' event listener + the flush-on-load below is
 * what actually guarantees delivery -- it just requires the app to be
 * open again rather than syncing silently in the background.
 */
(function () {
    async function ensureServiceWorker() {
        if (!('serviceWorker' in navigator)) return null;
        try {
            const reg = await navigator.serviceWorker.register('/sw.js');
            await navigator.serviceWorker.ready;
            return reg;
        } catch (e) {
            return null;
        }
    }

    // Sends a message to the active service worker and waits for its
    // reply via a MessageChannel, so callers can show real success/error
    // state instead of firing and forgetting.
    function waitForController(timeoutMs = 8000) {
        if (navigator.serviceWorker.controller) {
            return Promise.resolve(navigator.serviceWorker.controller);
        }
        return navigator.serviceWorker.ready.then(
            () =>
                new Promise((resolve) => {
                    if (navigator.serviceWorker.controller) {
                        resolve(navigator.serviceWorker.controller);
                        return;
                    }
                    const onChange = () => {
                        navigator.serviceWorker.removeEventListener('controllerchange', onChange);
                        resolve(navigator.serviceWorker.controller);
                    };
                    navigator.serviceWorker.addEventListener('controllerchange', onChange);
                    setTimeout(() => {
                        navigator.serviceWorker.removeEventListener('controllerchange', onChange);
                        resolve(navigator.serviceWorker.controller); // may still be null -- caller handles that
                    }, timeoutMs);
                })
        );
    }

    async function messageServiceWorker(message) {
        if (!('serviceWorker' in navigator)) {
            throw new Error('Service workers are not supported in this browser.');
        }
        const controller = await waitForController();
        if (!controller) {
            throw new Error('Offline support did not finish starting up -- please reload the page and try again.');
        }
        return new Promise((resolve, reject) => {
            const channel = new MessageChannel();
            channel.port1.onmessage = (event) => {
                if (event.data?.error) reject(new Error(event.data.error));
                else resolve(event.data);
            };
            controller.postMessage(message, [channel.port2]);
        });
    }

    async function queuedFetch(url, options = {}) {
        try {
            const res = await fetch(url, options);
            if (!res.ok && res.status >= 500) throw new Error('Server error');
            return res;
        } catch (e) {
            try {
                await NovelcastOfflineDB.queueRequest({
                    url,
                    method: options.method || 'GET',
                    headers: options.headers || { 'Content-Type': 'application/json' },
                    body: options.body,
                });
                registerBackgroundSync();
            } catch (dbErr) {
                /* IndexedDB unavailable (rare) -- the write is genuinely lost */
            }
            return null;
        }
    }

    function registerBackgroundSync() {
        navigator.serviceWorker?.ready.then((reg) => reg.sync?.register('flush-novelcast-queue')).catch(() => {});
    }

    async function flushQueueNow() {
        try {
            await NovelcastOfflineDB.flushSyncQueue();
        } catch (e) {
            /* will retry on the next online event / page load */
        }
    }

    async function markStoryOffline(storyId, meta) {
        return messageServiceWorker({ type: 'MARK_STORY_OFFLINE', storyId: Number(storyId), meta });
    }

    async function removeStoryOffline(storyId) {
        return messageServiceWorker({ type: 'REMOVE_STORY_OFFLINE', storyId: Number(storyId) });
    }

    async function isStoryOffline(storyId) {
        try {
            const record = await NovelcastOfflineDB.getOfflineStory(storyId);
            return !!record;
        } catch (e) {
            return false;
        }
    }

    window.NovelcastOffline = {
        ensureServiceWorker,
        queuedFetch,
        flushQueueNow,
        markStoryOffline,
        removeStoryOffline,
        isStoryOffline,
    };

    ensureServiceWorker();

    window.addEventListener('online', flushQueueNow);
    if (navigator.onLine) flushQueueNow();
})();
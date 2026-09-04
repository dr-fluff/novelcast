(function () {
    function getNovelcastDeviceId() {
        const key = 'novelcastDeviceId';
        let id = localStorage.getItem(key);

        if (!id) {
            const random = window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

            id = random.replace(/[^A-Za-z0-9_-]/g, '_');
            localStorage.setItem(key, id);
        }

        document.cookie = `novelcast_device_id=${encodeURIComponent(id)}; Path=/; Max-Age=31536000; SameSite=Lax`;

        return id;
    }

    const deviceId = getNovelcastDeviceId();
    const libraryStateStorageKey = 'novelcast.library.index';
    const libraryStateKeys = ['q', 'sort', 'genre', 'tag', 'series', 'language', 'status'];

    function readLocalLibraryState() {
        try {
            const saved = JSON.parse(localStorage.getItem(libraryStateStorageKey) || 'null');
            return saved && typeof saved === 'object' ? saved : null;
        } catch (e) {
            return null;
        }
    }

    const currentUrl = new URL(window.location.href);
    const hasLibraryState = libraryStateKeys.some((key) => currentUrl.searchParams.has(key));
    if (currentUrl.pathname === '/' && !hasLibraryState) {
        const saved = readLocalLibraryState();
        const params = new URLSearchParams();
        libraryStateKeys.forEach((key) => {
            if (saved?.[key]) params.set(key, saved[key]);
        });
        if (params.toString()) {
            window.location.replace(`/?${params.toString()}`);
            return;
        }
    }

    const current = window.novelcastPageData || {
        sort: '',
        genre: '',
        tag: '',
        series: '',
        language: '',
        status: '',
    };

    const toolbar = document.querySelector('.grid-toolbar[data-persist-key]');

    if (toolbar) {
        let submitter = null;

        toolbar.querySelectorAll("button[type='submit']").forEach((button) => {
            button.addEventListener('click', () => {
                submitter = button;
            });
        });

        toolbar.addEventListener('submit', (event) => {
            event.preventDefault();

            const params = new URLSearchParams(new FormData(toolbar));

            if (submitter?.name) {
                params.set(submitter.name, submitter.value);
            }

            Object.entries(current).forEach(([key, value]) => {
                if (submitter?.name === key) {
                    return;
                }

                if (!params.has(key) && value) {
                    params.set(key, value);
                }
            });

            if (!params.has('sort')) {
                params.set('sort', current.sort || 'title');
            }

            const value = {
                q: params.get('q') || '',
                sort: params.get('sort') || current.sort || 'title',
                genre: params.get('genre') || '',
                tag: params.get('tag') || '',
                series: params.get('series') || '',
                language: params.get('language') || '',
                status: params.get('status') || '',
            };

            try {
                localStorage.setItem(libraryStateStorageKey, JSON.stringify(value));
            } catch (e) {
            }

            fetch('/api/user-preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    deviceId,
                    name: toolbar.dataset.persistKey,
                    value,
                }),
                keepalive: true,
            })
                .catch(() => {})
                .finally(() => {
                    const query = params.toString();

                    window.location.href = `${toolbar.action}${query ? `?${query}` : ''}`;
                });
        });

        document.querySelector('.grid-toolbar-clear')?.addEventListener('click', () => {
            try {
                localStorage.removeItem(libraryStateStorageKey);
            } catch (e) {
            }
            fetch('/api/user-preferences', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    deviceId,
                    name: toolbar.dataset.persistKey,
                }),
                keepalive: true,
            }).catch(() => {});
        });
    }

    const prefetchedStories = new Set();
    let prefetchTimer = null;

    function prefetchStory(card) {
        const href = card?.getAttribute('href');
        const connection = navigator.connection;
        if (
            !href ||
            prefetchedStories.has(href) ||
            connection?.saveData ||
            ['slow-2g', '2g'].includes(connection?.effectiveType)
        ) {
            return;
        }

        prefetchedStories.add(href);
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = href;
        document.head.appendChild(link);
    }

    document.querySelectorAll('a.card[href]').forEach((card) => {
        card.addEventListener('mouseenter', () => {
            clearTimeout(prefetchTimer);
            prefetchTimer = setTimeout(() => prefetchStory(card), 150);
        });
        card.addEventListener('mouseleave', () => clearTimeout(prefetchTimer));
        card.addEventListener('focusin', () => prefetchStory(card));
    });

    let refreshTimer = null;

    const refreshEvents = new Set(['download_finished', 'sync_story_updated', 'sync_finished']);

    window.addEventListener('novelcast:notification', (event) => {
        const payload = event.detail || {};

        if (!refreshEvents.has(payload.type)) {
            return;
        }

        if (payload.type === 'sync_finished' && !Number(payload.new_chapters || 0)) {
            return;
        }

        clearTimeout(refreshTimer);

        refreshTimer = setTimeout(() => {
            window.location.reload();
        }, 900);
    });
})();

/* ── Offline badges ──────────────────────────────────────────────────── */

async function paintOfflineBadges() {
    if (!window.NovelcastOfflineDB) return;

    let offlineIds;
    try {
        const stories = await NovelcastOfflineDB.getAllOfflineStories();
        offlineIds = new Set(stories.map((s) => String(s.storyId)));
    } catch (e) {
        return;
    }

    document.querySelectorAll('a.card[href]').forEach((card) => {
        const match = card.getAttribute('href').match(/story_id=(\d+)/);
        const storyId = match?.[1];
        const badge = card.querySelector('.card-offline-badge');
        if (!badge) return;
        badge.style.display = storyId && offlineIds.has(storyId) ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', paintOfflineBadges);
window.addEventListener('online', paintOfflineBadges);
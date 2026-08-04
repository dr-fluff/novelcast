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

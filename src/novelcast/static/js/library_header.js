window.addStory = async function (event) {
    event.preventDefault();

    const input = document.getElementById('story-url');
    const url = input.value.trim();

    if (!url) return;

    setStatus('adding');

    try {
        const res = await fetch('/api/download/story', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        if (!res.ok) {
            const err = await res.text();
            console.error('Download failed:', err);
            setStatus('error');
            if (typeof showNotification === 'function') {
                showNotification(`Download failed: ${err}`, 'error', 8000);
            }
            return;
        }

        const data = await res.json();
        console.log('Story added:', data);

        if (data.status !== 'ok') {
            setStatus('error');
            return;
        }

        input.value = '';
        setStatus('done');
    } catch (err) {
        console.error(err);
        setStatus('error');
    }
};

window.setStatus = function (state) {
    const dot = document.getElementById('sync-status');
    if (!dot) return;

    switch (state) {
        case 'adding':
            dot.style.background = 'orange';
            dot.title = 'Downloading...';
            break;
        case 'done':
            dot.style.background = 'green';
            dot.title = 'Done';
            break;
        case 'error':
            dot.style.background = 'red';
            dot.title = 'Error';
            break;
        default:
            dot.style.background = 'green';
            dot.title = 'Idle';
    }
};

window.toggleUserMenu = function () {
    const panel = document.getElementById('user-menu-panel');
    const overlay = document.getElementById('user-menu-overlay');
    if (!panel || !overlay) return;

    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        window.closeUserMenu();
    } else {
        panel.classList.add('open');
        overlay.classList.add('open');
        window.closeReaderSettings();
    }
};

window.getNovelcastDeviceId = function () {
    try {
        const storedId = localStorage.getItem('nc_device_id');
        if (storedId) {
            document.cookie = `nc_device_id=${encodeURIComponent(storedId)}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
            return storedId;
        }
    } catch (error) {
        // Fall back to the first-party cookie when local storage is unavailable.
    }

    const cookieId = document.cookie.match(/(?:^|; )nc_device_id=([^;]+)/)?.[1];
    if (cookieId) return decodeURIComponent(cookieId);

    const newId = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
              const random = (Math.random() * 16) | 0;
              return (char === 'x' ? random : (random & 0x3) | 0x8).toString(16);
          });
    try {
        localStorage.setItem('nc_device_id', newId);
    } catch (error) {
        // The cookie remains the fallback device store.
    }
    document.cookie = `nc_device_id=${encodeURIComponent(newId)}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
    return newId;
};

window.openReaderSettings = async function () {
    const links = document.getElementById('user-menu-links');
    const panel = document.getElementById('user-menu-reader-settings');
    if (!links || !panel) return;

    links.hidden = true;
    panel.hidden = false;
    if (panel.dataset.loaded === 'true') return;

    let schema = {};
    try {
        schema = JSON.parse(panel.dataset.readingSchema || '{}');
    } catch (error) {
        schema = {};
    }
    const fields = document.getElementById('user-menu-reader-fields');
    if (!fields) return;

    const settings = Object.fromEntries(Object.entries(schema).map(([key, spec]) => [key, spec.default]));
    const deviceId = window.getNovelcastDeviceId();
    try {
        const response = await fetch('/api/chapter-settings', {
            headers: { 'X-Device-Id': deviceId },
        });
        if (response.ok) Object.assign(settings, (await response.json()).settings || {});
    } catch (error) {
        // Defaults from the schema keep the controls usable while offline.
    }

    const save = async () => {
        const status = document.getElementById('user-menu-reader-status');
        try {
            const response = await fetch('/api/chapter-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Device-Id': deviceId },
                body: JSON.stringify({ settings }),
            });
            if (!response.ok) throw new Error('Settings could not be saved.');
            if (status) status.textContent = 'Saved';
        } catch (error) {
            if (status) status.textContent = 'Could not save settings';
        }
    };

    const applyTheme = () => {
        const preference = settings.theme || 'system';
        const root = document.documentElement;
        root.dataset.themeMode = preference;
        root.dataset.theme = preference === 'system'
            ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
            : preference;
    };

    Object.entries(schema).forEach(([key, spec]) => {
        const group = document.createElement('div');
        group.className = 'user-menu-reader-group';
        const label = document.createElement('label');
        label.textContent = spec.label || key;
        group.appendChild(label);

        if (spec.control === 'buttons') {
            const options = [...(spec.options || [])];
            if (key === 'theme' && !options.some((option) => option.value === 'system')) {
                options.unshift({ value: 'system', label: 'System' });
            }
            const buttons = document.createElement('div');
            buttons.className = 'user-menu-reader-options';
            options.forEach((option) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'setting-btn';
                button.dataset.key = key;
                button.dataset.value = option.value;
                button.textContent = option.label;
                button.classList.toggle('active', String(settings[key]) === String(option.value));
                button.addEventListener('click', () => {
                    const value = option.value;
                    settings[key] = typeof value === 'number' ? value : /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : value;
                    buttons.querySelectorAll('.setting-btn').forEach((item) => {
                        item.classList.toggle('active', String(settings[key]) === item.dataset.value);
                    });
                    if (key === 'theme') applyTheme();
                    save();
                });
                buttons.appendChild(button);
            });
            group.appendChild(buttons);
        } else if (spec.control === 'slider') {
            const control = document.createElement('div');
            control.className = 'user-menu-reader-slider';
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = spec.min;
            slider.max = spec.max;
            slider.step = spec.step || 1;
            slider.value = settings[key];
            const value = document.createElement('span');
            value.className = 'user-menu-reader-value';
            value.textContent = `${settings[key]}${spec.unit || ''}`;
            slider.addEventListener('input', () => {
                settings[key] = Number(slider.value);
                value.textContent = `${settings[key]}${spec.unit || ''}`;
            });
            slider.addEventListener('change', save);
            control.append(slider, value);
            group.appendChild(control);
        }

        fields.appendChild(group);
    });
    panel.dataset.loaded = 'true';
};

window.closeReaderSettings = function () {
    const links = document.getElementById('user-menu-links');
    const panel = document.getElementById('user-menu-reader-settings');
    if (links) links.hidden = false;
    if (panel) panel.hidden = true;
};

const systemThemeMedia = window.matchMedia?.('(prefers-color-scheme: dark)');
systemThemeMedia?.addEventListener?.('change', (event) => {
    if (document.documentElement.dataset.themeMode === 'system') {
        document.documentElement.dataset.theme = event.matches ? 'dark' : 'light';
    }
});

window.closeUserMenu = function () {
    const panel = document.getElementById('user-menu-panel');
    const overlay = document.getElementById('user-menu-overlay');
    if (!panel || !overlay) return;

    panel.classList.remove('open');
    overlay.classList.remove('open');
};

window.logoutUser = function () {
    window.location.href = '/logout';
};

window.startSync = async function () {
    try {
        const res = await fetch('/api/sync/all', {
            method: 'POST',
        });

        const data = await res.json();
        console.log('Sync started:', data);

        window.showSyncStatus('Sync running...');
    } catch (error) {
        console.error('Sync failed:', error);
        window.showSyncStatus('Sync failed');
    }
};

window.showSyncStatus = function (status) {
    const dot = document.getElementById('sync-status');
    if (!dot) return;

    dot.style.background = status === 'Sync failed' ? 'red' : 'orange';
    dot.title = status;
};

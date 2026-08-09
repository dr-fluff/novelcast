/* novelcast/static/js/story_page.js */

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

const novelcastDeviceId = getNovelcastDeviceId();

function saveDevicePreference(name, value) {
    fetch('/api/user-preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            deviceId: novelcastDeviceId,
            name,
            value,
        }),
        keepalive: true,
    }).catch(() => {});
}

window.toggleSection = function (key) {
    const body = document.getElementById(key + 'Body');
    const chevron = document.getElementById(key + 'Chevron');
    if (!body) return;
    const collapsed = body.classList.toggle('collapsed');
    if (chevron) chevron.classList.toggle('collapsed', collapsed);
};

const SORT_MODES = ['asc', 'desc'];
let chapterSortMode = document.querySelector('.story-page')?.dataset.chapterSort || 'asc';
if (!SORT_MODES.includes(chapterSortMode)) chapterSortMode = 'asc';

function applyChapterSort(mode) {
    const list = document.getElementById('chapterList');
    if (!list) return;

    const items = [...list.querySelectorAll('.chapter-item')];
    items.sort((a, b) => {
        const na = parseInt(a.dataset.chapterNumber, 10) || 0;
        const nb = parseInt(b.dataset.chapterNumber, 10) || 0;
        return mode === 'asc' ? na - nb : nb - na;
    });
    items.forEach((el) => list.appendChild(el));

    const icon = document.getElementById('sortIcon');
    if (icon) {
        icon.className = mode === 'asc' ? 'fa-solid fa-arrow-up-wide-short' : 'fa-solid fa-arrow-down-wide-short';
    }

    if (window.chapterPaginator) {
        setTimeout(() => window.chapterPaginator.refresh(), 0);
    }
}

window.cycleSort = function () {
    chapterSortMode = chapterSortMode === 'asc' ? 'desc' : 'asc';
    applyChapterSort(chapterSortMode);
    saveDevicePreference('story.chapters.sort', chapterSortMode);
};

let showingFullPath = false;

function toggleFullPath() {
    showingFullPath = !showingFullPath;

    document.querySelectorAll('.file-path-text').forEach((el) => {
        el.textContent = showingFullPath ? el.dataset.full : el.dataset.relative;

        el.classList.toggle('full-path', showingFullPath);
    });
}

let fileSortMode = document.querySelector('.story-page')?.dataset.fileSort || 'asc';
if (!SORT_MODES.includes(fileSortMode)) fileSortMode = 'asc';

function applyFileSort(mode) {
    const tbody = document.querySelector('.file-table tbody');
    if (!tbody) return;

    const rows = [...tbody.querySelectorAll('.file-row')];
    rows.sort((a, b) => {
        const aPath = a.querySelector('.file-path-text')?.dataset.relative || '';
        const bPath = b.querySelector('.file-path-text')?.dataset.relative || '';
        return mode === 'asc'
            ? aPath.localeCompare(bPath, undefined, { numeric: true, sensitivity: 'base' })
            : bPath.localeCompare(aPath, undefined, { numeric: true, sensitivity: 'base' });
    });
    rows.forEach((row) => tbody.appendChild(row));

    const icon = document.getElementById('fileSortIcon');
    if (icon) {
        icon.className = mode === 'asc' ? 'fa-solid fa-arrow-up-wide-short' : 'fa-solid fa-arrow-down-wide-short';
    }

    if (window.filePaginator) {
        setTimeout(() => window.filePaginator.refresh(), 0);
    }
}

window.cycleFileSort = function () {
    fileSortMode = fileSortMode === 'asc' ? 'desc' : 'asc';
    applyFileSort(fileSortMode);
    saveDevicePreference('story.files.sort', fileSortMode);
};

document.addEventListener('DOMContentLoaded', () => {
    applyChapterSort(chapterSortMode);
    applyFileSort(fileSortMode);
});

window.goToReading = async function () {
    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    const lastId = section?.dataset.lastChapterId;
    const unreadId = section?.dataset.firstUnreadId;
    const chapterId = lastId || unreadId;
    if (!storyId || !chapterId) return;

    try {
        const r = await fetch(`/api/chapter-progress?chapter_id=${chapterId}`);
        if (r.ok) {
            const data = await r.json();
            const page = data.page || 0;
            const url = `/chapter?story_id=${storyId}&chapter_id=${chapterId}${page > 0 ? `&page=${page}` : ''}`;
            window.location.href = url;
            return;
        }
    } catch (e) {
    }

    window.location.href = `/chapter?story_id=${storyId}&chapter_id=${chapterId}`;
};

window.openMetaPanel = function () {
    const panel = document.getElementById('metadataPanel');
    if (panel) panel.classList.add('open');
};

window.confirmDeleteStory = async function () {
    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    if (!storyId) return;
    if (!confirm('Delete this story and all its data? This cannot be undone.')) return;
    try {
        const res = await fetch(`/api/stories/${storyId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(await res.text());
        window.location.href = '/';
    } catch (err) {
        window.showNotification?.(`Delete failed: ${err.message}`, 'error', 6000) ??
            alert(`Delete failed: ${err.message}`);
    }
};

window.toggleDescription = function () {
    const desc = document.getElementById('storyDescription');
    const btn = document.getElementById('readMoreBtn');
    if (!desc || !btn) return;
    const expanded = desc.classList.toggle('expanded');
    btn.innerHTML = expanded
        ? 'Show less <i class="fa-solid fa-chevron-up"></i>'
        : 'Read more <i class="fa-solid fa-chevron-down"></i>';
};

let _activeDropdown = null;

function closeActiveDropdown() {
    if (_activeDropdown) {
        _activeDropdown.remove();
        _activeDropdown = null;
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.file-menu-wrapper') && !e.target.closest('.story-menu-wrapper')) {
        closeActiveDropdown();
    }
});

window.openFileMenu = function (btn, filePath, fileType) {
    closeActiveDropdown();
    const wrapper = btn.closest('.file-menu-wrapper');
    const dropdown = document.createElement('div');
    dropdown.className = 'file-dropdown';
    dropdown.innerHTML = `
        <button class="file-dropdown-item" onclick="downloadFile(${JSON.stringify(filePath)})">Download</button>
        <button class="file-dropdown-item danger" onclick="deleteFile(${JSON.stringify(filePath)})">Delete</button>
        <button class="file-dropdown-item" onclick="openFileInfo(${JSON.stringify(filePath)}, ${JSON.stringify(fileType)})">More Info</button>
    `;
    wrapper.appendChild(dropdown);
    _activeDropdown = dropdown;
};

window.openStoryMenu = function (btn) {
    closeActiveDropdown();
    const wrapper = btn.closest('.file-menu-wrapper');
    const dropdown = document.createElement('div');
    dropdown.className = 'file-dropdown';

    let items = `<button class="file-dropdown-item" onclick="updateStory()">Update story</button>`;
    if (_isStoryOffline) {
        items += `<button class="file-dropdown-item danger" onclick="removeOfflineCopy()">Remove from offline</button>`;
    }

    dropdown.innerHTML = items;
    wrapper.appendChild(dropdown);
    _activeDropdown = dropdown;
};

window.updateStory = async function () {
    closeActiveDropdown();

    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    if (!storyId) {
        return (
            window.showNotification?.('Unable to update story: missing story ID.', 'error', 6000) ||
            alert('Unable to update story: missing story ID.')
        );
    }

    try {
        const res = await fetch(`/api/sync/update/story/${storyId}`, {
            method: 'POST',
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || res.statusText);
        }

        window.showNotification?.('Update requested for this story.', 'success', 5000);
    } catch (err) {
        window.showNotification?.(`Update failed: ${err.message}`, 'error', 7000) ||
            alert(`Update failed: ${err.message}`);
    }
};

window.downloadFile = function (filePath) {
    closeActiveDropdown();
    window.open(`/api/files/download?path=${encodeURIComponent(filePath)}`, '_blank');
};

window.deleteFile = async function (filePath) {
    closeActiveDropdown();
    if (!confirm(`Delete file: ${filePath}?`)) return;
    try {
        const res = await fetch(`/api/files/delete`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath }),
        });
        if (!res.ok) throw new Error(await res.text());
        document.querySelectorAll('.file-path-text').forEach((el) => {
            if (el.dataset.full === filePath || el.dataset.relative === filePath) {
                el.closest('.file-row').remove();
            }
        });
        window.filePaginator?.refresh();
        window.showNotification?.('File deleted.', 'success', 4000);
    } catch (err) {
        window.showNotification?.(`Delete failed: ${err.message}`, 'error', 6000);
    }
};

window.openFileInfo = async function (filePath, fileType) {
    closeActiveDropdown();

    const overlay = document.getElementById('fileInfoOverlay');
    const title = document.getElementById('fileInfoTitle');
    const body = document.getElementById('fileInfoBody');
    const probe = document.getElementById('fileInfoProbeBtn');

    title.textContent = filePath.split('/').pop();
    body.innerHTML = `<div class="file-info-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading…</div>`;

    const isAudio = ['audio', 'm4b', 'mp3', 'aac', 'flac', 'ogg'].includes((fileType || '').toLowerCase());
    probe.style.display = isAudio ? '' : 'none';
    probe.onclick = () => probeAudioFile(filePath);

    overlay.classList.add('open');

    try {
        const res = await fetch(`/api/files/info?path=${encodeURIComponent(filePath)}`);
        if (!res.ok) throw new Error(await res.text());
        renderFileInfo(body, filePath, await res.json());
    } catch (err) {
        body.innerHTML = `
            <p class="file-info-section-title">Path</p>
            <div class="file-info-path-box">${filePath}</div>
            <p style="color:#f87171;font-size:0.88rem;margin-top:1rem;">
                Could not load file details: ${err.message}
            </p>`;
    }
};

window.addEventListener('novelcast:notification', (event) => {
    const payload = event.detail || {};
    const currentStoryId = document.querySelector('.story-page')?.dataset.storyId;
    if (!currentStoryId || String(payload.story_id) !== currentStoryId) return;

    if (document.getElementById('metaPanel')?.classList.contains('open')) {
        return;
    }

    if (['sync_story_updated', 'sync_finished', 'story_updated'].includes(payload.type)) {
        if (_isStoryOffline) {
            window.showNotification?.(
                'This story updated — your offline copy is now out of date. Tap the offline button to refresh it.',
                'info',
                8000
            );
        }
        window.location.reload();
    }
});

window.addEventListener('novelcast:story-updated', (event) => {
    const payload = event.detail || {};
    const currentStoryId = document.querySelector('.story-page')?.dataset.storyId;
    if (!currentStoryId || String(payload.storyId) !== currentStoryId) return;
    if (document.getElementById('metaPanel')?.classList.contains('open')) {
        return;
    }
    window.location.reload();
});

function renderFileInfo(body, filePath, info) {
    const details = [
        ['Size', info.size],
        ['Duration', info.duration],
        ['Format', info.format],
        ['Codec', info.codec],
        ['Channels', info.channels],
        ['Bitrate', info.bitrate],
        ['Chapters', info.chapters],
        ['Time Base', info.time_base],
        ['Embedded Cover', info.embedded_cover],
        ['Language', info.language],
    ].filter(([, v]) => v !== undefined && v !== null && v !== '');

    const left = details.filter((_, i) => i % 2 === 0);
    const right = details.filter((_, i) => i % 2 === 1);

    let detailRows = '';
    for (let i = 0; i < Math.max(left.length, right.length); i++) {
        const l = left[i] || null;
        const r = right[i] || null;
        detailRows += `
            <div class="file-info-row">${l ? `<dt>${l[0]}</dt><dd>${l[1]}</dd>` : '<dt></dt><dd></dd>'}</div>
            <div class="file-info-row">${r ? `<dt>${r[0]}</dt><dd>${r[1]}</dd>` : '<dt></dt><dd></dd>'}</div>`;
    }

    let metaTagsHtml = '';
    if (info.meta_tags && Object.keys(info.meta_tags).length) {
        const rows = Object.entries(info.meta_tags)
            .map(
                ([k, v]) =>
                    `<dt>${k}</dt><dd${k === 'Comment' || String(v).length > 60 ? ` class="file-info-comment"` : ''}>${v}</dd>`
            )
            .join('');
        metaTagsHtml = `
            <hr class="file-info-divider" />
            <div>
                <p class="file-info-section-title">Meta Tags</p>
                <dl class="file-info-tags-grid">${rows}</dl>
            </div>`;
    }

    body.innerHTML = `
        <div>
            <p class="file-info-section-title">Path</p>
            <div class="file-info-path-box">${filePath}</div>
        </div>
        ${details.length ? `<dl class="file-info-grid">${detailRows}</dl>` : ''}
        ${metaTagsHtml}
    `;
}

window.closeFileInfo = function (e) {
    if (e.target === document.getElementById('fileInfoOverlay')) closeFileInfoModal();
};

window.closeFileInfoModal = function () {
    document.getElementById('fileInfoOverlay').classList.remove('open');
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFileInfoModal();
});

window.probeAudioFile = async function (filePath) {
    window.showNotification?.('Probing audio file…', 'info', 3000);
    try {
        const res = await fetch(`/api/files/probe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath }),
        });
        if (!res.ok) throw new Error(await res.text());
        renderFileInfo(document.getElementById('fileInfoBody'), filePath, await res.json());
    } catch (err) {
        window.showNotification?.(`Probe failed: ${err.message}`, 'error', 6000);
    }
};

let _isStoryOffline = false;

async function refreshOfflineUI() {
    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    const btn = document.getElementById('offlineToggleBtn');
    const icon = document.getElementById('offlineToggleIcon');
    const badge = document.getElementById('offlineBadge');
    if (!storyId || !btn || !window.NovelcastOffline) return;

    const offline = await window.NovelcastOffline.isStoryOffline(storyId);
    _isStoryOffline = offline;

    btn.classList.toggle('active', offline);
    btn.title = offline ? 'Refresh offline copy' : 'Available offline';
    if (icon) icon.className = offline ? 'fa-solid fa-rotate' : 'fa-solid fa-download';
    if (badge) badge.style.display = offline ? '' : 'none';
}

window.toggleStoryOffline = async function () {
    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    const btn = document.getElementById('offlineToggleBtn');
    if (!storyId || !window.NovelcastOffline) return;

    let chapterIds = [];
    try {
        chapterIds = JSON.parse(section.dataset.chapterIds || '[]');
    } catch (e) {
    }
    if (!chapterIds.length) {
        window.showNotification?.('No downloaded chapters to make available offline yet.', 'info', 5000);
        return;
    }

    const coverUrl = document.querySelector('.story-cover')?.getAttribute('src') || '';
    const title = document.querySelector('.story-title')?.textContent?.trim() || '';

    if (btn) btn.disabled = true;

    try {
        const alreadyOffline = _isStoryOffline;

        if (alreadyOffline) {
            window.showNotification?.('Refreshing offline copy…', 'info', 3000);
            const result = await window.NovelcastOffline.markStoryOffline(storyId, { title, coverUrl, chapterIds });
            const added = result?.addedChapters || 0;
            const removed = result?.removedChapters || 0;
            const detail = added || removed ? ` (${added} added, ${removed} removed)` : ' — already up to date';
            window.showNotification?.(`Offline copy refreshed${detail}.`, 'success', 5000);
        } else {
            window.showNotification?.('Downloading for offline reading…', 'info', 4000);
            await window.NovelcastOffline.markStoryOffline(storyId, { title, coverUrl, chapterIds });
            window.showNotification?.('Available offline.', 'success', 4000);
        }
    } catch (err) {
        window.showNotification?.(`Offline update failed: ${err.message}`, 'error', 6000) ?? alert(err.message);
    } finally {
        if (btn) btn.disabled = false;
        refreshOfflineUI();
    }
};

window.removeOfflineCopy = async function () {
    closeActiveDropdown();
    const section = document.querySelector('.story-page');
    const storyId = section?.dataset.storyId;
    if (!storyId || !window.NovelcastOffline) return;

    if (!confirm('Remove this story from offline storage? Cached chapters will be deleted from this device.')) return;

    try {
        await window.NovelcastOffline.removeStoryOffline(storyId);
        window.showNotification?.('Removed from offline storage.', 'success', 4000);
    } catch (err) {
        window.showNotification?.(`Remove failed: ${err.message}`, 'error', 6000);
    } finally {
        refreshOfflineUI();
    }
};

document.addEventListener('DOMContentLoaded', refreshOfflineUI);
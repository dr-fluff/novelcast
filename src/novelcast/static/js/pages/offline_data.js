/* novelcast/static/js/offline_data.js */

(function () {
    const storyList = document.getElementById('offline-story-list');
    const storyCount = document.getElementById('offline-story-count');
    const storageInfo = document.getElementById('offline-storage-info');
    const status = document.getElementById('offline-data-status');
    const clearButton = document.getElementById('clear-offline-data-btn');

    function formatMB(bytes) {
        return (bytes / 1024 / 1024).toFixed(1);
    }

    async function loadStorageInfo() {
        let usedMB = null;
        let quotaMB = null;

        if (navigator.storage?.estimate) {
            const estimate = await navigator.storage.estimate();
            usedMB = formatMB(estimate.usage || 0);
            quotaMB = formatMB(estimate.quota || 0);
        }

        const [chapterCache, shellCache] = await Promise.all([
            caches.open('novelcast-chapters-v1'),
            caches.open('novelcast-shell-v1'),
        ]);
        const [chapterEntries, shellEntries] = await Promise.all([chapterCache.keys(), shellCache.keys()]);

        storageInfo.innerHTML = `
            <div class="stats-card">
                <span class="stats-card__label">Storage used</span>
                <span class="stats-card__value">
                    ${usedMB !== null ? usedMB : '<span class="stats-card__value--empty">—</span>'}
                    ${usedMB !== null ? `<span class="stats-card__unit">MB${quotaMB !== null ? ` / ${quotaMB} MB` : ''}</span>` : ''}
                </span>
            </div>
            <div class="stats-card">
                <span class="stats-card__label">Cached app files</span>
                <span class="stats-card__value">${shellEntries.length}</span>
            </div>
            <div class="stats-card">
                <span class="stats-card__label">Cached chapters</span>
                <span class="stats-card__value">${chapterEntries.length}</span>
            </div>
        `;
    }

    async function loadOfflineStories() {
        const stories = await NovelcastOfflineDB.getAllOfflineStories();

        storyCount.textContent = stories.length || '';

        if (!stories.length) {
            storyList.innerHTML = `
                <div class="offline-empty">
                    <i class="fa-solid fa-cloud"></i>
                    <p>No stories are available offline yet.</p>
                    <p class="offline-empty__hint">Open a story and tap the download icon to save it for offline reading.</p>
                </div>
            `;
            return;
        }

        storyList.innerHTML = stories
            .map((story) => {
                const date = new Date(story.downloadedAt).toLocaleString();
                return `
                    <article class="offline-story-card">
                        ${
                            story.coverUrl
                                ? `<img class="offline-story-card__cover" src="${story.coverUrl}" alt="Cover for ${story.title}">`
                                : `<div class="offline-story-card__cover offline-story-card__cover--placeholder"><i class="fa-solid fa-book-open"></i></div>`
                        }
                        <div class="offline-story-card__body">
                            <h3 class="offline-story-card__title">${story.title}</h3>
                            <p class="offline-story-card__meta">
                                <i class="fa-solid fa-list"></i> ${story.chapterIds.length} chapters
                            </p>
                            <p class="offline-story-card__meta">
                                <i class="fa-regular fa-clock"></i> Downloaded ${date}
                            </p>
                        </div>
                    </article>
                `;
            })
            .join('');
    }

    async function clearOfflineData() {
        if (!confirm('Remove all offline stories and cached chapters?')) return;

        clearButton.disabled = true;
        status.textContent = '';

        try {
            const stories = await NovelcastOfflineDB.getAllOfflineStories();
            for (const story of stories) {
                await NovelcastOfflineDB.deleteOfflineStory(story.storyId);
            }

            await caches.delete('novelcast-chapters-v1');
            await caches.delete('novelcast-shell-v1');

            status.textContent = 'Offline data cleared.';
            status.classList.add('pg-status--success');

            await loadOfflineStories();
            await loadStorageInfo();
        } catch (err) {
            status.textContent = `Failed to clear offline data: ${err.message}`;
            status.classList.add('pg-status--error');
        } finally {
            clearButton.disabled = false;
        }
    }

    clearButton.addEventListener('click', clearOfflineData);

    (async function init() {
        await loadStorageInfo();
        await loadOfflineStories();
    })();
})();
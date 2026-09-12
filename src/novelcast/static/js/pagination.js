/* ── Pagination ───────────────────────────────────────────────────────── */

const PAGE_SIZE = 15;

/**
 * Build a paginator for a list of elements.
 * Uses CSS class `paged-hidden` instead of inline display so it never
 * conflicts with other JS that reads/sets element visibility.
 *
 * @param {object} opts
 * @param {() => HTMLElement[]} opts.getItems  - Function that re-queries items each time
 *                                               (handles sort reordering, dynamic adds).
 * @param {HTMLElement}  opts.pagerEl          - The .pagination div to render into.
 * @param {number}       [opts.pageSize]       - Items per page (default PAGE_SIZE).
 * @param {(items: unknown[]) => void} [opts.renderPage] - Custom page renderer.
 * @returns {{ show: (page: number) => void, refresh: () => void }}
 */
function createPaginator({ getItems, pagerEl, pageSize = PAGE_SIZE, renderPage = null }) {
    let currentPage = 1;

    function items() {
        return getItems();
    }
    function totalPages() {
        return Math.max(1, Math.ceil(items().length / pageSize));
    }

    function show(page) {
        const all = items();
        const total = Math.max(1, Math.ceil(all.length / pageSize));
        currentPage = Math.max(1, Math.min(page, total));

        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;

        if (renderPage) {
            renderPage(all.slice(start, end));
        } else {
            all.forEach((el, i) => {
                if (i >= start && i < end) {
                    el.classList.remove('paged-hidden');
                } else {
                    el.classList.add('paged-hidden');
                }
            });
        }

        renderButtons(total);
    }

    function renderButtons(total) {
        if (total <= 1) {
            pagerEl.style.display = 'none';
            return;
        }
        pagerEl.style.display = '';

        const cur = currentPage;

        // Always show: first, last, cur, cur±1 — ellipsis elsewhere
        const range = 3;

        const visible = new Set([1, total]);

        for (let i = -range; i <= range; i++) {
            const page = cur + i;
            if (page >= 1 && page <= total) {
                visible.add(page);
            }
        }
        const sorted = [...visible].sort((a, b) => a - b);

        let html = `<button class="page-btn" ${cur === 1 ? 'disabled' : ''} data-page="${cur - 1}" aria-label="Previous">&#8249;</button>`;

        let prev = 0;
        for (const p of sorted) {
            if (p - prev > 1) html += `<span class="page-ellipsis">…</span>`;
            html += `<button class="page-btn ${p === cur ? 'active' : ''}" data-page="${p}">${p}</button>`;
            prev = p;
        }

        html += `<button class="page-btn" ${cur === total ? 'disabled' : ''} data-page="${cur + 1}" aria-label="Next">&#8250;</button>`;

        pagerEl.innerHTML = html;
        pagerEl.querySelectorAll('.page-btn[data-page]').forEach((btn) => {
            btn.addEventListener('click', () => show(parseInt(btn.dataset.page, 10)));
        });
    }

    // Public API
    const api = {
        show,
        // Call after external reorder (e.g. cycleSort) to re-apply current page
        refresh() {
            show(1);
        },
    };

    show(1);
    return api;
}

/* ── Chapter pagination ───────────────────────────────────────────────── */

(function initChapterPagination() {
    const list = document.getElementById('chapterList');
    if (!list) return;

    let chapterData = [];
    try {
        chapterData = JSON.parse(list.dataset.chapterData || '[]');
    } catch (error) {
        console.error('Could not parse chapter data', error);
    }

    const readChapters = new Set(JSON.parse(list.dataset.readChapters || '[]'));
    const lastChapterId = Number(list.dataset.lastChapterId) || null;
    const storyId = list.dataset.storyId;
    let sortMode = document.querySelector('.story-page')?.dataset.chapterSort || 'asc';

    function sortedItems() {
        return [...chapterData].sort((a, b) => {
            const difference = (Number(a.chapter_number) || 0) - (Number(b.chapter_number) || 0);
            return sortMode === 'desc' ? -difference : difference;
        });
    }

    function renderChapter(item) {
        const chapterId = Number(item.id);
        const isRead = readChapters.has(chapterId);
        const isCurrent = lastChapterId === chapterId;
        const row = document.createElement('li');
        row.className = `chapter-item${isRead ? ' chapter-read' : ''}${isCurrent ? ' chapter-current' : ''}`;
        row.dataset.chapterId = String(chapterId);
        row.dataset.chapterNumber = String(item.chapter_number);
        const addedDate = item.created_at ? new Date(item.created_at).toISOString().slice(0, 10) : '';
        row.innerHTML = `
            <a href="/chapter?story_id=${encodeURIComponent(storyId)}&chapter_id=${chapterId}" class="chapter-link">
                <div class="chapter-main">
                    <span class="chapter-number">Chapter ${item.chapter_number}</span>
                    <span class="chapter-name"></span>
                    ${isCurrent ? '<span class="chapter-current-badge" title="You\'re currently reading this chapter"><i class="fa-solid fa-bookmark"></i> Continue</span>' : ''}
                </div>
                <span class="chapter-status">
                    <span class="chapter-status-label${isRead ? ' status-read' : ''}">${isRead ? 'Read' : 'Unread'}</span>
                    ${addedDate ? `<span class="chapter-added-date">Added ${addedDate}</span>` : ''}
                </span>
            </a>`;
        row.querySelector('.chapter-name').textContent = item.title || 'Untitled chapter';
        return row;
    }

    const pagerEl = document.createElement('div');
    pagerEl.className = 'pagination';
    pagerEl.id = 'chapterPager';
    list.insertAdjacentElement('afterend', pagerEl);

    // Re-query each time so cycleSort() DOM reordering is respected
    const paginator = createPaginator({
        getItems: () => sortedItems(),
        pagerEl,
        pageSize: PAGE_SIZE,
        renderPage: (items) => {
            list.replaceChildren(...items.map(renderChapter));
        },
    });

    window.chapterPaginator = paginator;
    window.setChapterSortMode = (mode) => {
        sortMode = mode;
        paginator.refresh();
    };
    window.showChapterId = (chapterId) => {
        const index = sortedItems().findIndex((item) => Number(item.id) === Number(chapterId));
        if (index >= 0) paginator.show(Math.floor(index / PAGE_SIZE) + 1);
    };

    // Hook into cycleSort if it exists: after sort, reset to page 1
    const _origCycleSort = window.cycleSort;
    if (typeof _origCycleSort === 'function') {
        window.cycleSort = function (...args) {
            _origCycleSort.apply(this, args);
            // Small delay so the sort has time to reorder the DOM
            setTimeout(() => paginator.refresh(), 50);
        };
    }

})();

/* ── File table pagination ────────────────────────────────────────────── */

(function initFilePagination() {
    const tbody = document.querySelector('.file-table tbody');
    if (!tbody) return;
    if (tbody.querySelectorAll('.file-row').length <= PAGE_SIZE) return;

    const body = tbody.closest('.collapsible-body');
    if (!body) return;

    const pagerEl = document.createElement('div');
    pagerEl.className = 'pagination';
    pagerEl.id = 'filePager';
    body.appendChild(pagerEl);

    const paginator = createPaginator({
        getItems: () => [...tbody.querySelectorAll('.file-row')],
        pagerEl,
    });

    // After deleteFile removes a row, refresh pagination
    const _origDeleteFile = window.deleteFile;
    if (typeof _origDeleteFile === 'function') {
        window.deleteFile = async function (...args) {
            await _origDeleteFile.apply(this, args);
            paginator.refresh();
        };
    }

    window.filePaginator = paginator;
})();

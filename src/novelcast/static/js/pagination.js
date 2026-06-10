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
 * @returns {{ show: (page: number) => void, refresh: () => void }}
 */
function createPaginator({ getItems, pagerEl, pageSize = PAGE_SIZE }) {
    let currentPage = 1;

    function items()      { return getItems(); }
    function totalPages() { return Math.max(1, Math.ceil(items().length / pageSize)); }

    function show(page) {
        const all   = items();
        const total = Math.max(1, Math.ceil(all.length / pageSize));
        currentPage = Math.max(1, Math.min(page, total));

        const start = (currentPage - 1) * pageSize;
        const end   = start + pageSize;

        all.forEach((el, i) => {
            if (i >= start && i < end) {
                el.classList.remove("paged-hidden");
            } else {
                el.classList.add("paged-hidden");
            }
        });

        renderButtons(total);
    }

    function renderButtons(total) {
        if (total <= 1) {
            pagerEl.style.display = "none";
            return;
        }
        pagerEl.style.display = "";

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

        let html = `<button class="page-btn" ${cur === 1 ? "disabled" : ""} data-page="${cur - 1}" aria-label="Previous">&#8249;</button>`;

        let prev = 0;
        for (const p of sorted) {
            if (p - prev > 1) html += `<span class="page-ellipsis">…</span>`;
            html += `<button class="page-btn ${p === cur ? "active" : ""}" data-page="${p}">${p}</button>`;
            prev = p;
        }

        html += `<button class="page-btn" ${cur === total ? "disabled" : ""} data-page="${cur + 1}" aria-label="Next">&#8250;</button>`;

        pagerEl.innerHTML = html;
        pagerEl.querySelectorAll(".page-btn[data-page]").forEach(btn => {
            btn.addEventListener("click", () => show(parseInt(btn.dataset.page, 10)));
        });
    }

    // Public API
    const api = {
        show,
        // Call after external reorder (e.g. cycleSort) to re-apply current page
        refresh() { show(1); },
    };

    show(1);
    return api;
}

/* ── Chapter pagination ───────────────────────────────────────────────── */

(function initChapterPagination() {
    const list = document.getElementById("chapterList");
    if (!list) return;
    if (list.querySelectorAll(".chapter-item").length <= PAGE_SIZE) return;

    const pagerEl = document.createElement("div");
    pagerEl.className = "pagination";
    pagerEl.id = "chapterPager";
    list.insertAdjacentElement("afterend", pagerEl);

    // Re-query each time so cycleSort() DOM reordering is respected
    const paginator = createPaginator({
        getItems: () => [...list.querySelectorAll(".chapter-item")],
        pagerEl,
    });

    // Hook into cycleSort if it exists: after sort, reset to page 1
    const _origCycleSort = window.cycleSort;
    if (typeof _origCycleSort === "function") {
        window.cycleSort = function (...args) {
            _origCycleSort.apply(this, args);
            // Small delay so the sort has time to reorder the DOM
            setTimeout(() => paginator.refresh(), 50);
        };
    }

    // Expose so story_page.js can call window.chapterPaginator.refresh() if needed
    window.chapterPaginator = paginator;
})();

/* ── File table pagination ────────────────────────────────────────────── */

(function initFilePagination() {
    const tbody = document.querySelector(".file-table tbody");
    if (!tbody) return;
    if (tbody.querySelectorAll(".file-row").length <= PAGE_SIZE) return;

    const body = tbody.closest(".collapsible-body");
    if (!body) return;

    const pagerEl = document.createElement("div");
    pagerEl.className = "pagination";
    pagerEl.id = "filePager";
    body.appendChild(pagerEl);

    const paginator = createPaginator({
        getItems: () => [...tbody.querySelectorAll(".file-row")],
        pagerEl,
    });

    // After deleteFile removes a row, refresh pagination
    const _origDeleteFile = window.deleteFile;
    if (typeof _origDeleteFile === "function") {
        window.deleteFile = async function (...args) {
            await _origDeleteFile.apply(this, args);
            paginator.refresh();
        };
    }

    window.filePaginator = paginator;
})();
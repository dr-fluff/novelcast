// novelcast/static/js/metadata_panel.js
// API is mounted at /api/stories/…

(function () {
    "use strict";

    let storyId       = null;
    let currentAuthorId = null;
    let saveCloseTimer = null;

    function el(id) { return document.getElementById(id); }

    function setVal(id, value) {
        const node = el(id);
        if (node) node.value = value;
    }

    function getVal(id) {
        const node = el(id);
        return node ? node.value.trim() : "";
    }

    // ── Open / Close ───────────────────────────────────────────────────────

    function clearSaveCloseTimer() {
        if (saveCloseTimer) {
            clearTimeout(saveCloseTimer);
            saveCloseTimer = null;
        }
    }

    window.openMetaPanel = async function () {
        const page = document.querySelector(".story-page");
        storyId = page ? page.dataset.storyId : null;
        if (!storyId) return;

        clearSaveCloseTimer();
        el("metaPanel").classList.add("open");
        el("metaPanel").setAttribute("aria-hidden", "false");
        el("metaPanelBackdrop").classList.add("open");
        document.body.style.overflow = "hidden";

        setStatus("", "");
        await loadData();
    };

    window.closeMetaPanel = function () {
        clearSaveCloseTimer();
        el("metaPanel").classList.remove("open");
        el("metaPanel").setAttribute("aria-hidden", "true");
        el("metaPanelBackdrop").classList.remove("open");
        document.body.style.overflow = "";
    };

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && el("metaPanel")?.classList.contains("open")) {
            closeMetaPanel();
        }
    });

    // ── Load ───────────────────────────────────────────────────────────────

    async function loadData() {
        // Pull from rendered DOM first
        const titleEl  = document.querySelector(".story-title");
        const sourceEl = document.querySelector(".meta-link, .story-description a");

        setVal("metaTitle",     titleEl  ? titleEl.textContent.trim() : "");
        setVal("metaSourceUrl", sourceEl ? sourceEl.href              : "");

        // Try to load full story metadata from API
        try {
            const sres = await fetch(`/api/stories/${storyId}`);
            if (sres.ok) {
                const sdata = await sres.json();
                const st = sdata.story || {};
                setVal('metaTitle', st.title || getVal('metaTitle'));
                setVal('metaSubtitle', st.subtitle || '');
                setVal('metaDescription', st.description || '');
                setVal('metaPublishYear', st.publish_year || '');
                setVal('metaLanguage', st.language || '');
                setVal('metaSourceUrl', st.source_url || getVal('metaSourceUrl'));
                if (el('metaAutoUpdate')) el('metaAutoUpdate').checked = Boolean(st.auto_update);
                if (el('metaHideAuthorNotes')) el('metaHideAuthorNotes').checked = Boolean(st.hide_author_notes);
                renderMetaTagList('metaSeriesWrap', st.series_list ?? parseCommaList(st.series));
                renderMetaTagList('metaGenresWrap', st.genres_list ?? parseCommaList(st.genres));
                renderMetaTagList('metaTagsWrap', st.tags_list ?? parseCommaList(st.tags));
            }
        } catch (_) {}

        // Reset
        currentAuthorId = null;
        setVal("metaAuthorName", "");

        // Load authors from API
        try {
            const res = await fetch(`/api/stories/${storyId}/authors`);
            if (res.ok) {
                const data    = await res.json();
                const authors = data.authors || [];
                if (authors.length > 0) {
                    const a = authors[0];
                    currentAuthorId = a.id;
                    setVal("metaAuthorName", a.name || "");
                }
            }
        } catch (_) { /* non-fatal */ }

        // Fallback: author name from DOM
        if (!getVal("metaAuthorName")) {
            const authorEl = document.querySelector(".story-author-link, .story-author-name");
            if (authorEl) {
                const txt = authorEl.textContent.trim();
                setVal("metaAuthorName", txt === "Unknown author" ? "" : txt);
            }
        }
    }

    function parseCommaList(raw) {
        if (!raw) return [];
        return String(raw)
            .split(/,|;/)
            .map(item => item.trim())
            .filter(Boolean);
    }

    function renderMetaTagList(wrapperId, values) {
        const container = el(wrapperId);
        if (!container) return;
        container.querySelectorAll('.meta-tag').forEach(el => el.remove());
        const addBtn = container.querySelector('.meta-tag-add');
        const list = Array.isArray(values) ? values : [];
        list.forEach(value => {
            const tag = document.createElement('span');
            tag.className = 'meta-tag';
            tag.dataset.value = value;
            tag.textContent = value;

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'meta-tag-remove';
            remove.setAttribute('aria-label', 'Remove tag');
            remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            remove.onclick = () => tag.remove();

            tag.appendChild(remove);
            if (addBtn) container.insertBefore(tag, addBtn);
        });
    }

    function collectMetaTagList(wrapperId) {
        const container = el(wrapperId);
        if (!container) return [];
        const values = new Set();
        container.querySelectorAll('.meta-tag').forEach(tag => {
            const value = (tag.dataset.value || '').trim();
            if (value) values.add(value);
        });

        const input = container.querySelector('.meta-tag-entry');
        if (input) {
            parseCommaList(input.value).forEach(value => values.add(value));
        }

        return Array.from(values);
    }

    window.addMetaTagFromInput = function (wrapperId, inputId) {
        const input = el(inputId);
        if (!input) return;
        const rawValue = input.value.trim();
        if (!rawValue) return;

        parseCommaList(rawValue).forEach(value => addMetaTag(wrapperId, value));
        input.value = "";
        input.focus();
    };

    function addMetaTag(wrapperId, value) {
        const container = el(wrapperId);
        if (!container) return;

        const normalized = String(value).trim();
        if (!normalized) return;

        const existing = Array.from(container.querySelectorAll('.meta-tag')).some(tag => tag.dataset.value === normalized);
        if (existing) return;

        const tag = document.createElement('span');
        tag.className = 'meta-tag';
        tag.dataset.value = normalized;
        tag.textContent = normalized;

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'meta-tag-remove';
        remove.setAttribute('aria-label', 'Remove tag');
        remove.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        remove.onclick = () => tag.remove();

        tag.appendChild(remove);
        const addBtn = container.querySelector('.meta-tag-add');
        if (addBtn) container.insertBefore(tag, addBtn);
        else container.appendChild(tag);
    }

    // ── Save ───────────────────────────────────────────────────────────────

    window.saveMetadata = async function () {
        const saveBtn = el("metaSaveBtn");
        if (saveBtn) saveBtn.disabled = true;
        setStatus("Saving…", "");

        const title       = getVal("metaTitle");
        const authorName  = getVal("metaAuthorName");
        const sourceUrl   = getVal("metaSourceUrl") || null;
        const subtitle    = getVal("metaSubtitle") || null;
        const description = getVal("metaDescription") || null;
        const publishYear = getVal("metaPublishYear") || null;
        const language    = getVal("metaLanguage") || null;
        const series      = collectMetaTagList('metaSeriesWrap');
        const genres      = collectMetaTagList('metaGenresWrap');
        const tags        = collectMetaTagList('metaTagsWrap');
        const authorNames = parseCommaList(authorName);

        if (!title) {
            setStatus("Title is required.", "error");
            if (saveBtn) saveBtn.disabled = false;
            return;
        }

        try {
            // 1 — Save story metadata
            const storyRes = await fetch(`/api/stories/${storyId}/metadata`, {
                method:  "PATCH",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({
                    title,
                    author: authorName || null,
                    subtitle: subtitle,
                    description: description,
                    publish_year: publishYear ? parseInt(publishYear, 10) : null,
                    language: language,
                    series: series,
                    genres: genres,
                    tags: tags,
                    source_url: sourceUrl,
                    auto_update: el('metaAutoUpdate')?.checked || false,
                    hide_author_notes: el('metaHideAuthorNotes')?.checked || false,
                }),
            });
            if (!storyRes.ok) {
                const err = await storyRes.json().catch(() => ({}));
                throw new Error(err.detail || "Failed to save story");
            }
            clearSaveCloseTimer();
            const storyData = await storyRes.json();

            // 2 — Re-fetch author id if missing
            if (!currentAuthorId && authorName) {
                try {
                    const ar = await fetch(`/api/stories/${storyId}/authors`);
                    if (ar.ok) {
                        const ad = await ar.json();
                        if (ad.authors?.length) currentAuthorId = ad.authors[0].id;
                    }
                } catch (_) {}
            }

            // 3 — Save author only for a single author entry.
            if (currentAuthorId && authorName && authorNames.length === 1) {
                const authorRes = await fetch(
                    `/api/stories/${storyId}/authors/${currentAuthorId}`,
                    {
                        method:  "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body:    JSON.stringify({ name: authorName, bio: null }),
                    }
                );
                if (!authorRes.ok) {
                    const err = await authorRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to save author");
                }
            }

            // 5 — Update DOM
            _updatePageDOM(storyData.story, authorName, sourceUrl);
            setStatus("Saved!", "success");
            saveCloseTimer = setTimeout(() => {
                setStatus("", "");
                closeMetaPanel();
            }, 1200);

        } catch (err) {
            clearSaveCloseTimer();
            setStatus(err.message || "Something went wrong.", "error");
        } finally {
            if (saveBtn) saveBtn.disabled = false;
        }
    };

    // ── DOM patch after save ───────────────────────────────────────────────

    function _updatePageDOM(story, authorName, sourceUrl) {
        if (!story) return;

        const titleEl = document.querySelector(".story-title");
        if (titleEl) titleEl.textContent = story.title || "";

        const authorContainer = document.querySelector(".story-author");
        const isMultiAuthor = authorName && authorName.includes(",");
        if (isMultiAuthor) {
            if (authorContainer) authorContainer.textContent = `by ${authorName}`;
        } else {
            const authorLinkEl = document.querySelector(".story-author-link");
            const authorNameEl = document.querySelector(".story-author-name");
            if (authorLinkEl)      authorLinkEl.textContent = authorName || "Unknown author";
            else if (authorNameEl) authorNameEl.textContent = authorName || "Unknown author";
        }

        // subtitle and series (there are two .story-subtitle elements in template)
        const subtitleEls = document.querySelectorAll('.story-subtitle');
        if (subtitleEls.length > 0) {
            if (story.subtitle) subtitleEls[0].textContent = story.subtitle;
            else subtitleEls[0].textContent = '';
        }
        if (subtitleEls.length > 1) {
            if (story.series) subtitleEls[1].textContent = story.series;
            else subtitleEls[1].textContent = '';
        }

        // description
        const descEl = document.getElementById('storyDescription');
        if (descEl) descEl.textContent = story.description || '';

        // meta grid: rebuild rows from known fields
        const metaGrid = document.querySelector('.story-meta-grid');
        if (metaGrid) {
            metaGrid.innerHTML = '';

            function addRow(label, value) {
                if (!value && value !== 0) return;
                const row = document.createElement('div');
                row.className = 'meta-row';

                const dt = document.createElement('dt');
                dt.textContent = label;

                const dd = document.createElement('dd');
                if (label === 'Duration' || label === 'Size') {
                    dd.textContent = value;
                } else if (label === 'Source') {
                    const link = document.createElement('a');
                    link.href = story.source_url;
                    link.target = '_blank';
                    link.rel = 'noreferrer';
                    link.className = 'meta-link';
                    link.textContent = story.source_url;
                    dd.appendChild(link);
                } else {
                    const items = String(value).split(/,\s*/).map(item => item.trim()).filter(Boolean);
                    items.forEach((item, index) => {
                        const link = document.createElement('a');
                        link.className = 'meta-link';
                        link.href = '/?q=' + encodeURIComponent(`${label},${item}`);
                        link.textContent = item;
                        if (index) dd.appendChild(document.createTextNode(', '));
                        dd.appendChild(link);
                    });
                }

                row.appendChild(dt);
                row.appendChild(dd);
                metaGrid.appendChild(row);
            }

            addRow('Narrators', story.narrators);
            addRow('Publish year', story.publish_year);
            addRow('Publisher', story.publisher);
            addRow('Genres', story.genres);
            addRow('Tags', story.tags);
            addRow('Language', story.language);
            addRow('Duration', story.duration);
            addRow('Size', story.size);
            if (story.source_url) {
                const row = document.createElement('div');
                row.className = 'meta-row';

                const dt = document.createElement('dt');
                dt.textContent = 'Source';

                const dd = document.createElement('dd');
                const link = document.createElement('a');
                link.href = story.source_url;
                link.target = '_blank';
                link.rel = 'noreferrer';
                link.className = 'meta-link';
                link.textContent = story.source_url;
                dd.appendChild(link);

                row.appendChild(dt);
                row.appendChild(dd);
                metaGrid.appendChild(row);
            } else if (!story.narrators && !story.publish_year) {
                const row = document.createElement('div');
                row.className = 'meta-row';

                const dt = document.createElement('dt');
                dt.textContent = 'Source';

                const dd = document.createElement('dd');
                dd.className = 'meta-muted';
                dd.textContent = 'No source URL available.';

                row.appendChild(dt);
                row.appendChild(dd);
                metaGrid.appendChild(row);
            }
        }

        // source link (if present elsewhere)
        const metaLink = document.querySelector('.meta-link');
        if (metaLink && sourceUrl) {
            metaLink.href = sourceUrl;
            metaLink.textContent = sourceUrl;
        }

        document.title = `${story.title} · NovelCast`;
    }

    // ── Tab switching ──────────────────────────────────────────────────────

    window.switchTab = function (btn, panelId) {
        document.querySelectorAll(".meta-tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".meta-tab-panel").forEach(p => p.classList.add("hidden"));
        btn.classList.add("active");
        const panel = document.getElementById(panelId);
        if (panel) panel.classList.remove("hidden");
    };

    // ── Status helper ──────────────────────────────────────────────────────

    function setStatus(msg, cls) {
        const s = el("metaSaveStatus");
        if (!s) return;
        s.textContent = msg;
        s.className   = "meta-save-status" + (cls ? " " + cls : "");
    }

})();

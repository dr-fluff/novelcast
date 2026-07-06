// novelcast/static/js/unified-panel.js
// Handles: add_story, metadata, author panels with config-driven behavior

const UnifiedPanel = (() => {
    "use strict";

    let panelStates = {}; // Track state per panel ID
    let handlers = {}; // Panel-type-specific handlers

    const $ = (id) => document.getElementById(id);
    const log = (type, ...args) => console.log(`[Panel:${type}]`, ...args);
    const err = (type, ...args) => console.error(`[Panel:${type}]`, ...args);

    // ─────────────────────────────────────────────────────────────────
    // PANEL STATE MANAGEMENT
    // ─────────────────────────────────────────────────────────────────

    function getState(panelId) {
        if (!panelStates[panelId]) {
            panelStates[panelId] = { isLoading: false, panelType: null };
        }
        return panelStates[panelId];
    }

    function setState(panelId, updates) {
        Object.assign(getState(panelId), updates);
    }

    // ─────────────────────────────────────────────────────────────────
    // CORE PANEL OPERATIONS
    // ─────────────────────────────────────────────────────────────────

    function setOpen(panelId, open) {
        const panel = $(`${panelId}`);
        const backdrop = $(`${panelId}-backdrop`);

        if (!panel || !backdrop) {
            console.warn(`Panel or backdrop not found for ${panelId}`);
            return;
        }

        panel.classList.toggle("open", open);
        backdrop.classList.toggle("open", open);
        panel.setAttribute("aria-hidden", open ? "false" : "true");
        document.body.style.overflow = open ? "hidden" : "";
    }

    // ─────────────────────────────────────────────────────────────────
    // TAB SWITCHING
    // ─────────────────────────────────────────────────────────────────

    function switchTab(panelId, tabId, tabButton) {
        const panel = $(panelId);
        if (!panel) return;

        // Deactivate all tabs and hide all content
        panel.querySelectorAll(".unified-panel-tab").forEach((t) => {
            t.classList.remove("active");
        });
        panel.querySelectorAll(".unified-panel-content").forEach((c) => {
            c.style.display = "none";
        });

        // Activate clicked tab and show content
        if (tabButton) tabButton.classList.add("active");
        const contentEl = $(`${tabId}-${panelId}`);
        if (contentEl) contentEl.style.display = "";
    }

    // ─────────────────────────────────────────────────────────────────
    // CONTEXT-AWARE ACTION BUTTON
    // ─────────────────────────────────────────────────────────────────

    function getActiveTabIndex(panelId) {
        const panel = $(panelId);
        if (!panel) return 0;

        const contents = panel.querySelectorAll(".unified-panel-content");
        for (let i = 0; i < contents.length; i++) {
            if (contents[i].style.display !== "none") {
                return i;
            }
        }
        return 0;
    }

    function updateActionButton(panelId) {
        const state = getState(panelId);
        const btn = $(`addStoryActionBtn-${panelId}`);
        if (!btn || state.panelType !== "add_story") return;

        btn.style.display = "";

        const tabIndex = getActiveTabIndex(panelId);

        switch (tabIndex) {
            case 0: // URL tab
                btn.innerHTML = '<i class="fa-solid fa-download"></i> Preview';
                btn.disabled = false;
                btn.onclick = () => handlers.add_story.previewMetadata(panelId);
                break;
            case 1: // Metadata tab
                btn.innerHTML = '<i class="fa-solid fa-arrow-right"></i> Select Chapters';
                btn.disabled = false;
                btn.onclick = () => handlers.add_story.switchTabByIndex(panelId, 2);
                break;
            case 2: // Chapters tab
                btn.innerHTML = '<i class="fa-solid fa-download"></i> Download';
                btn.disabled = false;
                btn.onclick = () => handlers.add_story.confirm(panelId);
                break;
            case 3: // Download tab
                btn.style.display = "none";
                break;
        }
    }

    
    
    // ─────────────────────────────────────────────────────────────────
    // TAG HELPERS
    // ─────────────────────────────────────────────────────────────────

    function getTagValues(containerId, panelId) {
        const wrap = $(`${containerId}-${panelId}`);
        if (!wrap) return [];

        return Array.from(wrap.querySelectorAll(".tag"))
            .map((el) => el.dataset.value || el.textContent.split("\n")[0].trim())
            .filter(Boolean);
    }

    function parseCommaList(raw) {
        if (!raw) return [];
        return String(raw)
            .split(/,|;/)
            .map((item) => item.trim())
            .filter(Boolean);
    }

    function renderTagList(containerId, panelId, values) {
        const container = $(`${containerId}-${panelId}`);
        if (!container) return;
        
        // Remove existing tags
        container.querySelectorAll(".tag").forEach((el) => el.remove());
        
        const addBtn = container.querySelector(".tag-add");
        const list = Array.isArray(values) ? values : [];
        
        list.forEach((value) => {
            const tag = document.createElement("span");
            tag.className = "tag";
            tag.dataset.value = value;
            tag.innerHTML = value + ' <button type="button" class="tag-remove" aria-label="Remove"><i class="fa-solid fa-xmark"></i></button>';
            
            tag.querySelector(".tag-remove").onclick = () => tag.remove();
            
            if (addBtn) container.insertBefore(tag, addBtn);
            else container.appendChild(tag);
        });
    }

    function collectTagList(containerId, panelId) {
        const container = $(`${containerId}-${panelId}`);
        if (!container) return [];
        
        const values = new Set();
        container.querySelectorAll(".tag").forEach((tag) => {
            const value = (tag.dataset.value || "").trim();
            if (value) values.add(value);
        });

        // Also collect from input
        const input = container.querySelector(".tag-entry");
        if (input) {
            parseCommaList(input.value).forEach((value) => values.add(value));
        }

        return Array.from(values);
    }

    // ─────────────────────────────────────────────────────────────────
    // FORM HELPERS
    // ─────────────────────────────────────────────────────────────────

    function getVal(fieldId, panelId) {
        const node = $(`${fieldId}-${panelId}`);
        return node ? node.value.trim() : "";
    }

    function setVal(fieldId, panelId, value) {
        const node = $(`${fieldId}-${panelId}`);
        if (node) node.value = value || "";
    }

    function setStatus(panelId, msg, cls) {
        const statusEl = $(`status-${panelId}`);
        if (!statusEl) return;
        statusEl.textContent = msg;
        statusEl.className = "unified-panel-status" + (cls ? " " + cls : "");
    }

    // ─────────────────────────────────────────────────────────────────
    // SAFE JSON FETCH
    // ─────────────────────────────────────────────────────────────────

    async function fetchJSON(url, options = {}) {
        const res = await fetch(url, options);
        const text = await res.text();

        if (!text) {
            throw new Error("Empty response from server");
        }

        try {
            return { ok: res.ok, data: JSON.parse(text), status: res.status };
        } catch (e) {
            console.error("Non-JSON response:", text);
            throw new Error("Server did not return valid JSON");
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // PANEL TYPE: ADD_STORY
    // ─────────────────────────────────────────────────────────────────

    handlers.add_story = {
        name: "add_story",
        
        open(panelId) {
            setState(panelId, { panelType: "add_story", selectedChapters: [] });
            setStatus(panelId, "", "");

            setVal("addStoryChapterRegex", panelId, "");
            
            // Reset all fields
            setVal("addStoryUrl", panelId, "");
            setVal("addStoryTitle", panelId, "");
            setVal("addStoryAuthor", panelId, "");
            setVal("addStorySubtitle", panelId, "");
            setVal("addStoryDescription", panelId, "");
            setVal("addStoryPublishYear", panelId, "");
            setVal("addStoryLanguage", panelId, "");
            setVal("addStoryFilenamePattern", panelId, "");  
            const contentSourceEl = $(`addStoryContentSource-${panelId}`);
            if (contentSourceEl) contentSourceEl.value = "file"; 
            renderTagList("addStoryGenresWrap", panelId, []);
            renderTagList("addStoryTagsWrap", panelId, []);
            renderTagList("addStorySeriesWrap", panelId, []);
            
            const chaptersList = $(`chaptersList-${panelId}`);
            if (chaptersList) chaptersList.innerHTML = "";
            
            const countEl = $(`chapterCountValue-${panelId}`);
            if (countEl) countEl.textContent = "—";

            this.switchTabByIndex(panelId, 0);
            setOpen(panelId, true);

        },

        close(panelId) {
            setOpen(panelId, false);
            setState(panelId, { selectedChapters: [] });
        },

        async previewMetadata(panelId) {
            const state = getState(panelId);
            if (state.isLoading) return;

            const url = getVal("addStoryUrl", panelId);
            if (!url) {
                setStatus(panelId, "URL is required", "error");
                return;
            }
            
            const chapterRegex = getVal("addStoryChapterRegex", panelId) || null;
            const filenamePattern = getVal("addStoryFilenamePattern", panelId) || null;

            setState(panelId, { isLoading: true });
            setStatus(panelId, "Previewing…", "");

            try {
                const result = await fetchJSON("/api/stories/preview", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, chapter_regex: chapterRegex }),
                    filename_pattern: filenamePattern,
                });

                if (!result.ok) {
                    throw new Error(result.data.detail || "Preview failed");
                }

                const data = result.data;
                
                // Populate fields
                setVal("addStoryTitle", panelId, data.title || "");
                setVal("addStoryAuthor", panelId, data.author || "");
                setVal("addStorySubtitle", panelId, data.subtitle || "");
                setVal("addStoryDescription", panelId, data.description || "");
                setVal("addStoryPublishYear", panelId, data.publish_year || "");
                setVal("addStoryLanguage", panelId, data.language || "");

                renderTagList("addStoryGenresWrap", panelId, data.genres || []);
                renderTagList("addStoryTagsWrap", panelId, data.tags || []);
                renderTagList("addStorySeriesWrap", panelId, data.series || []);
                
                setState(panelId, { 
                    isLoading: false,
                    storySiteId: data.story_site_id || null,
                });
                // Update chapter count
                const countEl = $(
                    `chapterCountValue-${panelId}`
                );
                if (countEl) countEl.textContent = data.chapter_count ?? "—";

                // Display chapters
                if (data.chapters && data.chapters.length > 0) {
                    this.displayChapters(panelId, data.chapters);
                }

                // Switch to metadata tab
                this.switchTabByIndex(panelId, 1);

                setStatus(panelId, "", "");
            } catch (e) {
                err("add_story", e);
                setStatus(panelId, e.message, "error");
            } finally {
                setState(panelId, { isLoading: false });
            }
        },

        handleCoverFileSelect(panelId, inputEl) {
            handlers.metadata?.handleCoverFileSelect(panelId, inputEl);
        },
        toggleCoverUrlInput(panelId) {
            handlers.metadata?.toggleCoverUrlInput(panelId);
        },
        fetchCoverFromUrl(panelId) {
            handlers.metadata?.fetchCoverFromUrl(panelId);
        },
        removeCover(panelId) {
            handlers.metadata?.removeCover(panelId);
        },

        displayChapters(panelId, chapters) {
            const list = $(`chaptersList-${panelId}`);
            if (!list) return;

            list.innerHTML = chapters
                .map(
                    (ch, idx) => `
                <div class="chapter-item${ch.locked ? " chapter-locked" : ""}">
                    <input 
                        type="checkbox" 
                        id="ch-${idx}-${panelId}"
                        data-chapter-number="${ch.number}"
                        ${ch.locked ? "disabled" : "checked"}
                        onchange="UnifiedPanel.updateChapterSelection('${panelId}')"
                    />
                    <label for="ch-${idx}-${panelId}">
                        <span class="chapter-number">Chapter ${ch.number}</span>
                        <span class="chapter-title">${ch.title || "(no title)"}</span>
                        ${ch.locked ? '<i class="fa-solid fa-lock chapter-lock-icon" title="Requires Patreon access"></i>' : ""}
                    </label>
                </div>
            `
                )
                .join("");

            const countEl = $(`chapterTotalCount-${panelId}`);
            if (countEl) countEl.textContent = chapters.length;
            
            this.updateChapterSelection(panelId);
        },

        updateChapterSelection(panelId) {
            const list = $(`chaptersList-${panelId}`);
            if (!list) return;

            const checkboxes = list.querySelectorAll('input[type="checkbox"]');
            const selected = Array.from(checkboxes)
                .filter((cb) => cb.checked)
                .map((cb) => parseInt(cb.dataset.chapterNumber));

            setState(panelId, { selectedChapters: selected });

            const countEl = $(`chapterSelectCount-${panelId}`);
            if (countEl) countEl.textContent = selected.length;
        },

        selectAllChapters(panelId) {
            const list = $(`chaptersList-${panelId}`);
            if (!list) return;
            list.querySelectorAll('input[type="checkbox"]:not(:disabled)').forEach((cb) => {
                cb.checked = true;
            });
            this.updateChapterSelection(panelId);
        },  

        deselectAllChapters(panelId) {
            const list = $(`chaptersList-${panelId}`);
            if (!list) return;
            list.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
                cb.checked = false;
            });
            this.updateChapterSelection(panelId);
        },

        switchTabByIndex(panelId, index) {
            const panel = $(panelId);
            const tabs = panel.querySelectorAll(".unified-panel-tab");
            const contents = panel.querySelectorAll(".unified-panel-content");

            tabs.forEach((t) => t.classList.remove("active"));
            contents.forEach((c) => (c.style.display = "none"));

            if (tabs[index]) tabs[index].classList.add("active");
            if (contents[index]) contents[index].style.display = "";

            updateActionButton(panelId);
        },

        async confirm(panelId) {
            const state = getState(panelId);
            if (state.isLoading) return;

            setState(panelId, { isLoading: true });

            // Switch to download tab briefly so user sees it triggered,
            // then close the panel — download continues in background
            this.switchTabByIndex(panelId, 3);
            
            setTimeout(() => this.close(panelId), 400);  // brief flash then close

            try {
                const payload = {
                    url: getVal("addStoryUrl", panelId) || "",
                    title: getVal("addStoryTitle", panelId) || "",
                    author: getVal("addStoryAuthor", panelId) || "",
                    subtitle: getVal("addStorySubtitle", panelId) || "",
                    description: getVal("addStoryDescription", panelId) || "",
                    publish_year: getVal("addStoryPublishYear", panelId)
                        ? Number(getVal("addStoryPublishYear", panelId))
                        : null,
                    language: getVal("addStoryLanguage", panelId) || "",
                    series: collectTagList("addStorySeriesWrap", panelId),
                    genres: collectTagList("addStoryGenresWrap", panelId),
                    tags: collectTagList("addStoryTagsWrap", panelId),
                    chapter_regex: getVal("addStoryChapterRegex", panelId) || null,
                    content_source: $(`addStoryContentSource-${panelId}`)?.value || null,
                    filename_pattern: getVal("addStoryFilenamePattern", panelId) || null,
                    auto_update: $(`addStoryAutoUpdate-${panelId}`)?.checked || false,
                    hide__author_notes: $("metaHideAuthorNotes-")?.checked || true,
                    selected_chapters: state.selectedChapters.length > 0
                        ? state.selectedChapters
                        : null,
                };

                log("add_story", "Payload:", payload);

                const result = await fetchJSON("/api/stories/add", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!result.ok) {
                    throw new Error(result.data.detail || "Failed to add story");
                }

                // Done — panel is already closed, nothing more to do here.
                // The backend will emit a WebSocket event when download completes.

            } catch (e) {
                err("add_story", e);
                // Panel is closed so we can't show status inside it.
                // Emit to whatever global notification system you have,
                // or reopen the panel with an error.
                console.error("[add_story] Download failed:", e.message);
            } finally {
                setState(panelId, { isLoading: false });
            }
        },
    };

    // ─────────────────────────────────────────────────────────────────
    // PANEL TYPE: METADATA
    // ─────────────────────────────────────────────────────────────────

    handlers.metadata = {
        name: "metadata",
        storyId: null,
        authorId: null,

        open(panelId, storyId) {
            this.storyId = storyId;
            setState(panelId, { panelType: "metadata" });
            setStatus(panelId, "", "");
            setOpen(panelId, true);
            this.loadData(panelId);
        },

        close(panelId) {
            setOpen(panelId, false);
        },

        async loadData(panelId) {
            if (!this.storyId) return;

            try {
                const result = await fetchJSON(
                    `/api/stories/${this.storyId}`
                );
                if (result.ok) {
                    const st = result.data.story || {};
                    setVal("metaTitle", panelId, st.title || "");
                    setVal("metaSubtitle", panelId, st.subtitle || "");
                    setVal("metaDescription", panelId, st.description || "");
                    setVal("metaPublishYear", panelId, st.publish_year || "");
                    setVal("metaLanguage", panelId, st.language || "");
                    setVal("metaSourceUrl", panelId, st.source_url || "");
                    
                    const hideAuthorNotesEl = $(`metaHideAuthorNotes-${panelId}`);
                    if (hideAuthorNotesEl)
                        hideAuthorNotesEl.checked = Boolean(st.hide_author_notes);

                    const autoUpdateEl = $(
                        `metaAutoUpdate-${panelId}`
                    );
                    if (autoUpdateEl)
                        autoUpdateEl.checked = Boolean(st.auto_update);
                    
                    this.renderCoverPreview(panelId, st.cover_path);

                    renderTagList(
                        "metaSeriesWrap",
                        panelId,
                        st.series_list || parseCommaList(st.series)
                    );
                    renderTagList(
                        "metaGenresWrap",
                        panelId,
                        st.genres_list || parseCommaList(st.genres)
                    );
                    renderTagList(
                        "metaTagsWrap",
                        panelId,
                        st.tags_list || parseCommaList(st.tags)
                    );
                }
            } catch (_) {}

            // Load author
            try {
                const result = await fetchJSON(
                    `/api/stories/${this.storyId}/authors`
                );
                if (result.ok) {
                    const authors = result.data.authors || [];
                    if (authors.length > 0) {
                        const a = authors[0];
                        this.authorId = a.id;
                        setVal("metaAuthorName", panelId, a.name || "");
                    }
                }
            } catch (_) {}
        },

        async save(panelId) {
            const saveBtn = $(`metaSaveBtn-${panelId}`);
            if (saveBtn) saveBtn.disabled = true;
            setStatus(panelId, "Saving…", "");

            try {
                const title = getVal("metaTitle", panelId);
                const authorName = getVal("metaAuthorName", panelId);
                const sourceUrl = getVal("metaSourceUrl", panelId) || null;

                if (!title) {
                    throw new Error("Title is required");
                }

                const payload = {
                    title,
                    author: authorName || null,
                    subtitle: getVal("metaSubtitle", panelId) || null,
                    description: getVal("metaDescription", panelId) || null,
                    publish_year: getVal("metaPublishYear", panelId)
                        ? parseInt(getVal("metaPublishYear", panelId), 10)
                        : null,
                    language: getVal("metaLanguage", panelId) || null,
                    series: collectTagList("metaSeriesWrap", panelId),
                    genres: collectTagList("metaGenresWrap", panelId),
                    tags: collectTagList("metaTagsWrap", panelId),
                    source_url: sourceUrl,
                    auto_update: $(`metaAutoUpdate-${panelId}`)?.checked || false,
                    hide_author_notes: $(`metaHideAuthorNotes-${panelId}`)?.checked || false,
                };

                const result = await fetchJSON(
                    `/api/stories/${this.storyId}/metadata`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    }
                );

                if (!result.ok) {
                    throw new Error(
                        result.data.detail || "Failed to save"
                    );
                }

                setStatus(panelId, "Saved!", "success");
                setTimeout(() => this.close(panelId), 1200);
            } catch (e) {
                err("metadata", e);
                setStatus(panelId, e.message, "error");
            } finally {
                if (saveBtn) saveBtn.disabled = false;
            }
        },
        
        renderCoverPreview(panelId, coverPath) {
            const preview = $(`coverPreview-${panelId}`);
            const removeBtn = $(`coverRemoveBtn-${panelId}`);
            if (!preview) return;

            if (coverPath) {
                preview.innerHTML = `<img src="/covers?path=${encodeURIComponent(coverPath)}" alt="Cover" />`;
                if (removeBtn) removeBtn.style.display = "";
            } else {
                preview.innerHTML = `<i class="fa-solid fa-image"></i><p>No cover image</p>`;
                if (removeBtn) removeBtn.style.display = "none";
            }
        },

        async handleCoverFileSelect(panelId, inputEl) {
            const file = inputEl.files?.[0];
            if (!file || !this.storyId) return;

            // instant local preview while the upload is in flight
            const preview = $(`coverPreview-${panelId}`);
            const localUrl = URL.createObjectURL(file);
            if (preview) preview.innerHTML = `<img src="${localUrl}" alt="Cover" />`;

            const statusEl = $(`coverStatus-${panelId}`);
            if (statusEl) { statusEl.textContent = "Uploading…"; statusEl.className = "unified-panel-status"; }

            try {
                const formData = new FormData();
                formData.append("file", file);

                const res = await fetch(`/api/stories/${this.storyId}/cover`, { method: "POST", body: formData });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Upload failed");

                if (preview) preview.innerHTML = `<img src="${data.cover_url}" alt="Cover" />`;
                const removeBtn = $(`coverRemoveBtn-${panelId}`);
                if (removeBtn) removeBtn.style.display = "";
                if (statusEl) { statusEl.textContent = "Cover updated"; statusEl.className = "unified-panel-status success"; }
            } catch (e) {
                if (statusEl) { statusEl.textContent = e.message; statusEl.className = "unified-panel-status error"; }
            } finally {
                inputEl.value = "";
            }
        },

        toggleCoverUrlInput(panelId) {
            const row = $(`coverUrlRow-${panelId}`);
            if (row) row.style.display = row.style.display === "none" ? "" : "none";
        },

        async fetchCoverFromUrl(panelId) {
            const url = getVal("coverUrlInput", panelId);
            if (!url || !this.storyId) return;

            const statusEl = $(`coverStatus-${panelId}`);
            if (statusEl) { statusEl.textContent = "Fetching…"; statusEl.className = "unified-panel-status"; }

            try {
                const result = await fetchJSON(`/api/stories/${this.storyId}/cover/from-url`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url }),
                });
                if (!result.ok) throw new Error(result.data.detail || "Fetch failed");

                const preview = $(`coverPreview-${panelId}`);
                if (preview) preview.innerHTML = `<img src="${result.data.cover_url}" alt="Cover" />`;
                const removeBtn = $(`coverRemoveBtn-${panelId}`);
                if (removeBtn) removeBtn.style.display = "";
                setVal("coverUrlInput", panelId, "");
                $(`coverUrlRow-${panelId}`).style.display = "none";

                if (statusEl) { statusEl.textContent = "Cover updated"; statusEl.className = "unified-panel-status success"; }
            } catch (e) {
                if (statusEl) { statusEl.textContent = e.message; statusEl.className = "unified-panel-status error"; }
            }
        },

        async removeCover(panelId) {
            if (!this.storyId) return;
            try {
                const result = await fetchJSON(`/api/stories/${this.storyId}/cover`, { method: "DELETE" });
                if (!result.ok) throw new Error(result.data.detail || "Failed to remove cover");
                this.renderCoverPreview(panelId, null);
            } catch (e) {
                err("metadata", e);
            }
        },
    };

    // ─────────────────────────────────────────────────────────────────
    // PANEL TYPE: AUTHOR
    // ─────────────────────────────────────────────────────────────────

    handlers.author = {
        name: "author",
        storyId: null,
        authorId: null,

        open(panelId, storyId, authorId) {
            this.storyId = storyId;
            this.authorId = authorId;
            setState(panelId, { panelType: "author" });
            setStatus(panelId, "", "");
            setOpen(panelId, true);
            this.loadData(panelId);
        },

        close(panelId) {
            setOpen(panelId, false);
        },

        async loadData(panelId) {
            if (!this.storyId || !this.authorId) return;

            try {
                const result = await fetchJSON(
                    `/api/stories/${this.storyId}/authors`
                );
                if (result.ok) {
                    const authors = result.data.authors || [];
                    const author = authors.find(
                        (a) => a.id === this.authorId
                    );
                    if (author) {
                        setVal("authorName", panelId, author.name || "");
                        setVal("authorBio", panelId, author.bio || "");
                    }
                }
            } catch (_) {}
        },

        async save(panelId) {
            const saveBtn = $(`authorSaveBtn-${panelId}`);
            if (saveBtn) saveBtn.disabled = true;
            setStatus(panelId, "Saving…", "");

            try {
                const name = getVal("authorName", panelId);
                if (!name) {
                    throw new Error("Author name is required");
                }

                const payload = {
                    name,
                    bio: getVal("authorBio", panelId) || null,
                };

                const result = await fetchJSON(
                    `/api/stories/${this.storyId}/authors/${this.authorId}`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    }
                );

                if (!result.ok) {
                    throw new Error(
                        result.data.detail || "Failed to save"
                    );
                }

                setStatus(panelId, "Saved!", "success");
                setTimeout(() => this.close(panelId), 1200);
            } catch (e) {
                err("author", e);
                setStatus(panelId, e.message, "error");
            } finally {
                if (saveBtn) saveBtn.disabled = false;
            }
        },
    };
    

    // ─────────────────────────────────────────────────────────────────
    // PUBLIC API
    // ─────────────────────────────────────────────────────────────────

    return {
        // Open panel by type
        open(panelType, panelId, ...args) {
            const handler = handlers[panelType];
            if (!handler) {
                console.warn(`Unknown panel type: ${panelType}`);
                return;
            }
            handler.open(panelId, ...args);
        },

        // Close panel
        close(panelId) {
            const state = getState(panelId);
            const handler = handlers[state.panelType];
            if (handler) handler.close(panelId);
        },

        // Switch tab
        switchTab(panelId, tabId, btn) {
            switchTab(panelId, tabId, btn);
            updateActionButton(panelId);
        },

        // Handle action
        handleAction(panelId, actionId) {
            const state = getState(panelId);
            const handler = handlers[state.panelType];
            if (!handler) return;

            const action = handler[actionId];
            if (typeof action === "function") {
                action.call(handler, panelId);
            }
        },

        // Add story specific
        updateChapterSelection(panelId) {
            handlers.add_story?.updateChapterSelection(panelId);
        },

        selectAllChapters(panelId) {
            handlers.add_story?.selectAllChapters(panelId);
        },

        deselectAllChapters(panelId) {
            handlers.add_story?.deselectAllChapters(panelId);
        },

        // Metadata specific
        // (methods called from template actions)
        previewMetadata(panelId) {
            handlers.add_story?.previewMetadata(panelId);
        },

        confirm(panelId) {
            handlers.add_story?.confirm(panelId);
        },

        // Update button text/action based on active tab
        updateActionButton(panelId) {
            updateActionButton(panelId);
        },
    };
})();
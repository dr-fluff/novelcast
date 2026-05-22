// novelcast/static/js/metadata_panel.js
// NOTE: all API calls use /api/stories/… because the stories router
// is mounted under the /api prefix in create_app().

(function () {
    "use strict";

    let storyId       = null;
    let currentAuthorId = null;

    function el(id) { return document.getElementById(id); }

    // ── Open / Close ───────────────────────────────────────────────────────

    window.openMetaPanel = async function () {
        const page = document.querySelector(".story-page");
        storyId = page ? page.dataset.storyId : null;
        if (!storyId) return;

        el("metaPanel").classList.add("open");
        el("metaPanel").setAttribute("aria-hidden", "false");
        el("metaPanelBackdrop").classList.add("open");
        document.body.style.overflow = "hidden";

        setStatus("", "");
        await loadData();
    };

    window.closeMetaPanel = function () {
        el("metaPanel").classList.remove("open");
        el("metaPanel").setAttribute("aria-hidden", "true");
        el("metaPanelBackdrop").classList.remove("open");
        document.body.style.overflow = "";
    };

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && el("metaPanel").classList.contains("open")) {
            closeMetaPanel();
        }
    });

    // ── Load ───────────────────────────────────────────────────────────────

    async function loadData() {
        // Story fields from rendered DOM
        const titleEl  = document.querySelector(".story-title");
        const urlEl    = document.querySelector(".story-description a");

        el("metaTitle").value     = titleEl ? titleEl.textContent.trim() : "";
        el("metaSourceUrl").value = urlEl   ? urlEl.href                 : "";

        // Reset author fields
        currentAuthorId = null;
        el("metaAuthorName").value = "";
        el("metaAuthorBio").value  = "";
        el("metaLinksContainer").innerHTML = "";

        try {
            const res = await fetch(`/api/stories/${storyId}/authors`);
            if (!res.ok) return;
            const data = await res.json();
            const authors = data.authors || [];

            if (authors.length > 0) {
                const a = authors[0];
                currentAuthorId           = a.id;
                el("metaAuthorName").value = a.name || "";
                el("metaAuthorBio").value  = a.bio  || "";

                // Populate link rows
                (a.links || []).forEach(lnk => addLinkRow(lnk.label, lnk.url));
            } else {
                // Fall back to denormalized text on page
                const authorEl = document.querySelector(".story-author");
                if (authorEl) {
                    const txt = authorEl.textContent.trim();
                    el("metaAuthorName").value = txt === "Unknown author" ? "" : txt;
                }
            }
        } catch (_) { /* non-fatal */ }
    }

    // ── Link rows ──────────────────────────────────────────────────────────

    window.addLinkRow = function (label = "", url = "") {
        const container = el("metaLinksContainer");

        const row = document.createElement("div");
        row.className = "meta-link-row";

        const labelInput = document.createElement("input");
        labelInput.type        = "text";
        labelInput.placeholder = "Label (e.g. Patreon)";
        labelInput.value       = label;

        const urlInput = document.createElement("input");
        urlInput.type        = "url";
        urlInput.placeholder = "https://…";
        urlInput.value       = url;

        const removeBtn = document.createElement("button");
        removeBtn.type      = "button";
        removeBtn.className = "meta-remove-link-btn";
        removeBtn.setAttribute("aria-label", "Remove link");
        removeBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        removeBtn.onclick   = () => row.remove();

        row.appendChild(labelInput);
        row.appendChild(urlInput);
        row.appendChild(removeBtn);
        container.appendChild(row);
    };

    function collectLinks() {
        const rows = el("metaLinksContainer").querySelectorAll(".meta-link-row");
        const links = [];
        rows.forEach(row => {
            const inputs = row.querySelectorAll("input");
            const label  = (inputs[0]?.value || "").trim();
            const url    = (inputs[1]?.value || "").trim();
            if (label && url) links.push({ label, url });
        });
        return links;
    }

    // ── Save ───────────────────────────────────────────────────────────────

    window.saveMetadata = async function () {
        const saveBtn = el("metaSaveBtn");
        saveBtn.disabled = true;
        setStatus("Saving…", "");

        const title      = el("metaTitle").value.trim();
        const authorName = el("metaAuthorName").value.trim();
        const sourceUrl  = el("metaSourceUrl").value.trim() || null;

        if (!title) {
            setStatus("Title is required.", "error");
            saveBtn.disabled = false;
            return;
        }

        try {
            // 1. Save story + author text cache
            const storyRes = await fetch(`/api/stories/${storyId}/metadata`, {
                method:  "PATCH",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ title, author: authorName || null, source_url: sourceUrl }),
            });
            if (!storyRes.ok) {
                const err = await storyRes.json().catch(() => ({}));
                throw new Error(err.detail || "Failed to save story");
            }
            const storyData = await storyRes.json();

            // After saving story, re-fetch authors to get currentAuthorId if it was missing
            if (!currentAuthorId && authorName) {
                try {
                    const ar = await fetch(`/api/stories/${storyId}/authors`);
                    if (ar.ok) {
                        const ad = await ar.json();
                        if (ad.authors?.length) currentAuthorId = ad.authors[0].id;
                    }
                } catch (_) {}
            }

            // 2. Save author name + bio
            if (currentAuthorId && authorName) {
                const authorRes = await fetch(
                    `/api/stories/${storyId}/authors/${currentAuthorId}`,
                    {
                        method:  "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body:    JSON.stringify({ name: authorName, bio: el("metaAuthorBio").value.trim() || null }),
                    }
                );
                if (!authorRes.ok) {
                    const err = await authorRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to save author");
                }

                // 3. Save links
                const links    = collectLinks();
                const linksRes = await fetch(
                    `/api/stories/${storyId}/authors/${currentAuthorId}/links`,
                    {
                        method:  "PUT",
                        headers: { "Content-Type": "application/json" },
                        body:    JSON.stringify({ links }),
                    }
                );
                if (!linksRes.ok) {
                    const err = await linksRes.json().catch(() => ({}));
                    throw new Error(err.detail || "Failed to save links");
                }
            }

            // 4. Update visible DOM
            _updatePageDOM(storyData.story, authorName, sourceUrl);
            setStatus("Saved!", "success");
            setTimeout(() => { setStatus("", ""); closeMetaPanel(); }, 1200);

        } catch (err) {
            setStatus(err.message || "Something went wrong.", "error");
        } finally {
            saveBtn.disabled = false;
        }
    };

    // ── DOM patch ──────────────────────────────────────────────────────────

    function _updatePageDOM(story, authorName, sourceUrl) {
        if (!story) return;

        const titleEl  = document.querySelector(".story-title");
        const authorEl = document.querySelector(".story-author");
        const descEl   = document.querySelector(".story-description");

        if (titleEl)  titleEl.textContent  = story.title || "";
        if (authorEl) authorEl.textContent = authorName  || "Unknown author";

        document.title = `${story.title} · NovelCast`;

        if (descEl) {
            if (sourceUrl) {
                descEl.innerHTML = `Source: <a href="${esc(sourceUrl)}" target="_blank" rel="noreferrer">${esc(sourceUrl)}</a>`;
            } else {
                descEl.textContent = "No source URL available.";
            }
        }
    }

    // ── Helpers ────────────────────────────────────────────────────────────

    function setStatus(msg, cls) {
        const s = el("metaSaveStatus");
        s.textContent = msg;
        s.className   = "meta-save-status" + (cls ? " " + cls : "");
    }

    function esc(str) {
        return str
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

})();

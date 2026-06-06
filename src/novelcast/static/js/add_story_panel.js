(function () {
    "use strict";

    let isLoading = false;

    const $ = (id) => document.getElementById(id);

    const log = (...a) => console.log("[AddStory]", ...a);
    const err = (...a) => console.error("[AddStory]", ...a);

    // -----------------------------
    // PANEL CONTROL
    // -----------------------------
    function setOpen(open, step = 1) {
        const panel = $("addStoryPanel");
        const backdrop = $("addStoryBackdrop");

        if (!panel || !backdrop) {
            err("Panel or backdrop missing");
            return;
        }

        panel.classList.toggle("open", open);
        backdrop.classList.toggle("open", open);

        panel.setAttribute("aria-hidden", open ? "false" : "true");
        document.body.style.overflow = open ? "hidden" : "";

        showStep(step);
    }

    window.openAddStoryPanel = function () {
        setOpen(true, 1);
    };

    window.closeAddStoryPanel = function () {
        setOpen(false);
    };

    // -----------------------------
    // STEP CONTROL (FIXED)
    // IMPORTANT: uses BOTH class styles safely
    // -----------------------------
    function showStep(step) {
        const steps = [
            $("addStoryStep1"),
            $("addStoryStep2"),
            $("addStoryStep3"),
        ];

        steps.forEach((el, i) => {
            if (!el) return;

            const active = i === step - 1;

            // support both patterns
            el.classList.toggle("hidden", !active);
            el.classList.toggle("is-active", active);
        });
    }

    window.showStep = showStep;

    // -----------------------------
    // SAFE JSON FETCH
    // -----------------------------
    async function fetchJSON(url, options) {
        const res = await fetch(url, options);
        const text = await res.text();

        if (!text) {
            throw new Error("Empty backend response");
        }

        try {
            return JSON.parse(text);
        } catch (e) {
            err("Non-JSON response:", text);
            throw new Error("Backend did not return JSON");
        }
    }

    // -----------------------------
    // PREVIEW
    // -----------------------------
    window.openAddStoryPanelWithLoading = async function (url) {
        if (isLoading) return;
        isLoading = true;

        setOpen(true, 3);

        try {
            log("Preview:", url);

            const data = await fetchJSON("/api/stories/preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });

            log("DATA:", data);

            $("addStoryUrl").value = data.url || url || "";
            $("addStoryTitle").value = data.title || "";
            $("addStoryAuthor").value = data.author || "";
            $("addStorySubtitle").value = data.subtitle || "";
            $("addStoryDescription").value = data.description || "";
            $("addStoryPublishYear").value = data.publish_year || "";
            $("addStoryLanguage").value = data.language || "";

            $("chapterCountValue").textContent = data.chapter_count ?? "—";

            showStep(2);
        } catch (e) {
            err(e);
            showStep(2);
        }

        isLoading = false;
    };

    // -----------------------------
    // TAG EXTRACTION (FIXED)
    // -----------------------------
    function getTagValues(wrapperId) {
        const wrap = $(wrapperId);
        if (!wrap) return [];

        return Array.from(wrap.querySelectorAll(".add-story-tag"))
            .map(el => el.textContent.trim())
            .filter(Boolean);
    }

    window.getTagValues = getTagValues;

    // -----------------------------
    // CONFIRM ADD STORY (FIXED ENDPOINT + SAFE FETCH)
    // -----------------------------
    window.confirmAddStory = async function () {
        try {
            const payload = {
                url: $("addStoryUrl")?.value || "",
                title: $("addStoryTitle")?.value || "",
                author: $("addStoryAuthor")?.value || "",
                subtitle: $("addStorySubtitle")?.value || "",
                description: $("addStoryDescription")?.value || "",
                publish_year: $("addStoryPublishYear")?.value
                    ? Number($("addStoryPublishYear").value)
                    : null,
                language: $("addStoryLanguage")?.value || "",
                series: getTagValues("addStorySeriesWrap"),
                genres: getTagValues("addStoryGenresWrap"),
                tags: getTagValues("addStoryTagsWrap"),
                auto_update: $("addStoryAutoUpdate")?.checked || false,
            };

            log("ADD payload:", payload);

            showStep(3);

            // IMPORTANT FIX: your backend is mounted under /stories (NOT /api/stories)
            const res = await fetch("/api/stories/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const text = await res.text();

            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                err("Non-JSON response:", text);
                throw new Error("Backend did not return JSON");
            }

            if (!res.ok) {
                throw new Error(data.detail || "Failed to add story");
            }

            $("addStoryProgressText").textContent = "Story added successfully";
            $("addStoryProgressFill").style.width = "100%";

            setTimeout(() => setOpen(false), 800);

        } catch (e) {
            err(e);

            showStep(2);

            const status = $("addStoryStatus");
            if (status) {
                status.textContent = e.message;
                status.classList.add("error");
            }
        }
    };

})();
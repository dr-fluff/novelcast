(function () {
    'use strict';

    let isLoading = false;
    let selectedChapters = []; // ← NEW

    const $ = (id) => document.getElementById(id);

    const log = (...a) => console.log('[AddStory]', ...a);
    const err = (...a) => console.error('[AddStory]', ...a);

    // -----------------------------
    // PANEL CONTROL
    // -----------------------------
    function setOpen(open) {
        const panel = $('addStoryPanel');
        const backdrop = $('addStoryBackdrop');

        if (!panel || !backdrop) {
            err('Panel or backdrop missing');
            return;
        }

        panel.classList.toggle('open', open);
        backdrop.classList.toggle('open', open);

        panel.setAttribute('aria-hidden', open ? 'false' : 'true');
        document.body.style.overflow = open ? 'hidden' : '';

        if (!open) {
            selectedChapters = []; // ← RESET on close
        }
    }

    window.openAddStoryPanel = function () {
        setOpen(true);
    };

    window.closeAddStoryPanel = function () {
        setOpen(false);
    };

    window.openAddStoryPanelWithLoading = async function (url, title = '', author = '') {
        try {
            setOpen(true);

            const urlInput = document.getElementById('addStoryUrl');

            if (!urlInput) {
                throw new Error('addStoryUrl input not found');
            }

            urlInput.value = url;

            await previewStoryMetadata();
        } catch (e) {
            console.error('[AddStory]', e);
        }
    };

    // ← NEW: Tab switching
    window.switchAddStoryTab = function (btn, tabId) {
        document.querySelectorAll('.add-story-tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.add-story-step').forEach((p) => p.classList.add('hidden'));
        btn.classList.add('active');
        document.getElementById(tabId).classList.remove('hidden');
    };

    // ← NEW: Handle action button based on current tab
    window.handleAddStoryAction = function () {
        const activeTab = document.querySelector('.add-story-tab.active');
        const tabText = activeTab?.textContent.trim().toLowerCase() || '';

        if (tabText.includes('url')) {
            previewStoryMetadata();
        } else if (tabText.includes('metadata')) {
            showChaptersTab();
        } else if (tabText.includes('chapter')) {
            confirmAddStory();
        }
    };

    // ← NEW: Show chapters tab after metadata preview
    function showChaptersTab() {
        const tabs = document.querySelectorAll('.add-story-tab');
        const steps = document.querySelectorAll('.add-story-step');

        tabs.forEach((t) => t.classList.remove('active'));
        steps.forEach((s) => s.classList.add('hidden'));

        if (tabs[2]) tabs[2].classList.add('active');
        if (steps[2]) steps[2].classList.remove('hidden');

        const btn = document.getElementById('addStoryActionBtn');
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-download"></i> Download Story';
        }
    }

    // ← NEW: Display chapters in the list
    window.displayChapters = function (chapters) {
        const list = document.getElementById('chaptersList');
        if (!list) return;

        list.innerHTML = chapters
            .map(
                (ch, idx) => `
            <div class="chapter-item">
                <input 
                    type="checkbox" 
                    id="ch-${idx}"
                    data-chapter-number="${ch.number}"
                    checked
                    onchange="updateChapterSelection()"
                />
                <label for="ch-${idx}">
                    <span class="chapter-number">Chapter ${ch.number}</span>
                    <span class="chapter-title">${ch.title || '(no title)'}</span>
                </label>
            </div>
        `
            )
            .join('');

        document.getElementById('chapterTotalCount').textContent = chapters.length;
        updateChapterSelection();
    };

    // ← NEW: Update selected chapters count
    window.updateChapterSelection = function () {
        const checkboxes = document.querySelectorAll('#chaptersList input[type="checkbox"]');
        selectedChapters = Array.from(checkboxes)
            .filter((cb) => cb.checked)
            .map((cb) => parseInt(cb.dataset.chapterNumber));

        const countEl = document.getElementById('chapterSelectCount');
        if (countEl) {
            countEl.textContent = selectedChapters.length;
        }
    };

    // ← NEW: Select/deselect all chapters
    window.selectAllChapters = function () {
        document.querySelectorAll('#chaptersList input[type="checkbox"]').forEach((cb) => (cb.checked = true));
        updateChapterSelection();
    };

    window.deselectAllChapters = function () {
        document.querySelectorAll('#chaptersList input[type="checkbox"]').forEach((cb) => (cb.checked = false));
        updateChapterSelection();
    };

    // -----------------------------
    // SAFE JSON FETCH
    // -----------------------------
    async function fetchJSON(url, options) {
        const res = await fetch(url, options);
        const text = await res.text();

        if (!text) {
            throw new Error('Empty backend response');
        }

        try {
            return JSON.parse(text);
        } catch (e) {
            err('Non-JSON response:', text);
            throw new Error('Backend did not return JSON');
        }
    }

    // ← UPDATED: Preview with chapters
    window.previewStoryMetadata = async function () {
        if (isLoading) return;
        isLoading = true;

        const url = $('addStoryUrl')?.value;
        if (!url) {
            err('URL is required');
            isLoading = false;
            return;
        }

        try {
            log('Preview:', url);

            const data = await fetchJSON('/api/stories/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });

            log('Preview data:', data);

            // Populate metadata fields
            $('addStoryTitle').value = data.title || '';
            $('addStoryAuthor').value = data.author || '';
            $('addStorySubtitle').value = data.subtitle || '';
            $('addStoryDescription').value = data.description || '';
            $('addStoryPublishYear').value = data.publish_year || '';
            $('addStoryLanguage').value = data.language || '';

            $('chapterCountValue').textContent = data.chapter_count ?? '—';

            // ← NEW: Display chapters
            if (data.chapters && data.chapters.length > 0) {
                displayChapters(data.chapters);
            }

            // Switch to metadata tab
            const tabs = document.querySelectorAll('.add-story-tab');
            const steps = document.querySelectorAll('.add-story-step');

            tabs.forEach((t) => t.classList.remove('active'));
            steps.forEach((s) => s.classList.add('hidden'));

            if (tabs[1]) tabs[1].classList.add('active');
            if (steps[1]) steps[1].classList.remove('hidden');

            // Update button label
            const btn = document.getElementById('addStoryActionBtn');
            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-arrow-right"></i> Next: Chapters';
            }
        } catch (e) {
            err(e);
            const status = $('addStoryStatus');
            if (status) {
                status.textContent = e.message;
                status.classList.add('error');
            }
        }

        isLoading = false;
    };

    // -----------------------------
    // TAG EXTRACTION
    // -----------------------------
    function getTagValues(wrapperId) {
        const wrap = $(wrapperId);
        if (!wrap) return [];

        return Array.from(wrap.querySelectorAll('.add-story-tag'))
            .map((el) => el.textContent.trim())
            .filter(Boolean);
    }

    window.getTagValues = getTagValues;

    // ← UPDATED: Include selected chapters
    window.confirmAddStory = async function () {
        log('Confirming add story with selected chapters:', selectedChapters);
        try {
            const payload = {
                url: $('addStoryUrl')?.value || '',
                title: $('addStoryTitle')?.value || '',
                author: $('addStoryAuthor')?.value || '',
                subtitle: $('addStorySubtitle')?.value || '',
                description: $('addStoryDescription')?.value || '',
                publish_year: $('addStoryPublishYear')?.value ? Number($('addStoryPublishYear').value) : null,
                language: $('addStoryLanguage')?.value || '',
                series: getTagValues('addStorySeriesWrap'),
                genres: getTagValues('addStoryGenresWrap'),
                tags: getTagValues('addStoryTagsWrap'),
                auto_update: $('addStoryAutoUpdate')?.checked || false,
                hide__author_notes: $('metaHideAuthorNotes')?.checked || true,
                selected_chapters: selectedChapters.length > 0 ? selectedChapters : null, // ← NEW
            };

            log('ADD payload:', payload);

            // Switch to download tab
            const tabs = document.querySelectorAll('.add-story-tab');
            const steps = document.querySelectorAll('.add-story-step');

            tabs.forEach((t) => t.classList.remove('active'));
            steps.forEach((s) => s.classList.add('hidden'));

            if (tabs[3]) tabs[3].classList.add('active');
            if (steps[3]) steps[3].classList.remove('hidden');

            const res = await fetch('/api/stories/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const text = await res.text();

            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                err('Non-JSON response:', text);
                throw new Error('Backend did not return JSON');
            }

            if (!res.ok) {
                throw new Error(data.detail || 'Failed to add story');
            }

            const chapterInfo =
                selectedChapters.length > 0 ? ` (${selectedChapters.length} chapters)` : ' (all chapters)';

            $('addStoryProgressText').textContent = 'Story added successfully' + chapterInfo;
            $('addStoryProgressFill').style.width = '100%';

            setTimeout(() => setOpen(false), 1200);
        } catch (e) {
            err(e);

            // Back to chapters tab
            const tabs = document.querySelectorAll('.add-story-tab');
            const steps = document.querySelectorAll('.add-story-step');

            tabs.forEach((t) => t.classList.remove('active'));
            steps.forEach((s) => s.classList.add('hidden'));

            if (tabs[2]) tabs[2].classList.add('active');
            if (steps[2]) steps[2].classList.remove('hidden');

            const status = $('addStoryStatus');
            if (status) {
                status.textContent = e.message;
                status.classList.add('error');
            }
        }
    };
})();

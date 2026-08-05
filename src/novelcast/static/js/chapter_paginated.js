/**
 * novelcast/static/js/chapter_paginated.js
 *
 * Column-based paginator. Renders content into a multi-column iframe
 * where each column is exactly one page wide. Navigating pages = translating
 * the column container horizontally. No scroll offset math needed.
 */

class PaginatedEReader {
    constructor() {
        this.state = {
            storyId: null,
            chapterId: null,
            nextChapterId: null,
            prevChapterId: null,
            chapterTitle: '',
            currentPage: 0,
            totalPages: 0,
            originalContent: null,
            contentPadding: 3,
        };

        this.iframe = null;
        this.iframeDoc = null;
        this.iframeWin = null;
        this.resizeTimer = null;
        this.repaginateTimer = null;
        this.touch = { startX: 0, endX: 0, threshold: 50 };

        // Safety-net defaults, used only until the schema (server-provided)
        // and/or the saved settings load. Once loadSchema() runs, defaults
        // come from the schema instead.
        this.settings = {
            theme: 'light',
            fontFamily: 'serif',
            fontSize: 100,
            lineSpacing: 100,
            fontWeight: 1,
            paragraphSpacing: 100,
            contentPadding: 3,
        };

        // Reading settings schema (label/control/options/range per field),
        // provided by the server via data-reading-schema on #settingsPanel.
        this.schema = {};

        this.deviceId = this.getDeviceId();
        this.userLoaded = false;

        document.readyState === 'loading'
            ? document.addEventListener('DOMContentLoaded', () => this.init())
            : this.init();
    }

    // ======================
    // INITIALIZATION
    // ======================

    async init() {
        this.registerServiceWorker();
        this.cacheContainerData();
        this.cacheElements();
        this.loadSchema();
        this.buildSettingsPanel();
        await this.loadUserSettings();
        this.updateSettingsUI();
        this.attachEvents();
        this.attachSettingsEvents();
        this.buildIframe();
    }

    registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return;
        navigator.serviceWorker.register('/sw.js').catch(() => {
            // If registration fails (unsupported context, etc.) the reader
            // still works — it just falls back to normal network requests
            // with no background precaching.
        });
    }

    getDeviceId() {
        // Try localStorage first (works in normal browsing, may be blocked
        // under strict tracking protection or private browsing).
        try {
            let id = localStorage.getItem('nc_device_id');
            if (id) return id;
        } catch (e) {
            /* localStorage blocked, fall through to cookie */
        }

        // Fallback: cookie-based device id, which tends to survive strict
        // tracking protection since it's first-party storage on this origin.
        const match = document.cookie.match(/(?:^|; )nc_device_id=([^;]+)/);
        if (match) {
            const id = decodeURIComponent(match[1]);
            try {
                localStorage.setItem('nc_device_id', id);
            } catch (e) {}
            return id;
        }

        // Neither exists — mint a new id and persist wherever we can.
        const id = this.generateUUID();
        try {
            localStorage.setItem('nc_device_id', id);
        } catch (e) {}
        try {
            document.cookie = `nc_device_id=${encodeURIComponent(id)}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
        } catch (e) {}
        return id;
    }

    generateUUID() {
        // crypto.randomUUID() only exists in secure contexts (HTTPS or
        // localhost) — LAN IPs over plain HTTP are not secure contexts,
        // so fall back to a manual RFC4122-ish generator there.
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
            try {
                return crypto.randomUUID();
            } catch (e) {
                /* fall through */
            }
        }
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = (Math.random() * 16) | 0;
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    loadSchema() {
        const panel = document.getElementById('settingsPanel');
        if (!panel) {
            this.schema = {};
            return;
        }
        try {
            this.schema = JSON.parse(panel.dataset.readingSchema || '{}');
        } catch (e) {
            this.schema = {};
        }

        // Seed settings defaults from the schema (server-provided), so the
        // safety-net defaults above only matter if this parse ever fails.
        Object.entries(this.schema).forEach(([key, spec]) => {
            if (spec.default !== undefined) this.settings[key] = spec.default;
        });
    }

    async loadUserSettings() {
        try {
            const r = await fetch('/api/chapter-settings', {
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.deviceId ? { 'X-Device-Id': this.deviceId } : {}),
                },
            });
            if (r.ok) {
                const data = await r.json();
                this.settings = { ...this.settings, ...data.settings };
                this.userLoaded = true;
            }
        } catch (e) {
            /* offline or unreachable — keep schema/safety-net defaults */
        }
    }

    async saveUserSettings() {
        if (!this.userLoaded) return;

        const url = '/api/chapter-settings';
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.deviceId ? { 'X-Device-Id': this.deviceId } : {}),
            },
            body: JSON.stringify({ settings: this.settings }),
        };

        try {
            // queuedFetch (from offline-sync.js) queues this in IndexedDB
            // and retries once back online if it fails — falls back to a
            // plain fetch if offline support hasn't loaded for some reason.
            if (window.NovelcastOffline?.queuedFetch) {
                await window.NovelcastOffline.queuedFetch(url, options);
            } else {
                await fetch(url, options);
            }
        } catch (e) {
            /* ignore */
        }
    }

    cacheContainerData() {
        const c = document.querySelector('.reader-container');
        if (!c) return;
        this.state.storyId = c.dataset.storyId;
        this.state.chapterId = c.dataset.chapterId;
        this.state.nextChapterId = c.dataset.nextChapterId;
        this.state.prevChapterId = c.dataset.prevChapterId;
        this.state.chapterTitle = c.dataset.chapterTitle || '';
        this.state.hideAuthorNotes = c.dataset.hideAuthorNotes === 'true';

        try {
            this.state.upcomingChapterIds = JSON.parse(c.dataset.upcomingChapterIds || '[]');
        } catch (e) {
            this.state.upcomingChapterIds = [];
        }
    }

    cacheElements() {
        const $ = (id) => document.getElementById(id);
        this.el = {
            scrollContainer: document.querySelector('.chapter-scroll-container'),
            chapterSource: $('chapterSource'),
            header: document.querySelector('.reader-header'),
            settingsBtn: $('settingsBtn'),
            closeSettingsBtn: $('closeSettings'),
            settingsPanel: $('settingsPanel'),
            settingsOverlay: $('settingsOverlay'),
            settingsFields: $('settingsFields'),
            nextBtn: $('nextChapterFloating'),
            prevBtn: $('prevChapter'),
            backBtn: document.querySelector('.back-btn'),
            pageCounter: this.createPageCounter(),
            // populated by buildSettingsPanel() once the panel is rendered
            settingBtns: null,
            settingSliders: null,
        };
    }

    createPageCounter() {
        let el = document.getElementById('pageCounter');
        if (el) return el;
        el = document.createElement('div');
        el.id = 'pageCounter';
        Object.assign(el.style, {
            position: 'fixed',
            bottom: '1.5rem',
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '0.5rem 1rem',
            background: 'rgba(0,0,0,0.6)',
            color: '#fff',
            borderRadius: '20px',
            fontSize: '0.85rem',
            zIndex: '9999',
            pointerEvents: 'none',
        });
        document.body.appendChild(el);
        return el;
    }

    // ======================
    // IFRAME + COLUMNS
    // ======================

    getPageSize() {
        return {
            w: this.el.scrollContainer.clientWidth,
            h: this.el.scrollContainer.clientHeight,
        };
    }

    // Runs once the iframe document has actually loaded. Pulled out into
    // its own method (rather than an inline arrow function passed straight
    // to addEventListener) so it can be attached to the 'load' event
    // BEFORE we write to the document — see buildIframe() below for why
    // that ordering matters.
    onIframeLoad() {
        const touchTarget = this.iframeDoc.body;

        touchTarget.addEventListener('touchstart', (e) => {
            this.touch.startX = e.changedTouches[0].screenX;
            this.touch.startY = e.changedTouches[0].screenY;
        });

        touchTarget.addEventListener('touchend', (e) => {
            const dx = e.changedTouches[0].screenX - this.touch.startX;
            const dy = e.changedTouches[0].screenY - this.touch.startY;

            // Ignore mostly vertical gestures
            if (Math.abs(dy) > Math.abs(dx)) return;

            if (dx < -this.touch.threshold) {
                this.nextPage();
            } else if (dx > this.touch.threshold) {
                this.prevPage();
            }
        });

        requestAnimationFrame(() =>
            requestAnimationFrame(async () => {
                this.calculatePages();
                this.render(0); // show content immediately
                this.iframeWin.addEventListener('keydown', (e) => this.handleKey(e));
                const startPage = await this.resolveStartPage();
                if (startPage > 0) this.render(startPage); // jump once progress loads

                // Give the current chapter's own render a brief head start
                // before kicking off background precaching of upcoming ones,
                // so precache network activity doesn't compete with anything
                // the person is actively waiting on right now.
                setTimeout(() => this.precacheUpcomingChapters(), 300);
            })
        );
    }

    buildIframe() {
        if (!this.state.originalContent) {
            this.state.originalContent = this.el.chapterSource?.innerHTML || '';
        }

        if (this.iframe) {
            this.iframe.remove();
            this.iframe = null;
            this.iframeDoc = null;
            this.iframeWin = null;
        }

        const iframe = document.createElement('iframe');
        Object.assign(iframe.style, {
            display: 'block',
            width: '100%',
            height: '100%',
            border: 'none',
            overflow: 'hidden',
        });
        iframe.setAttribute('scrolling', 'no');

        this.el.scrollContainer.appendChild(iframe);
        this.iframe = iframe;
        this.iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        this.iframeWin = iframe.contentWindow;

        const { w, h } = this.getPageSize();
        const cleanContent = this.state.originalContent;

        const titleEscaped = this.state.chapterTitle.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        // IMPORTANT: attach the 'load' listener BEFORE calling doc.open() /
        // write() / close(). Some WebKit builds (confirmed: iPadOS 15.8,
        // real hardware — not reproducible in desktop Firefox's simulated
        // iPad viewport) can fire 'load' synchronously as part of close(),
        // or on an earlier tick than expected. If the listener is attached
        // AFTER close(), it can miss the event entirely — totalPages then
        // stays stuck at its initial value of 0 forever, the page counter
        // pill never gets its text set, and nextPage()/prevPage() always
        // fall through to the change-chapter branch since
        // `currentPage < totalPages - 1` (0 < -1) is false. That matches
        // every symptom seen on that device exactly.
        iframe.addEventListener('load', () => this.onIframeLoad(), { once: true });

        this.iframeDoc.open();
        this.iframeDoc.write(`<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>${this.buildCSS(w, h)}</style>
</head>
<body>
<div id="columns">
  <div id="content">
    <h2 class="chapter-title">${titleEscaped}</h2>
    <hr class="chapter-divider"/>
    ${cleanContent}
  </div>
</div>
</body>
</html>`);
        this.iframeDoc.close();
    }

    async resolveStartPage() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('lastPage') === '1') return this.state.totalPages - 1;

        const pageParam = params.get('page');
        const anchorParam = params.get('anchor');

        if (anchorParam !== null) return this.findPageForAnchor(parseInt(anchorParam, 10));
        if (pageParam !== null) return Math.min(parseInt(pageParam, 10), this.state.totalPages - 1);

        // ← was always falling through to 0; now fetches saved progress
        try {
            const r = await fetch(`/api/chapter-progress?chapter_id=${this.state.chapterId}`);
            if (r.ok) {
                const data = await r.json();
                if (data.anchor != null) return this.findPageForAnchor(data.anchor);
                if (data.page) return Math.min(data.page, this.state.totalPages - 1);
            }
        } catch (e) {
            /* fall through to 0 */
        }

        return 0;
    }

    findPageForAnchor(paragraphIndex) {
        const doc = this.iframeDoc;
        if (!doc) return 0;
        const { w } = this.getPageSize();

        const paragraphs = doc.querySelectorAll('p');
        const target = paragraphs[paragraphIndex] || paragraphs[0];
        if (!target) return 0;

        // offsetLeft in a CSS columns layout = horizontal position in the column strip
        const page = Math.floor(target.offsetLeft / w);
        return Math.max(0, Math.min(page, this.state.totalPages - 1));
    }

    saveProgress(page, totalPages) {
        // Track the latest pending save so it can be flushed immediately
        // (bypassing the debounce) if the browser signals the page is
        // about to be hidden/backgrounded — see flushProgress() below.
        this._pendingProgress = { page, totalPages };

        clearTimeout(this.progressTimer);
        this.progressTimer = setTimeout(() => this.flushProgress(false), 500);
    }

    // Sends whatever progress is currently pending, right now, bypassing
    // the normal 500ms debounce entirely. Mobile browsers commonly
    // suspend JS timers the instant a tab is backgrounded (app switch,
    // screen lock) — if several page turns happened in quick succession
    // right before that, each one's debounce timer kept getting
    // cancelled by the next, and the final pending save could be
    // discarded entirely before it ever got a chance to fire. That's
    // why reopening the app could show the reader having silently
    // regressed by however many pages were turned in that last ~500ms
    // window. Calling this on visibilitychange/pagehide closes that gap.
    flushProgress(useBeacon) {
        if (!this._pendingProgress) return;
        const { page, totalPages } = this._pendingProgress;

        clearTimeout(this.progressTimer);
        this._pendingProgress = null;

        const anchor = this.findAnchorParagraph();
        const payload = JSON.stringify({
            chapter_id: Number(this.state.chapterId),
            story_id: Number(this.state.storyId),
            page,
            total_pages: totalPages,
            anchor,
        });

        if (useBeacon && navigator.sendBeacon) {
            // sendBeacon is specifically designed to survive the page being
            // torn down mid-request — a normal fetch is not guaranteed to
            // complete once the browser starts suspending/discarding the tab.
            // Note: sendBeacon has no failure callback, so this path can't
            // be routed through the offline queue — if the device is
            // actually offline at teardown time, this delivery attempt is
            // simply lost. The debounced path below (normal foreground
            // page turns) is what the offline queue actually protects.
            const blob = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon('/api/chapter-progress', blob);
        } else {
            const url = '/api/chapter-progress';
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true, // best-effort: helps the request survive unload in more browsers
            };

            if (window.NovelcastOffline?.queuedFetch) {
                window.NovelcastOffline.queuedFetch(url, options).catch(() => {});
            } else {
                fetch(url, options).catch(() => {});
            }
        }
    }

    findAnchorParagraph() {
        const doc = this.iframeDoc;
        if (!doc) return 0;
        const { w } = this.getPageSize();
        const scrollLeft = this.state.currentPage * w;

        const paragraphs = doc.querySelectorAll('p');
        for (let i = 0; i < paragraphs.length; i++) {
            const rect = paragraphs[i].getBoundingClientRect();
            // getBoundingClientRect is relative to iframe viewport, not columns
            // use offsetLeft instead
            const left = paragraphs[i].offsetLeft;
            if (left >= scrollLeft - w && left < scrollLeft + w) {
                return i;
            }
        }
        return 0;
    }

    getProgress(chapterId) {
        try {
            const val = localStorage.getItem(`nc_progress_${chapterId}`);
            return val !== null ? parseInt(val, 10) : null;
        } catch (e) {
            return null;
        }
    }

    buildCSS(w, h) {
        const fontSize = ((1.05 * this.settings.fontSize) / 100).toFixed(3);
        const lineHeight = ((1.85 * this.settings.lineSpacing) / 100).toFixed(3);
        const fontWeight = [300, 400, 700][this.settings.fontWeight] ?? 400;
        const paragraphMargin = ((1.5 * this.settings.paragraphSpacing) / 100).toFixed(3);

        const themes = {
            light: { bg: '#faf8f3', text: '#2c2c2c', secondary: '#666', accent: '#3b82f6', hr: 'rgba(0,0,0,0.12)' },
            sepia: { bg: '#f4eee6', text: '#5c4033', secondary: '#8d6e63', accent: '#8d6e63', hr: 'rgba(0,0,0,0.08)' },
            dark: {
                bg: '#1a1a1a',
                text: '#e8e8e8',
                secondary: '#a8a8a8',
                accent: '#60a5fa',
                hr: 'rgba(255,255,255,0.1)',
            },
        };
        const c = themes[this.settings.theme] || themes.light;

        const fontSerif = `Georgia, "Noto Serif", "Times New Roman", serif`;
        const fontSans = `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
        const fontStack = this.settings.fontFamily === 'sans' ? fontSans : fontSerif;

        return `
      * { box-sizing: border-box; margin: 0; padding: 0; }

      html, body {
        width:    ${w}px;
        height:   ${h}px;
        overflow: hidden;
        background: ${c.bg};
      }

      #columns {
        width:               ${w}px;
        height:              ${h}px;
        column-width:        ${w}px;
        -webkit-column-width: ${w}px;
        column-gap:          0px;
        -webkit-column-gap:  0px;
        column-fill:         auto;
        -webkit-column-fill: auto;
        transform:           translateX(0);
        -webkit-transform:   translateX(0);
        will-change:         transform;
      }

      /* Content flows naturally into columns */
      #content {
        font-family: ${fontStack};
        font-size:   ${fontSize}rem;
        line-height: ${lineHeight};
        font-weight: ${fontWeight};
        color:       ${c.text};
        padding: 2rem ${this.settings.contentPadding}rem;
        /* Let content be as tall as columns allow */
        height:      ${h}px;
      }

      .chapter-title {
        font-size:      1.4em;
        font-weight:    600;
        letter-spacing: -0.02em;
        color:          ${c.text};
        margin-bottom:  0.75rem;
        /* Prevent title from being split across columns */
        break-after:    avoid;
        -webkit-column-break-after: avoid;
        column-span:    none;
        -webkit-column-span: none;
      }

      .chapter-divider {
        border:        none;
        border-top:    1px solid ${c.hr};
        margin-bottom: 1.25rem;
        break-after:   avoid;
        -webkit-column-break-after: avoid;
      }

      /* Override inline styles from scraped HTML */
      p, span, a, b, i, em, strong {
        font-size:   ${fontSize}rem !important;
        line-height: ${lineHeight} !important;
        color:       ${c.text} !important;
        font-weight: ${fontWeight} !important;
      }

      strong, b { font-weight: bold !important; }
      em, i     { font-style: italic !important; }

      p, li, blockquote {
        margin: 0 0 ${paragraphMargin}rem 0 !important;
      }
      p:first-of-type { margin-top: 0 !important; }

      /* Avoid paragraphs breaking right before last line */
      p { orphans: 2; widows: 2; }

      a { color: ${c.accent} !important; text-decoration: underline; }

      blockquote {
        padding:     0.8rem 1.2rem !important;
        border-left: 3px solid ${c.accent}55 !important;
        font-style:  italic !important;
        color:       ${c.secondary} !important;
        margin:      1rem 0 !important;
      }

      ul, ol {
        margin:  0.8rem 0 0.8rem 1.8rem !important;
        padding: 0 !important;
      }

      img {
        max-width: 100% !important;
        height:    auto !important;
        display:   block !important;
        margin:    1rem 0 !important;
      }

      ${
          this.state.hideAuthorNotes
              ? `
      .author-note-portlet,
      .author-note-portlet *,
      .portlet.solid.author-note-portlet,
      .portlet-body.author-note { display: none !important; }
    `
              : ''
      }
    `;
    }

    // ======================
    // PAGINATION
    // ======================

    calculatePages() {
        const doc = this.iframeDoc;
        if (!doc) return;

        const { w } = this.getPageSize();
        const columnsEl = doc.getElementById('columns');
        if (!columnsEl) return;

        // scrollWidth of the column container = total width of all columns
        const totalWidth = columnsEl.scrollWidth;
        this.state.totalPages = Math.max(1, Math.round(totalWidth / w));
    }

    // ======================
    // RENDERING
    // ======================

    render(index) {
        const i = Math.max(0, Math.min(index, this.state.totalPages - 1));
        this.state.currentPage = i;

        const { w } = this.getPageSize();
        const columnsEl = this.iframeDoc?.getElementById('columns');
        if (columnsEl) {
            columnsEl.style.transform = `translateX(${-i * w}px)`;
        }

        this.saveProgress(i, this.state.totalPages);
        this.updateUI();
    }

    repaginate(targetPage) {
        clearTimeout(this.repaginateTimer);
        this.repaginateTimer = setTimeout(() => {
            // Same ordering fix as buildIframe(): attach 'load' before
            // rebuilding the iframe's document, not after.
            const onLoad = () => {
                requestAnimationFrame(() =>
                    requestAnimationFrame(() => {
                        this.render(Math.min(targetPage, this.state.totalPages - 1));
                    })
                );
            };
            // buildIframe() itself now attaches onIframeLoad() first, so by
            // the time it returns the 'load' handling for this rebuild is
            // already wired up. We still want our own targetPage callback to
            // run after that too.
            this.buildIframe();
            this.iframe.addEventListener('load', onLoad, { once: true });
        }, 50);
    }

    updateUI() {
        const { currentPage, totalPages } = this.state;
        if (this.el.pageCounter) this.el.pageCounter.textContent = `${currentPage + 1} / ${totalPages}`;
        if (this.el.prevBtn) this.el.prevBtn.style.opacity = currentPage === 0 ? '0.3' : '0.8';
        if (this.el.nextBtn) this.el.nextBtn.style.opacity = currentPage === totalPages - 1 ? '0.3' : '0.8';
    }

    // Hands the service worker a list of upcoming chapter URLs to fetch
    // and cache in the background, with retry/backoff on its side. Runs
    // once per chapter load, as early as reasonably possible — on a slow
    // or spotty connection, the whole point is to get ahead of the
    // problem before it happens, not wait until you're already near the
    // end of the current chapter (by then a dropped connection has less
    // time to recover before you tap "next").
    precacheUpcomingChapters() {
        if (!('serviceWorker' in navigator)) return;
        const { storyId, upcomingChapterIds } = this.state;
        if (!upcomingChapterIds || upcomingChapterIds.length === 0) return;

        const urls = upcomingChapterIds.map((cid) => `/chapter?story_id=${storyId}&chapter_id=${cid}`);

        navigator.serviceWorker.ready
            .then((reg) => {
                if (reg.active) {
                    reg.active.postMessage({ type: 'PRECACHE_CHAPTERS', urls });
                }
            })
            .catch(() => {
                /* best-effort — normal navigation still works without it */
            });
    }

    // ======================
    // NAVIGATION
    // ======================

    nextPage = () => {
        const { currentPage, totalPages, nextChapterId, storyId } = this.state;
        const cleanNext = !nextChapterId || nextChapterId === 'None' ? null : nextChapterId;
        if (currentPage < totalPages - 1) this.render(currentPage + 1);
        // Explicitly request page 0 — otherwise resolveStartPage() falls
        // back to whatever page was last saved for this specific chapter,
        // which could be stale (e.g. from skimming ahead once before) and
        // would silently resume there instead of starting the chapter
        // fresh, which is what advancing forward should always do.
        else if (cleanNext) window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanNext}&page=0`;
        else window.location.href = `/story?story_id=${storyId}`;
    };

    prevPage = () => {
        const { currentPage, prevChapterId, storyId } = this.state;
        const cleanPrev = !prevChapterId || prevChapterId === 'None' ? null : prevChapterId;
        if (currentPage > 0) this.render(currentPage - 1);
        else if (cleanPrev) window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanPrev}&lastPage=1`;
        else window.location.href = `/story?story_id=${storyId}`;
    };

    handleKey(e) {
        if (['ArrowRight', 'ArrowDown', ' '].includes(e.key)) {
            e.preventDefault();
            this.nextPage();
        }
        if (['ArrowLeft', 'ArrowUp'].includes(e.key)) {
            e.preventDefault();
            this.prevPage();
        }
    }

    // ======================
    // SETTINGS — rendered dynamically from this.schema
    // ======================

    buildSettingsPanel() {
        const container = this.el.settingsFields;
        if (!container) return;

        container.innerHTML = '';

        Object.entries(this.schema).forEach(([key, spec]) => {
            const group = document.createElement('div');
            group.className = 'settings-group';

            const label = document.createElement('label');
            label.textContent = `${spec.label}:`;
            group.appendChild(label);

            if (spec.control === 'buttons') {
                const btnGroup = document.createElement('div');
                btnGroup.className = 'button-group';

                (spec.options || []).forEach((opt) => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'setting-btn';
                    btn.dataset.settingKey = key;
                    btn.dataset.settingValue = opt.value;
                    btn.innerHTML = opt.icon ? `<i class="fa-solid ${opt.icon}"></i> ${opt.label}` : opt.label;
                    btnGroup.appendChild(btn);
                });

                group.appendChild(btnGroup);
            } else if (spec.control === 'slider') {
                const sliderContainer = document.createElement('div');
                sliderContainer.className = 'slider-container';
                sliderContainer.innerHTML = `
          <span class="slider-min">−</span>
          <input type="range" class="slider" data-setting-key="${key}"
                 min="${spec.min}" max="${spec.max}" step="${spec.step || 1}">
          <span class="slider-max">+</span>
        `;
                group.appendChild(sliderContainer);

                const valueDisplay = document.createElement('div');
                valueDisplay.className = 'slider-value';
                valueDisplay.dataset.valueFor = key;
                group.appendChild(valueDisplay);
            }

            container.appendChild(group);
        });

        this.el.settingBtns = container.querySelectorAll('.setting-btn');
        this.el.settingSliders = container.querySelectorAll('.slider[data-setting-key]');
    }

    updateSettingsUI() {
        this.el.settingBtns?.forEach((btn) => {
            const key = btn.dataset.settingKey;
            const isActive = String(this.settings[key]) === btn.dataset.settingValue;
            btn.classList.toggle('active', isActive);
        });

        this.el.settingSliders?.forEach((slider) => {
            const key = slider.dataset.settingKey;
            const spec = this.schema[key] || {};
            const value = this.settings[key];

            slider.value = value;

            const display = this.el.settingsFields?.querySelector(`[data-value-for="${key}"]`);
            if (display) display.textContent = `${value}${spec.unit || ''}`;
        });
    }

    attachSettingsEvents() {
        const container = this.el.settingsFields;
        if (!container) return;

        container.addEventListener('click', (e) => {
            const btn = e.target.closest('.setting-btn');
            if (!btn) return;

            const key = btn.dataset.settingKey;
            let value = btn.dataset.settingValue;
            const asNumber = Number(value);
            if (!Number.isNaN(asNumber) && value !== '') value = asNumber;

            this.settings[key] = value;
            this.updateSettingsUI();
            this.repaginate(this.state.currentPage);
            this.saveUserSettings();
        });

        // Live-update the preview on every tick of the drag, but keep this
        // cheap — no repagination, no saving. Fast drags on mobile were
        // getting interrupted because buildIframe() (full doc.write + layout)
        // was firing on every 'input' event, blocking the main thread long
        // enough to drop the touch gesture mid-drag.
        container.addEventListener('input', (e) => {
            const slider = e.target.closest('.slider[data-setting-key]');
            if (!slider) return;

            const key = slider.dataset.settingKey;
            this.settings[key] = Number(slider.value);
            this.updateSettingsUI();
        });

        // Only repaginate and save once the drag actually finishes — 'change'
        // fires once when the user releases the slider/lifts their finger.
        container.addEventListener('change', (e) => {
            const slider = e.target.closest('.slider[data-setting-key]');
            if (!slider) return;

            this.repaginate(this.state.currentPage);
            this.saveUserSettings();
        });
    }

    // ======================
    // EVENTS
    // ======================

    attachEvents() {
        // Keyboard on the outer page
        document.addEventListener('keydown', (e) => this.handleKey(e));

        // Touch swipe
        const sc = this.el.scrollContainer;
        if (sc) {
            sc.addEventListener(
                'touchstart',
                (e) => {
                    this.touch.startX = e.changedTouches[0].screenX;
                },
                { passive: true }
            );
            sc.addEventListener('touchend', (e) => {
                const diff = this.touch.startX - e.changedTouches[0].screenX;
                if (diff > this.touch.threshold) this.nextPage();
                else if (diff < -this.touch.threshold) this.prevPage();
            });
        }

        // Resize / zoom
        window.addEventListener('resize', () => {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                this.repaginate(this.state.currentPage);
            }, 250);
        });

        // Settings panel open/close
        this.el.settingsBtn?.addEventListener('click', () => {
            this.el.settingsPanel.classList.add('active');
            this.el.settingsOverlay.classList.add('active');
        });
        const closePanel = () => {
            this.saveUserSettings();
            this.el.settingsPanel.classList.remove('active');
            this.el.settingsOverlay.classList.remove('active');
        };
        this.el.closeSettingsBtn?.addEventListener('click', closePanel);
        this.el.settingsOverlay?.addEventListener('click', closePanel);

        this.el.nextBtn?.addEventListener('click', this.nextPage);
        this.el.prevBtn?.addEventListener('click', this.prevPage);
        this.el.backBtn?.addEventListener('click', () => {
            window.location.href = '/';
        });

        // Flush any pending (debounced) progress save immediately once the
        // browser signals the page is being hidden — app switch, screen
        // lock, closing the tab, etc. Covers both: visibilitychange fires
        // reliably when the app is backgrounded but the page/process may
        // still be alive; pagehide fires when the page is actually being
        // torn down (navigation away, tab close). Using sendBeacon (via
        // flushProgress(true)) so the request has the best chance of
        // actually completing even as the browser suspends the page.
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                this.flushProgress(true);
            }
        });
        window.addEventListener('pagehide', () => {
            this.flushProgress(true);
        });
    }
}

new PaginatedEReader();
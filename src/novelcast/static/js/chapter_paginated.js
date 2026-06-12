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
    };

    this.iframe = null;
    this.iframeDoc = null;
    this.iframeWin = null;
    this.resizeTimer = null;
    this.repaginateTimer = null;
    this.touch = { startX: 0, endX: 0, threshold: 50 };

    this.settings = {
      theme: 'light',
      fontFamily: 'serif',
      fontSize: 110,
      lineSpacing: 100,
      fontWeight: 1,
      paragraphSpacing: 100,
    };

    this.userLoaded = false;

    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', () => this.init())
      : this.init();
  }

  // ======================
  // INITIALIZATION
  // ======================

  async init() {
    this.cacheContainerData();
    this.cacheElements();
    await this.loadUserSettings();
    this.updateSettingsUI();
    this.attachEvents();
    this.buildIframe();
  }

  async loadUserSettings() {
    try {
      const r = await fetch('/api/chapter-settings', { headers: { 'Content-Type': 'application/json' } });
      if (r.ok) {
        const data = await r.json();
        this.settings = { ...this.settings, ...data.settings };
        this.userLoaded = true;
      }
    } catch (e) { /* use defaults */ }
  }

  async saveUserSettings() {
    if (!this.userLoaded) return;
    try {
      await fetch('/api/chapter-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: this.settings }),
      });
    } catch (e) { /* ignore */ }
  }

  cacheContainerData() {
    const c = document.querySelector('.reader-container');
    if (!c) return;
    this.state.storyId       = c.dataset.storyId;
    this.state.chapterId     = c.dataset.chapterId;
    this.state.nextChapterId = c.dataset.nextChapterId;
    this.state.prevChapterId = c.dataset.prevChapterId;
    this.state.chapterTitle  = c.dataset.chapterTitle || '';
  }

  cacheElements() {
    const $ = id => document.getElementById(id);
    this.el = {
      scrollContainer:        document.querySelector('.chapter-scroll-container'),
      chapterSource:          $('chapterSource'),
      header:                 document.querySelector('.reader-header'),
      settingsBtn:            $('settingsBtn'),
      closeSettingsBtn:       $('closeSettings'),
      settingsPanel:          $('settingsPanel'),
      settingsOverlay:        $('settingsOverlay'),
      lineSpacingSlider:      $('lineSpacingSlider'),
      lineSpacingValue:       $('lineSpacingValue'),
      paragraphSpacingSlider: $('paragraphSpacingSlider'),
      paragraphSpacingValue:  $('paragraphSpacingValue'),
      themeBtns:              document.querySelectorAll('.theme-btn'),
      fontFamilyBtns:         document.querySelectorAll('.font-family-btn'),
      fontSizeBtns:           document.querySelectorAll('.font-size-btn'),
      fontSizeValue:          $('fontSizeValue'),
      fontWeightBtns:         document.querySelectorAll('.font-weight-btn'),
      nextBtn:                $('nextChapterFloating'),
      prevBtn:                $('prevChapter'),
      backBtn:                document.querySelector('.back-btn'),
      pageCounter:            this.createPageCounter(),
    };
  }

  createPageCounter() {
    let el = document.getElementById('pageCounter');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'pageCounter';
    Object.assign(el.style, {
      position: 'fixed', bottom: '1.5rem', left: '50%',
      transform: 'translateX(-50%)', padding: '0.5rem 1rem',
      background: 'rgba(0,0,0,0.6)', color: '#fff',
      borderRadius: '20px', fontSize: '0.85rem',
      zIndex: '9999', pointerEvents: 'none',
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
      display:  'block',
      width:    '100%',
      height:   '100%',
      border:   'none',
      overflow: 'hidden',
    });
    iframe.setAttribute('scrolling', 'no');

    this.el.scrollContainer.appendChild(iframe);
    this.iframe = iframe;
    this.iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    this.iframeWin = iframe.contentWindow;

    const { w, h } = this.getPageSize();
    const cleanContent = this.stripAuthorNotes(this.state.originalContent);
    const titleEscaped = this.state.chapterTitle
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

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

    iframe.addEventListener('load', () => {
    const touchTarget = this.iframeDoc.body;

    touchTarget.addEventListener('touchstart', e => {
      this.touch.startX = e.changedTouches[0].screenX;
      this.touch.startY = e.changedTouches[0].screenY;
    });

    touchTarget.addEventListener('touchend', e => {
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
      requestAnimationFrame(() => {
        this.calculatePages();
        this.render(0);
        this.iframeWin.addEventListener('keydown', e => this.handleKey(e));
      })
    );
  }, { once: true });
  }

  buildCSS(w, h) {
    const fontSize        = ((1.05 * this.settings.fontSize)        / 100).toFixed(3);
    const lineHeight      = ((1.85 * this.settings.lineSpacing)     / 100).toFixed(3);
    const fontWeight      = [300, 400, 700][this.settings.fontWeight] ?? 400;
    const paragraphMargin = ((1.5  * this.settings.paragraphSpacing)/ 100).toFixed(3);

    const themes = {
      light: { bg: '#faf8f3', text: '#2c2c2c', secondary: '#666', accent: '#3b82f6', hr: 'rgba(0,0,0,0.12)' },
      sepia: { bg: '#f4eee6', text: '#5c4033', secondary: '#8d6e63', accent: '#8d6e63', hr: 'rgba(0,0,0,0.08)' },
      dark:  { bg: '#1a1a1a', text: '#e8e8e8', secondary: '#a8a8a8', accent: '#60a5fa', hr: 'rgba(255,255,255,0.1)' },
    };
    const c = themes[this.settings.theme] || themes.light;

    const fontSerif = `Georgia, "Noto Serif", "Times New Roman", serif`;
    const fontSans  = `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
    const fontStack = this.settings.fontFamily === 'sans' ? fontSans : fontSerif;

    return `
      * { box-sizing: border-box; margin: 0; padding: 0; }

      html, body {
        width:    ${w}px;
        height:   ${h}px;
        overflow: hidden;
        background: ${c.bg};
      }

      /* The column container spans as wide as needed for all pages */
      #columns {
        width:               ${w}px;
        height:              ${h}px;
        /* CSS columns: each column = one page */
        column-width:        ${w}px;
        column-gap:          0px;
        /* Start at page 0 */
        transform:           translateX(0);
        will-change:         transform;
      }

      /* Content flows naturally into columns */
      #content {
        font-family: ${fontStack};
        font-size:   ${fontSize}rem;
        line-height: ${lineHeight};
        font-weight: ${fontWeight};
        color:       ${c.text};
        padding:     2rem 3rem;
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
        column-span:    none;
      }

      .chapter-divider {
        border:        none;
        border-top:    1px solid ${c.hr};
        margin-bottom: 1.25rem;
        break-after:   avoid;
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

      /* Hide author notes */
      .author-note,
      .author-note-portlet,
      .portlet-body.author-note,
      .portlet.solid.author-note-portlet { display: none !important; }
    `;
  }

  stripAuthorNotes(html) {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    temp.querySelectorAll(
      '.author-note-portlet, .portlet.solid.author-note-portlet, .author-note, .portlet-body.author-note'
    ).forEach(el => el.remove());
    return temp.innerHTML;
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
      // Slide the column strip left by one page width per page
      columnsEl.style.transform = `translateX(${-i * w}px)`;
    }

    this.updateUI();
  }

  repaginate(targetPage) {
    clearTimeout(this.repaginateTimer);
    this.repaginateTimer = setTimeout(() => {
      this.buildIframe();
      this.iframe.addEventListener('load', () => {
        requestAnimationFrame(() => requestAnimationFrame(() => {
          this.render(Math.min(targetPage, this.state.totalPages - 1));
        }));
      }, { once: true });
    }, 50);
  }

  updateUI() {
    const { currentPage, totalPages } = this.state;
    if (this.el.pageCounter)
      this.el.pageCounter.textContent = `${currentPage + 1} / ${totalPages}`;
    if (this.el.prevBtn)
      this.el.prevBtn.style.opacity = currentPage === 0 ? '0.3' : '0.8';
    if (this.el.nextBtn)
      this.el.nextBtn.style.opacity = currentPage === totalPages - 1 ? '0.3' : '0.8';
  }

  // ======================
  // NAVIGATION
  // ======================

  nextPage = () => {
    const { currentPage, totalPages, nextChapterId, storyId } = this.state;
    const cleanNext = (!nextChapterId || nextChapterId === 'None') ? null : nextChapterId;
    if (currentPage < totalPages - 1) this.render(currentPage + 1);
    else if (cleanNext) window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanNext}`;
    else window.location.href = `/story?story_id=${storyId}`;
  };

  prevPage = () => {
    const { currentPage, prevChapterId, storyId } = this.state;
    const cleanPrev = (!prevChapterId || prevChapterId === 'None') ? null : prevChapterId;
    if (currentPage > 0) this.render(currentPage - 1);
    else if (cleanPrev) window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanPrev}&lastPage=1`;
    else window.location.href = `/story?story_id=${storyId}`;
  };

  handleKey(e) {
    if (['ArrowRight', 'ArrowDown', ' '].includes(e.key)) { e.preventDefault(); this.nextPage(); }
    if (['ArrowLeft',  'ArrowUp'        ].includes(e.key)) { e.preventDefault(); this.prevPage(); }
  }

  // ======================
  // SETTINGS
  // ======================

  updateSettingsUI() {
    const sizeLabels = {
      75: '12',
      88: '14',
      100: '16',
      113: '18',
      125: '20',
      150: '24',
      225: '36'
    };
    this.el.themeBtns.forEach(b =>
      b.classList.toggle('active', b.dataset.theme === this.settings.theme));
    this.el.fontFamilyBtns.forEach(b =>
      b.classList.toggle('active', b.dataset.font === this.settings.fontFamily));
    this.el.fontSizeBtns.forEach(b =>
      b.classList.toggle('active', Number(b.dataset.size) === this.settings.fontSize));
    if (this.el.fontSizeValue)
      this.el.fontSizeValue.textContent = sizeLabels[this.settings.fontSize] ?? '16';
    this.el.fontWeightBtns.forEach(b =>
      b.classList.toggle('active', Number(b.dataset.weight) === this.settings.fontWeight));
    if (this.el.lineSpacingSlider) {
      this.el.lineSpacingSlider.value = this.settings.lineSpacing;
      if (this.el.lineSpacingValue)
        this.el.lineSpacingValue.textContent = this.settings.lineSpacing + '%';
    }
    if (this.el.paragraphSpacingSlider) {
      this.el.paragraphSpacingSlider.value = this.settings.paragraphSpacing;
      if (this.el.paragraphSpacingValue)
        this.el.paragraphSpacingValue.textContent = this.settings.paragraphSpacing + '%';
    }
  }

  // ======================
  // EVENTS
  // ======================

  attachEvents() {
    // Keyboard on the outer page
    document.addEventListener('keydown', e => this.handleKey(e));

    // Touch swipe
    const sc = this.el.scrollContainer;
    if (sc) {
      sc.addEventListener('touchstart', e => {
        this.touch.startX = e.changedTouches[0].screenX;
      }, { passive: true });
      sc.addEventListener('touchend', e => {
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

    // Settings changes
    this.el.themeBtns.forEach(btn => btn.addEventListener('click', e => {
      this.settings.theme = e.currentTarget.dataset.theme;
      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);
      this.saveUserSettings();
    }));

    this.el.fontFamilyBtns.forEach(btn => btn.addEventListener('click', e => {
      this.settings.fontFamily = e.currentTarget.dataset.font;
      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);
      this.saveUserSettings();
    }));

    this.el.fontSizeBtns.forEach(btn => btn.addEventListener('click', e => {
      this.settings.fontSize = Number(e.currentTarget.dataset.size);
      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);
      this.saveUserSettings();
    }));

    this.el.lineSpacingSlider?.addEventListener('input', e => {
      if (this.el.lineSpacingValue)
        this.el.lineSpacingValue.textContent = e.target.value + '%';
    });
    this.el.lineSpacingSlider?.addEventListener('input', e => {
      this.settings.lineSpacing = Number(e.target.value);

      if (this.el.lineSpacingValue) {
        this.el.lineSpacingValue.textContent = e.target.value + '%';
      }

      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);

      clearTimeout(this.lineSpacingSaveTimer);
      this.lineSpacingSaveTimer = setTimeout(() => {
        this.saveUserSettings();
      }, 300);
    });

    this.el.fontWeightBtns.forEach(btn => btn.addEventListener('click', e => {
      this.settings.fontWeight = Number(e.currentTarget.dataset.weight);
      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);
      this.saveUserSettings();
    }));

    this.el.paragraphSpacingSlider?.addEventListener('input', e => {
      if (this.el.paragraphSpacingValue)
        this.el.paragraphSpacingValue.textContent = e.target.value + '%';
    });
    this.el.paragraphSpacingSlider?.addEventListener('input', e => {
      this.settings.paragraphSpacing = Number(e.target.value);

      if (this.el.paragraphSpacingValue) {
        this.el.paragraphSpacingValue.textContent = e.target.value + '%';
      }

      this.updateSettingsUI();
      this.repaginate(this.state.currentPage);

      clearTimeout(this.paragraphSaveTimer);
      this.paragraphSaveTimer = setTimeout(() => {
        this.saveUserSettings();
      }, 300);
    });

    this.el.nextBtn?.addEventListener('click', this.nextPage);
    this.el.prevBtn?.addEventListener('click', this.prevPage);
    this.el.backBtn?.addEventListener('click', () => { window.location.href = '/'; });
  }
}

new PaginatedEReader();
class PaginatedEReader {
  constructor() {
    console.log('🚀 Paginated E-Reader loaded');

    this.state = {
      storyId: null,
      chapterId: null,
      nextChapterId: null,
      prevChapterId: null,
      currentPage: 0,
      totalPages: 0,
      pages: [],
      originalContent: null,
    };

    this.resizeTimer = null;
    this.touch = { startX: 0, endX: 0, threshold: 50 };

    this.settings = {
      theme: localStorage.getItem('novelcast_theme') || 'light',
      fontFamily: localStorage.getItem('novelcast_fontFamily') || 'serif',
      fontSize: Number(localStorage.getItem('novelcast_fontSize')) || 100,
      lineSpacing: Number(localStorage.getItem('novelcast_lineSpacing')) || 100,
      fontWeight: Number(localStorage.getItem('novelcast_fontWeight')) || 0,
    };

    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', () => this.init())
      : this.init();
  }

  // ======================
  // INIT
  // ======================

  init() {
    console.log('⚙️ Initializing E-Reader...');

    this.cacheContainerData();
    this.cacheElements();
    this.applySettings();
    this.attachEvents();

    this.paginate();
    this.render(0);

    console.log('✅ Ready. Pages:', this.state.totalPages);
  }

  cacheContainerData() {
    const container = document.querySelector('.reader-container');
    if (!container) return;

    Object.assign(this.state, container.dataset);
  }

  cacheElements() {
    const $ = (id) => document.getElementById(id);

    this.el = {
      container: document.querySelector('.chapter-text'),
      header: document.querySelector('.reader-header'),

      settingsBtn: $('settingsBtn'),
      closeSettingsBtn: $('closeSettings'),
      settingsPanel: $('settingsPanel'),
      settingsOverlay: $('settingsOverlay'),

      fontSizeSlider: $('fontSizeSlider'),
      fontSizeValue: $('fontSizeValue'),
      lineSpacingSlider: $('lineSpacingSlider'),
      lineSpacingValue: $('lineSpacingValue'),
      fontWeightSlider: $('fontWeightSlider'),
      fontWeightValue: $('fontWeightValue'),

      themeBtns: document.querySelectorAll('.theme-btn'),
      fontFamilyBtns: document.querySelectorAll('.font-family-btn'),

      nextBtn: $('nextChapterFloating'),
      prevBtn: $('prevChapter'),
      nextChapterBtn: $('nextChapterBtn'),
      backBtn: document.querySelector('.back-btn'),

      pageCounter: this.createPageCounter(),
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
  // PAGINATION ENGINE
  // ======================

  paginate() {
    const container = this.el.container;
    if (!container) return;

    if (!this.state.originalContent) {
      this.state.originalContent = container.innerHTML;
    }

    this.state.pages = [];

    const temp = document.createElement('div');
    temp.innerHTML = this.state.originalContent;

    const elements = [...temp.querySelectorAll('p, blockquote, ul, ol, h2, h3')];

    const page = this.createPageMeasurer(container);
    const maxHeight = this.getAvailableHeight();

    const flush = () => {
      if (page.innerHTML.trim()) {
        this.state.pages.push(page.innerHTML);
        page.innerHTML = '';
      }
    };

    for (const elem of elements) {
      const clone = elem.cloneNode(true);
      page.appendChild(clone);

      // Check if it fits
      if (page.scrollHeight <= maxHeight) {
        // ✅ Fits! Keep it on this page
        continue;
      }

      // ❌ Doesn't fit - remove it
      page.removeChild(clone);

      // If page is empty, force add this element (prevent infinite loop)
      if (!page.innerHTML.trim()) {
        page.appendChild(clone);
        console.warn('⚠️ Element larger than page height:', elem.tagName);
      }

      // Flush current page
      flush();

      // If element didn't fit and we added it to empty page, continue to next
      if (!page.innerHTML.trim()) {
        page.appendChild(clone);
      }
    }

    flush();
    page.remove();

    this.state.totalPages = Math.max(1, this.state.pages.length);

    console.log('✅ Pagination complete:', this.state.totalPages, 'pages');
  }

  createPageMeasurer(container) {
    const page = container.cloneNode(false);
    const style = getComputedStyle(container);

    Object.assign(page.style, {
      position: 'absolute',
      visibility: 'hidden',
      left: '-9999px',
      top: '0',

      width: container.clientWidth + 'px',
      minHeight: this.getAvailableHeight() + 'px',

      fontFamily: style.fontFamily,
      fontSize: style.fontSize,
      fontWeight: style.fontWeight,
      lineHeight: style.lineHeight,

      letterSpacing: style.letterSpacing,
      wordSpacing: style.wordSpacing,

      padding: style.padding,
      margin: style.margin,

      boxSizing: 'border-box',

      overflow: 'visible',
      whiteSpace: 'normal',
    });

    document.body.appendChild(page);
    return page;
  }

  getAvailableHeight() {
    const headerH = this.el.header?.offsetHeight || 70;
    return window.innerHeight - headerH - 180;
  }

  // ======================
  // RENDERING
  // ======================

  render(index) {
    const { pages } = this.state;
    if (!pages.length || index < 0 || index >= pages.length) return;

    this.state.currentPage = index;
    this.el.container.innerHTML = pages[index];

    this.updateUI();
  }

  updateUI() {
    const { currentPage, totalPages } = this.state;

    this.el.pageCounter.textContent = `${currentPage + 1} / ${totalPages}`;

    const isFirst = currentPage === 0;
    const isLast = currentPage === totalPages - 1;

    if (this.el.prevBtn) this.el.prevBtn.style.opacity = isFirst ? '0.3' : '0.8';
    if (this.el.nextBtn) this.el.nextBtn.style.opacity = isLast ? '0.3' : '0.8';
  }

  // ======================
  // NAVIGATION
  // ======================

  nextPage = () => {
    const { currentPage, totalPages, nextChapterId, storyId } = this.state;

    if (currentPage < totalPages - 1) {
      this.render(currentPage + 1);
    } else if (nextChapterId) {
      window.location.href = `/chapter?story_id=${storyId}&chapter_id=${nextChapterId}`;
    }
  };

  prevPage = () => {
    const { currentPage, prevChapterId, storyId } = this.state;

    if (currentPage > 0) {
      this.render(currentPage - 1);
    } else if (prevChapterId) {
      window.location.href = `/chapter?story_id=${storyId}&chapter_id=${prevChapterId}&lastPage=1`;
    }
  };

  // ======================
  // SETTINGS
  // ======================

  applySettings() {
    document.body.dataset.theme = this.settings.theme;

    if (this.settings.fontFamily === 'sans') {
      document.body.classList.add('font-sans');
    } else {
      document.body.classList.remove('font-sans');
    }

    this.applyCSSVariables();
    this.updateSettingsUI();
  }

  applyCSSVariables() {
    const root = document.documentElement;

    const baseFontSize = 1.05;
    const fontSize = (baseFontSize * this.settings.fontSize) / 100;
    root.style.setProperty('--font-size-base', fontSize + 'rem');

    const baseLineHeight = 1.85;
    const lineHeight = (baseLineHeight * this.settings.lineSpacing) / 100;
    root.style.setProperty('--line-height', lineHeight);

    const fontWeight = 400 + this.settings.fontWeight * 3;
    root.style.setProperty('--font-weight', fontWeight);
  }

  updateSettingsUI() {
    this.el.themeBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === this.settings.theme);
    });

    this.el.fontFamilyBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.font === this.settings.fontFamily);
    });

    if (this.el.fontSizeSlider) {
      this.el.fontSizeSlider.value = this.settings.fontSize;
      if (this.el.fontSizeValue) this.el.fontSizeValue.textContent = this.settings.fontSize + '%';
    }

    if (this.el.lineSpacingSlider) {
      this.el.lineSpacingSlider.value = this.settings.lineSpacing;
      if (this.el.lineSpacingValue) this.el.lineSpacingValue.textContent = this.settings.lineSpacing + '%';
    }

    if (this.el.fontWeightSlider) {
      this.el.fontWeightSlider.value = this.settings.fontWeight;
      const weight = this.settings.fontWeight;
      if (weight <= 30) {
        this.el.fontWeightValue.textContent = 'Light';
      } else if (weight <= 70) {
        this.el.fontWeightValue.textContent = 'Normal';
      } else {
        this.el.fontWeightValue.textContent = 'Bold';
      }
    }
  }

  saveSettings() {
    localStorage.setItem('novelcast_theme', this.settings.theme);
    localStorage.setItem('novelcast_fontFamily', this.settings.fontFamily);
    localStorage.setItem('novelcast_fontSize', this.settings.fontSize);
    localStorage.setItem('novelcast_lineSpacing', this.settings.lineSpacing);
    localStorage.setItem('novelcast_fontWeight', this.settings.fontWeight);
  }

  // ======================
  // EVENTS
  // ======================

  attachEvents() {
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (['ArrowRight', 'ArrowDown', ' '].includes(e.key)) {
        e.preventDefault();
        this.nextPage();
      }

      if (['ArrowLeft', 'ArrowUp'].includes(e.key)) {
        e.preventDefault();
        this.prevPage();
      }
    });

    // Touch swipe
    const container = document.querySelector('.chapter-scroll-container');
    if (container) {
      container.addEventListener('touchstart', (e) => {
        this.touch.startX = e.changedTouches[0].screenX;
      });

      container.addEventListener('touchend', (e) => {
        this.touch.endX = e.changedTouches[0].screenX;
        const diff = this.touch.startX - this.touch.endX;

        if (diff > this.touch.threshold) {
          this.nextPage();
        } else if (diff < -this.touch.threshold) {
          this.prevPage();
        }
      });
    }

    // Window resize - re-paginate
    window.addEventListener('resize', () => {
      clearTimeout(this.resizeTimer);

      this.resizeTimer = setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 200);
    });

    // Settings panel
    this.el.settingsBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      this.el.settingsPanel.classList.add('active');
      this.el.settingsOverlay.classList.add('active');
    });

    this.el.closeSettingsBtn?.addEventListener('click', () => {
      this.el.settingsPanel.classList.remove('active');
      this.el.settingsOverlay.classList.remove('active');
    });

    this.el.settingsOverlay?.addEventListener('click', () => {
      this.el.settingsPanel.classList.remove('active');
      this.el.settingsOverlay.classList.remove('active');
    });

    // Theme buttons
    this.el.themeBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.settings.theme = e.currentTarget.dataset.theme;
        this.applySettings();
        this.saveSettings();
      });
    });

    // Font family buttons
    this.el.fontFamilyBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.settings.fontFamily = e.currentTarget.dataset.font;
        this.applySettings();
        this.saveSettings();
      });
    });

    // Font size slider
    this.el.fontSizeSlider?.addEventListener('input', (e) => {
      this.settings.fontSize = Number(e.target.value);
      this.applyCSSVariables();
      this.saveSettings();

      // Re-paginate after font size changes
      setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 100);
    });

    // Line spacing slider
    this.el.lineSpacingSlider?.addEventListener('input', (e) => {
      this.settings.lineSpacing = Number(e.target.value);
      this.applyCSSVariables();
      this.saveSettings();

      // Re-paginate after line spacing changes
      setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 100);
    });

    // Font weight slider
    this.el.fontWeightSlider?.addEventListener('input', (e) => {
      this.settings.fontWeight = Number(e.target.value);
      this.applyCSSVariables();
      this.saveSettings();
      this.updateSettingsUI();
    });

    // Navigation buttons
    this.el.nextBtn?.addEventListener('click', this.nextPage);
    this.el.prevBtn?.addEventListener('click', this.prevPage);
    this.el.nextChapterBtn?.addEventListener('click', () => {
      if (this.state.nextChapterId) {
        window.location.href = `/chapter?story_id=${this.state.storyId}&chapter_id=${this.state.nextChapterId}`;
      }
    });
    this.el.backBtn?.addEventListener('click', () => {
      window.location.href = '/';
    });
  }
}

// INIT
console.log('🚀 E-Reader script loaded');
new PaginatedEReader();
/**
 * novelcast/static/js/chapter_paginated.js - UPDATED
 * 
 * Paginated e-reader with improved settings panel
 * - Font size as buttons (12, 14, 16, 18, 20)
 * - Font weight as buttons (Light, Normal, Bold)
 * - Smaller settings panel positioned on right side
 */

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

    // Default settings
    this.settings = {
      theme: 'light',
      fontFamily: 'serif',
      fontSize: 110,          // 16px (default)
      lineSpacing: 100,
      fontWeight: 1,          // 0=Light, 1=Normal, 2=Bold
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
    console.log('⚙️ Initializing E-Reader...');

    this.cacheContainerData();
    this.cacheElements();
    await this.loadUserSettings();
    this.applySettings();
    this.attachEvents();
    this.paginate();
    this.render(0);

    console.log('✅ Ready. Pages:', this.state.totalPages);
  }

  async loadUserSettings() {
    try {
      const response = await fetch('/api/chapter-settings', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        this.settings = { ...this.settings, ...data.settings };
        this.userLoaded = true;
        console.log('✅ User settings loaded');
      } else {
        console.log('ℹ️ Using default settings');
      }
    } catch (err) {
      console.warn('⚠️ Could not load user settings:', err);
    }
  }

  async saveUserSettings() {
    if (!this.userLoaded) return;

    try {
      const response = await fetch('/api/chapter-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: this.settings }),
      });

      if (response.ok) {
        console.log('✅ Settings saved');
      }
    } catch (err) {
      console.warn('⚠️ Could not save settings:', err);
    }
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
      lineSpacingSlider: $('lineSpacingSlider'),
      lineSpacingValue: $('lineSpacingValue'),
      paragraphSpacingSlider: $('paragraphSpacingSlider'),
      paragraphSpacingValue: $('paragraphSpacingValue'),
      themeBtns: document.querySelectorAll('.theme-btn'),
      fontFamilyBtns: document.querySelectorAll('.font-family-btn'),
      fontSizeBtns: document.querySelectorAll('.font-size-btn'),
      fontSizeValue: $('fontSizeValue'),
      fontWeightBtns: document.querySelectorAll('.font-weight-btn'),
      nextBtn: $('nextChapterFloating'),
      prevBtn: $('prevChapter'),
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

  getAvailableHeight() {
    const headerH = this.el.header?.offsetHeight || 70;
    return window.innerHeight - headerH - 120;
  }

  createPageMeasurer(container) {
    const page = document.createElement('div');

    Object.assign(page.style, {
      position: 'absolute',
      visibility: 'hidden',
      left: '-9999px',
      top: '0',
      width: container.clientWidth + 'px',
      minHeight: this.getAvailableHeight() + 'px',
      boxSizing: 'border-box',
      overflow: 'visible',
      whiteSpace: 'normal',
      padding: getComputedStyle(container).padding,
      margin: '0',
    });

    document.body.appendChild(page);
    return page;
  }

  splitParagraphIfNeeded(elem, measurer, maxHeight) {
    const clone = elem.cloneNode(true);
    measurer.innerHTML = '';
    measurer.appendChild(clone);

    if (measurer.scrollHeight <= maxHeight) {
      return [elem];
    }

    const text = elem.textContent;
    const words = text.split(/\s+/).filter(w => w.length > 0);

    if (words.length <= 1) {
      return [elem];
    }

    const chunks = [];
    let currentChunk = [];

    for (const word of words) {
      currentChunk.push(word);

      const testClone = elem.cloneNode(false);
      testClone.textContent = currentChunk.join(' ');
      measurer.innerHTML = '';
      measurer.appendChild(testClone);

      if (measurer.scrollHeight > maxHeight) {
        if (currentChunk.length > 1) {
          currentChunk.pop();
          const p = elem.cloneNode(false);
          p.textContent = currentChunk.join(' ');
          chunks.push(p);
          currentChunk = [word];
        } else {
          const p = elem.cloneNode(false);
          p.textContent = word;
          chunks.push(p);
          currentChunk = [];
        }
      }
    }

    if (currentChunk.length > 0) {
      const p = elem.cloneNode(false);
      p.textContent = currentChunk.join(' ');
      chunks.push(p);
    }

    return chunks.length > 0 ? chunks : [elem];
  }

  paginate() {
    const container = this.el.container;
    if (!container) return;

    if (!this.state.originalContent) {
      this.state.originalContent = container.innerHTML;
    }

    this.state.pages = [];

    const temp = document.createElement('div');
    temp.innerHTML = this.state.originalContent;

    temp.querySelectorAll('.author-note-portlet').forEach(el => el.remove());
    temp.querySelectorAll('.portlet.solid.author-note-portlet').forEach(el => el.remove());
    temp.querySelectorAll('.author-note').forEach(el => el.remove());

    const elements = [...temp.querySelectorAll('p, blockquote, ul, ol, h2, h3, div')].filter(
      el => el.textContent.trim().length > 0 && !el.querySelector('p, ul, ol, blockquote, h2, h3')
    );

    const measurer = this.createPageMeasurer(container);
    const maxHeight = this.getAvailableHeight();
    const pages = [];
    let currentPageHTML = '';
    let currentPageHeight = 0;

    for (const elem of elements) {
      const elemClone = elem.cloneNode(true);

      const testContainer = document.createElement('div');
      testContainer.innerHTML = currentPageHTML;
      testContainer.appendChild(elemClone.cloneNode(true));

      measurer.innerHTML = testContainer.innerHTML;
      const testHeight = measurer.scrollHeight;

      if (testHeight <= maxHeight) {
        currentPageHTML = testContainer.innerHTML;
        currentPageHeight = testHeight;
      } else if (currentPageHTML.trim()) {
        pages.push(currentPageHTML);
        currentPageHTML = elemClone.outerHTML;
        currentPageHeight = 0;

        measurer.innerHTML = elemClone.outerHTML;
        currentPageHeight = measurer.scrollHeight;

        if (currentPageHeight > maxHeight) {
          const split = this.splitParagraphIfNeeded(elem, measurer, maxHeight);

          for (const piece of split) {
            measurer.innerHTML = piece.outerHTML;
            if (measurer.scrollHeight > maxHeight) {
              if (currentPageHTML !== piece.outerHTML) {
                pages.push(currentPageHTML);
                currentPageHTML = piece.outerHTML;
              }
              currentPageHeight = measurer.scrollHeight;
            } else {
              if (currentPageHTML && currentPageHTML !== piece.outerHTML) {
                const testDiv = document.createElement('div');
                testDiv.innerHTML = currentPageHTML + piece.outerHTML;
                measurer.innerHTML = testDiv.innerHTML;

                if (measurer.scrollHeight <= maxHeight) {
                  currentPageHTML += piece.outerHTML;
                  currentPageHeight = measurer.scrollHeight;
                } else {
                  pages.push(currentPageHTML);
                  currentPageHTML = piece.outerHTML;
                  measurer.innerHTML = currentPageHTML;
                  currentPageHeight = measurer.scrollHeight;
                }
              } else {
                currentPageHTML = piece.outerHTML;
                currentPageHeight = measurer.scrollHeight;
              }
            }
          }
        }
      } else {
        currentPageHTML = elemClone.outerHTML;
        measurer.innerHTML = currentPageHTML;
        currentPageHeight = measurer.scrollHeight;

        if (currentPageHeight > maxHeight) {
          const split = this.splitParagraphIfNeeded(elem, measurer, maxHeight);

          currentPageHTML = '';
          for (const piece of split) {
            measurer.innerHTML = piece.outerHTML;
            const pieceHeight = measurer.scrollHeight;

            if (pieceHeight > maxHeight) {
              if (currentPageHTML) {
                pages.push(currentPageHTML);
              }
              pages.push(piece.outerHTML);
              currentPageHTML = '';
              currentPageHeight = 0;
            } else {
              if (currentPageHTML) {
                const testDiv = document.createElement('div');
                testDiv.innerHTML = currentPageHTML + piece.outerHTML;
                measurer.innerHTML = testDiv.innerHTML;

                if (measurer.scrollHeight <= maxHeight) {
                  currentPageHTML += piece.outerHTML;
                  currentPageHeight = measurer.scrollHeight;
                } else {
                  pages.push(currentPageHTML);
                  currentPageHTML = piece.outerHTML;
                  currentPageHeight = pieceHeight;
                }
              } else {
                currentPageHTML = piece.outerHTML;
                currentPageHeight = pieceHeight;
              }
            }
          }
        }
      }
    }

    if (currentPageHTML.trim()) {
      pages.push(currentPageHTML);
    }

    this.state.pages = pages;
    this.state.totalPages = Math.max(1, pages.length);
    measurer.remove();

    console.log('✅ Pagination complete:', this.state.totalPages, 'pages');
  }

  // ======================
  // RENDERING
  // ======================

  render(index) {
    if (index < 0 || index >= this.state.pages.length) return;

    this.state.currentPage = index;
    this.el.container.innerHTML = this.state.pages[index];
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
    const cleanNextChapterId = nextChapterId === "None" ? null : nextChapterId;

    if (currentPage < totalPages - 1) {
      this.render(currentPage + 1);
    } else if (cleanNextChapterId) {
      window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanNextChapterId}`;
    } else {
      window.location.href = `/story?story_id=${storyId}`;
    }
  };

  prevPage = () => {
    const { currentPage, prevChapterId, storyId } = this.state;
    const cleanPrevChapterId = prevChapterId === "None" ? null : prevChapterId;

    if (currentPage > 0) {
      this.render(currentPage - 1);
    } else if (cleanPrevChapterId) {
      window.location.href = `/chapter?story_id=${storyId}&chapter_id=${cleanPrevChapterId}&lastPage=1`;
    } else {
      window.location.href = `/story?story_id=${storyId}`;
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

    // Font size (convert percentage to rem)
    const baseFontSize = 1.05;
    const fontSize = (baseFontSize * this.settings.fontSize) / 100;
    root.style.setProperty('--font-size-base', fontSize + 'rem');

    const baseLineHeight = 1.85;
    const lineHeight = (baseLineHeight * this.settings.lineSpacing) / 100;
    root.style.setProperty('--line-height', lineHeight);

    // Font weight (0=400, 1=400, 2=400+100*3=700)
    const fontWeights = [400, 400, 700]; // Light, Normal, Bold
    const fontWeight = fontWeights[this.settings.fontWeight] || 400;
    root.style.setProperty('--font-weight', fontWeight);

    const baseParagraphMargin = 1.5;
    const paragraphMargin = (baseParagraphMargin * this.settings.paragraphSpacing) / 100;
    root.style.setProperty('--paragraph-margin', paragraphMargin + 'rem');
  }

  updateSettingsUI() {
    // Theme buttons
    this.el.themeBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === this.settings.theme);
    });

    // Font family buttons
    this.el.fontFamilyBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.font === this.settings.fontFamily);
    });

    // Font size buttons (80=12, 95=14, 110=16, 125=18, 145=20)
    const fontSizeMap = {
      80: '12',
      95: '14',
      110: '16',
      125: '18',
      145: '20',
    };

    this.el.fontSizeBtns.forEach(btn => {
      btn.classList.toggle('active', Number(btn.dataset.size) === this.settings.fontSize);
    });

    if (this.el.fontSizeValue) {
      this.el.fontSizeValue.textContent = fontSizeMap[this.settings.fontSize] || '16';
    }

    // Line spacing slider
    if (this.el.lineSpacingSlider) {
      this.el.lineSpacingSlider.value = this.settings.lineSpacing;
      if (this.el.lineSpacingValue) this.el.lineSpacingValue.textContent = this.settings.lineSpacing + '%';
    }

    // Font weight buttons
    this.el.fontWeightBtns.forEach(btn => {
      btn.classList.toggle('active', Number(btn.dataset.weight) === this.settings.fontWeight);
    });

    // Paragraph spacing slider
    if (this.el.paragraphSpacingSlider) {
      this.el.paragraphSpacingSlider.value = this.settings.paragraphSpacing;
      if (this.el.paragraphSpacingValue) this.el.paragraphSpacingValue.textContent = this.settings.paragraphSpacing + '%';
    }
  }

  // ======================
  // EVENTS
  // ======================

  attachEvents() {
    // Keyboard
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

    // Window resize
    window.addEventListener('resize', () => {
      clearTimeout(this.resizeTimer);
      this.resizeTimer = setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 200);
    });

    // Settings panel
    this.el.settingsBtn?.addEventListener('click', () => {
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
        this.saveUserSettings();
      });
    });

    // Font family buttons
    this.el.fontFamilyBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.settings.fontFamily = e.currentTarget.dataset.font;
        this.applySettings();
        this.saveUserSettings();
      });
    });

    // Font size buttons
    this.el.fontSizeBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.settings.fontSize = Number(e.currentTarget.dataset.size);
        this.applyCSSVariables();
        this.updateSettingsUI();
        this.saveUserSettings();

        // Re-paginate after font size changes
        setTimeout(() => {
          const page = this.state.currentPage;
          this.paginate();
          this.render(Math.min(page, this.state.totalPages - 1));
        }, 100);
      });
    });

    // Line spacing slider
    this.el.lineSpacingSlider?.addEventListener('input', (e) => {
      this.settings.lineSpacing = Number(e.target.value);
      this.applyCSSVariables();
      this.updateSettingsUI();
      this.saveUserSettings();

      setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 100);
    });

    // Font weight buttons
    this.el.fontWeightBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.settings.fontWeight = Number(e.currentTarget.dataset.weight);
        this.applyCSSVariables();
        this.updateSettingsUI();
        this.saveUserSettings();
      });
    });

    // Paragraph spacing slider
    this.el.paragraphSpacingSlider?.addEventListener('input', (e) => {
      this.settings.paragraphSpacing = Number(e.target.value);
      this.applyCSSVariables();
      this.updateSettingsUI();
      this.saveUserSettings();

      setTimeout(() => {
        const page = this.state.currentPage;
        this.paginate();
        this.render(Math.min(page, this.state.totalPages - 1));
      }, 100);
    });

    // Navigation buttons
    this.el.nextBtn?.addEventListener('click', this.nextPage);
    this.el.prevBtn?.addEventListener('click', this.prevPage);
    this.el.backBtn?.addEventListener('click', () => {
      window.location.href = '/';
    });
  }
}

// INIT
console.log('🚀 E-Reader script loaded');
new PaginatedEReader();
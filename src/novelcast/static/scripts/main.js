document.addEventListener('DOMContentLoaded', function () {
  const readerUI = document.querySelector('.reader-ui');
  const chapterContent = document.querySelector('.chapter-content');
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('reading-progress-text');

  let fontSize = 1.1;
  let theme = 'light';

  function applyFont() {
    if (chapterContent) {
      chapterContent.style.fontSize = fontSize + 'rem';
    }
  }

  window.changeFont = function (delta) {
    fontSize = Math.min(1.6, Math.max(0.9, fontSize + delta * 0.1));
    applyFont();
  };

  window.setTheme = function (t) {
    theme = t;
    document.body.classList.remove('light', 'dark', 'sepia');
    document.body.classList.add(t);
  };

  function updateProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.body.scrollHeight - window.innerHeight;

    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;

    if (progressBar) {
      progressBar.style.width = progress + '%';
    }

    if (progressText) {
      progressText.textContent = Math.round(progress) + '% read';
    }
  }

  window.addEventListener('scroll', updateProgress);

  if (readerUI) {
    let uiVisible = true;

    document.addEventListener('click', (e) => {
      // ignore clicks on controls or links
      if (e.target.closest('a') || e.target.closest('button')) return;

      uiVisible = !uiVisible;
      readerUI.classList.toggle('hidden', !uiVisible);
    });
  }

  if (readerUI) {
    let lastScrollY = window.scrollY;

    window.addEventListener('scroll', () => {
      if (window.scrollY > lastScrollY) {
        readerUI.classList.add('hidden');
      } else {
        readerUI.classList.remove('hidden');
      }

      lastScrollY = window.scrollY;
    });
  }

  let touchStartX = 0;

  document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
  });

  document.addEventListener('touchend', (e) => {
    const touchEndX = e.changedTouches[0].screenX;
    const threshold = 50;

    const nextBtn = document.querySelector('.nav-button.next');
    const prevBtn = document.querySelector('.nav-button.prev');

    if (touchEndX < touchStartX - threshold && nextBtn) {
      navigateWithTransition(nextBtn.href);
    }

    if (touchEndX > touchStartX + threshold && prevBtn) {
      navigateWithTransition(prevBtn.href);
    }
  });

  function navigateWithTransition(url) {
    if (!url) return;

    chapterContent?.classList.add('chapter-transition-out');
    readerUI?.classList.add('chapter-transition-out');

    setTimeout(() => {
      window.location.href = url;
    }, 250);
  }

  document.querySelectorAll('.nav-button').forEach((btn) => {
    btn.addEventListener('click', function (e) {
      const url = this.getAttribute('href');

      if (!url || url.startsWith('#')) return;

      e.preventDefault();
      navigateWithTransition(url);
    });
  });

  window.addEventListener('load', () => {
    chapterContent?.classList.add('chapter-transition-in');
    readerUI?.classList.add('chapter-transition-in');

    applyFont();
    updateProgress();
  });
});

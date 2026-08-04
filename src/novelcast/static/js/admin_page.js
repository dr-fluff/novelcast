window.syncStory = function syncStory() {
    fetch('/api/sync/update/all', { method: 'POST' });
};

// novelcast/static/js/admin_page.js

// ── Health check ─────────────────────────────────────────────────────────────

const STATUS_LABEL = {
    healthy: 'Healthy',
    warning: 'Warning',
    not_healthy: 'Not Healthy',
    not_configured: 'Not Configured',
};

window.runHealthCheck = async function runHealthCheck() {
    const btn = document.querySelector('[onclick="runHealthCheck()"]');
    if (btn) {
        btn.textContent = 'Checking…';
        btn.disabled = true;
    }

    try {
        const res = await fetch('/admin/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        renderHealthChecks(await res.json());
    } catch (err) {
        console.error('Health check failed:', err);
    } finally {
        if (btn) {
            btn.textContent = 'Run Check';
            btn.disabled = false;
        }
    }
};

function renderHealthChecks(checks) {
    const list = document.querySelector('.health-list');
    if (!list) return;
    list.innerHTML = checks
        .map(
            (c) => `
    <div class="health-row">
      <div class="health-row__info">
        <span class="health-row__name">${esc(c.name)}</span>
        <span class="health-row__detail">${esc(c.detail)}</span>
      </div>
      <span class="health-badge health-badge--${esc(c.status)}">
        ${esc(STATUS_LABEL[c.status] ?? c.status)}
      </span>
    </div>
  `
        )
        .join('');
}

// ── Check for story updates ───────────────────────────────────────────────────

window.checkUpdates = async function checkUpdates() {
    try {
        const res = await fetch('/admin/check-updates', { method: 'POST' });
        const d = await res.json();
        const el = document.getElementById('pending-syncs');
        if (el) {
            el.textContent = d.stories_with_updates ?? 0;
            el.title = `${d.pending_chapters ?? 0} new chapters available`;
        }
        alert(d.message || 'Up to date');
    } catch (err) {
        console.error('Check updates failed:', err);
    }
};

// ── Sync all stories ──────────────────────────────────────────────────────────

window.syncStory = async function syncStory() {
    try {
        await fetch('/api/sync/update/all', { method: 'POST' });
    } catch (err) {
        console.error('Sync failed:', err);
    }
};

// ── Utility ───────────────────────────────────────────────────────────────────

function esc(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

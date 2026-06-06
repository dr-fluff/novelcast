window.runHealthCheck = function runHealthCheck() {
  fetch('/admin/health-check', { method: 'POST' }).then(() => window.location.reload());
}

window.checkUpdates = function checkUpdates() {
  fetch('/admin/check', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('pending-syncs');
      if (el) {
        el.textContent = d.stories_with_updates || 0;
        el.title = `${d.pending_chapters || 0} new chapters available`;
      }
      alert(d.message || 'Up to date');
    });
}

window.syncStory = function syncStory() {
    fetch('/api/update/all', { method: 'POST' })


}
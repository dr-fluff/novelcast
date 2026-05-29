window.getStoryPageData = function () {
    const section = document.querySelector(".story-page");
    if (!section) return null;

    return {
        storyId: section.dataset.storyId ? Number(section.dataset.storyId) : null,
        firstUnreadChapterId: section.dataset.firstUnreadId ? Number(section.dataset.firstUnreadId) : null,
    };
};

window.goToFirstUnread = function () {
    const data = window.getStoryPageData();
    if (!data || !data.firstUnreadChapterId) return;

    window.location.href = `/chapter?story_id=${data.storyId}&chapter_id=${data.firstUnreadChapterId}`;
};

window.confirmDeleteStory = async function () {
    const data = window.getStoryPageData();
    if (!data || !data.storyId) return;

    if (!confirm("Delete this story and all downloaded files?")) {
        return;
    }

    try {
        const res = await fetch(`/api/stories/${data.storyId}`, {
            method: "DELETE",
        });

        const responseBody = await res.json();
        if (!res.ok) {
            throw new Error(responseBody.detail || responseBody.error || res.statusText);
        }

        if (typeof window.showNotification === "function") {
            window.showNotification("Story deleted successfully.", "success", 5000);
        }

        window.location.replace("/");
    } catch (error) {
        console.error(error);
        if (typeof window.showNotification === "function") {
            window.showNotification(`Delete failed: ${error.message}`, "error", 8000);
        }
    }
};

window.toggleSection = function (section) {
    const body = document.getElementById(`${section}Body`);
    const chevron = document.getElementById(`${section}Chevron`);
    if (!body) return;

    body.classList.toggle("collapsed");
    if (chevron) {
        chevron.classList.toggle("collapsed");
    }
};

window.toggleDescription = function () {
    const desc = document.getElementById("storyDescription");
    const btn = document.getElementById("readMoreBtn");
    if (!desc || !btn) return;

    const expanded = desc.classList.toggle("expanded");
    btn.innerHTML = expanded
        ? 'Show less <i class="fa-solid fa-chevron-up"></i>'
        : 'Read more <i class="fa-solid fa-chevron-down"></i>';
};

window.buildMetaFilterLink = function (label, value) {
    if (!label || value === undefined || value === null) return null;
    const normalizedLabel = label.trim();
    if (!normalizedLabel) return null;
    if (normalizedLabel === "Duration" || normalizedLabel === "Size" || normalizedLabel === "Source") {
        return null;
    }

    const link = document.createElement("a");
    link.className = "meta-link";
    link.href = "/?q=" + encodeURIComponent(`${normalizedLabel},${value}`);
    link.textContent = value;
    return link;
};

window.enhanceStoryMetaGridLinks = function () {
    document.querySelectorAll(".story-meta-grid .meta-row").forEach(row => {
        const dt = row.querySelector("dt");
        const dd = row.querySelector("dd");
        if (!dt || !dd) return;
        if (dd.querySelector("a")) return;

        const label = dt.textContent.trim();
        const value = dd.textContent.trim();
        if (!value) return;
        if (["Duration", "Size", "Source"].includes(label)) return;

        const items = String(value).split(/,\s*/).map(item => item.trim()).filter(Boolean);
        dd.textContent = "";
        items.forEach((item, index) => {
            const link = window.buildMetaFilterLink(label, item);
            if (!link) return;
            if (index) dd.appendChild(document.createTextNode(", "));
            dd.appendChild(link);
        });
    });
};

document.addEventListener("DOMContentLoaded", () => {
    window.enhanceStoryMetaGridLinks();
});

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

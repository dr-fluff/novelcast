window.addStory = async function (event) {
    event.preventDefault();

    const input = document.getElementById("story-url");
    const url = input.value.trim();

    if (!url) return;

    setStatus("adding");

    try {
        const res = await fetch("/api/download/story", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url })
        });

        if (!res.ok) {
            const err = await res.text();
            console.error("Download failed:", err);
            setStatus("error");
            if (typeof showNotification === "function") {
                showNotification(`Download failed: ${err}`, "error", 8000);
            }
            return;
        }

        const data = await res.json();
        console.log("Story added:", data);

        if (data.status !== "ok") {
            setStatus("error");
            if (typeof showNotification === "function") {
                showNotification(`Download failed: ${data.error || "Unexpected response"}`, "error", 8000);
            }
            return;
        }

        input.value = "";
        setStatus("done");
        if (typeof showNotification === "function") {
            showNotification("Story download started. Notifications will appear shortly.", "success", 5000);
        }

    } catch (err) {
        console.error(err);
        setStatus("error");
    }
};

window.setStatus = function (state) {
    const dot = document.getElementById("sync-status");
    if (!dot) return;

    switch (state) {
        case "adding":
            dot.style.background = "orange";
            dot.title = "Downloading...";
            break;
        case "done":
            dot.style.background = "green";
            dot.title = "Done";
            break;
        case "error":
            dot.style.background = "red";
            dot.title = "Error";
            break;
        default:
            dot.style.background = "gray";
            dot.title = "Idle";
    }
};

window.toggleUserMenu = function () {
    console.log("User menu toggle");
};

window.startSync = async function () {
    try {
        const res = await fetch("/api/sync/all", {
            method: "POST",
        });

        const data = await res.json();
        console.log("Sync started:", data);

        window.showSyncStatus("Sync running...");
    } catch (error) {
        console.error("Sync failed:", error);
        window.showSyncStatus("Sync failed");
    }
};

window.showSyncStatus = function (status) {
    const dot = document.getElementById("sync-status");
    if (!dot) return;

    dot.style.background = status === "Sync failed" ? "red" : "orange";
    dot.title = status;
};


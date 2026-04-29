/* novelcast/static/js/notifications.js */

const activeNotifications = new Map();

function ensureNotificationContainer() {
    let container = document.getElementById("notification-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "notification-container";
        container.className = "notification-container";
        document.body.appendChild(container);
    }
    return container;
}

function createNotificationContent(message) {
    return `
        <div class="notification-body">
            <div class="notification-content">${message}</div>
        </div>
        <div class="notification-close">✕</div>
    `;
}

function setNotificationProgress(notification, progress, indeterminate = false) {
    let progressWrapper = notification.querySelector(".notification-progress");
    if (!progressWrapper) {
        const wrapper = document.createElement("div");
        wrapper.className = "notification-progress";

        const bar = document.createElement("div");
        bar.className = "notification-progress-bar";
        wrapper.appendChild(bar);

        const body = notification.querySelector(".notification-body");
        body.appendChild(wrapper);
        progressWrapper = wrapper;
    }

    const bar = progressWrapper.querySelector(".notification-progress-bar");
    if (indeterminate) {
        bar.classList.add("indeterminate");
        bar.style.width = "50%";
    } else {
        bar.classList.remove("indeterminate");
        bar.style.width = `${Math.min(Math.max(progress, 0), 100)}%`;
    }
}

function removeNotification(notification, id) {
    if (!notification) return;
    notification.remove();
    if (id) {
        activeNotifications.delete(id);
    }
}

function showNotification(message, type = "info", timeout = 7000, options = {}) {
    const container = ensureNotificationContainer();
    const id = options.id;
    let notif = id ? activeNotifications.get(id) : null;

    if (notif) {
        notif.className = `notification ${type}`;
        notif.querySelector(".notification-content").textContent = message;

        if (options.progress != null || options.indeterminate) {
            setNotificationProgress(notif, options.progress ?? 0, !!options.indeterminate);
        }

        if (options.persistent) {
            const closeButton = notif.querySelector(".notification-close");
            if (closeButton) closeButton.style.display = "none";
        }

        if (notif.dismissTimeout) {
            clearTimeout(notif.dismissTimeout);
            notif.dismissTimeout = null;
        }

        if (timeout > 0) {
            notif.dismissTimeout = setTimeout(() => removeNotification(notif, id), timeout);
        }

        return notif;
    }

    notif = document.createElement("div");
    notif.className = `notification ${type}`;
    notif.innerHTML = createNotificationContent(message);

    const closeButton = notif.querySelector(".notification-close");
    closeButton.onclick = () => removeNotification(notif, id);
    if (options.persistent) {
        closeButton.style.display = "none";
    }

    container.appendChild(notif);
    if (id) {
        activeNotifications.set(id, notif);
    }

    if (options.progress != null || options.indeterminate) {
        setNotificationProgress(notif, options.progress ?? 0, !!options.indeterminate);
    }

    if (timeout > 0) {
        notif.dismissTimeout = setTimeout(() => removeNotification(notif, id), timeout);
    }

    return notif;
}

function buildNotification(payload) {
    switch (payload.type) {
        case "download_started":
            return {
                message: `Downloading ${payload.source_url}...`,
                type: "info",
                timeout: 0,
                options: {
                    id: `download-${payload.download_id}`,
                    persistent: true,
                    indeterminate: true,
                },
            };
        case "download_finished":
            return {
                message: `Download complete: ${payload.title || payload.story_id}.`,
                type: "success",
                timeout: 5000,
                options: {
                    id: `download-${payload.download_id}`,
                    progress: 100,
                },
            };
        case "download_failed":
            return {
                message: `Download failed: ${payload.error || "Unknown error"}`,
                type: "error",
                timeout: 8000,
                options: {
                    id: `download-${payload.download_id}`,
                },
            };
        case "sync_started":
            return {
                message: `Sync started for “${payload.title || payload.story_id}”.`,
                type: "info",
                timeout: 7000,
            };
        case "sync_no_changes":
            return {
                message: `No updates found for story ${payload.story_id}.`,
                type: "info",
                timeout: 7000,
            };
        case "sync_progress":
            return {
                message: `${payload.new_chapters} new chapter${payload.new_chapters === 1 ? "" : "s"} downloaded.`,
                type: "info",
                timeout: 7000,
            };
        case "sync_finished":
            return {
                message: `Sync finished: ${payload.new_chapters} new chapter${payload.new_chapters === 1 ? "" : "s"}.`,
                type: "success",
                timeout: 7000,
            };
        case "story_added":
            return {
                message: `Story added: ${payload.title || payload.story_id}.`,
                type: "success",
                timeout: 7000,
            };
        default:
            return {
                message: JSON.stringify(payload),
                type: "info",
                timeout: 7000,
            };
    }
}

function getWebSocketHost() {
    const hostname = window.location.hostname;
    const port = window.location.port;

    // In browser-sync development mode, the page may be served on port 3000
    // while the FastAPI backend is still on 8001.
    if ((hostname === "localhost" || hostname === "127.0.0.1") && port === "3000") {
        return `${hostname}:8001`;
    }

    return window.location.host;
}

function createWebSocketUrl() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${getWebSocketHost()}/ws/notifications`;
}

function initNotificationSocket() {
    if (!window.WebSocket) {
        showNotification("WebSockets are not supported by this browser.", "warning");
        return;
    }

    const url = createWebSocketUrl();
    const socket = new WebSocket(url);

    /*
    socket.addEventListener("open", () => {
        showNotification("Notifications connected.", "success", 2000);
    });
    */
    socket.addEventListener("message", (event) => {
        try {
            const payload = JSON.parse(event.data);
            const notification = buildNotification(payload);
            showNotification(notification.message, notification.type, notification.timeout, notification.options);
        } catch (error) {
            showNotification("Received invalid notification payload.", "warning");
            console.error("Notification parse error:", error, event.data);
        }
    });

    socket.addEventListener("close", () => {
        showNotification("Notification connection closed. Reconnecting...", "warning", 3000);
        setTimeout(initNotificationSocket, 2000);
    });

    socket.addEventListener("error", () => {
        showNotification("Notification connection error.", "error", 3000);
    });
}

window.addEventListener("DOMContentLoaded", initNotificationSocket);
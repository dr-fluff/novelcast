/* ── File row menu & More Info modal ─────────────────────────────────── */

let _activeDropdown = null;

function closeActiveDropdown() {
    if (_activeDropdown) {
        _activeDropdown.remove();
        _activeDropdown = null;
    }
}

document.addEventListener("click", (e) => {
    if (!e.target.closest(".file-menu-wrapper")) {
        closeActiveDropdown();
    }
});

window.openFileMenu = function (btn, filePath, fileType) {
    closeActiveDropdown();

    const wrapper = btn.closest(".file-menu-wrapper");
    const dropdown = document.createElement("div");
    dropdown.className = "file-dropdown";
    dropdown.innerHTML = `
        <button class="file-dropdown-item" onclick="downloadFile(${JSON.stringify(filePath)})">Download</button>
        <button class="file-dropdown-item danger" onclick="deleteFile(${JSON.stringify(filePath)})">Delete</button>
        <button class="file-dropdown-item" onclick="openFileInfo(${JSON.stringify(filePath)}, ${JSON.stringify(fileType)})">More Info</button>
    `;
    wrapper.appendChild(dropdown);
    _activeDropdown = dropdown;
};

window.downloadFile = function (filePath) {
    closeActiveDropdown();
    // Adjust endpoint to match your API
    window.open(`/api/files/download?path=${encodeURIComponent(filePath)}`, "_blank");
};

window.deleteFile = async function (filePath) {
    closeActiveDropdown();
    if (!confirm(`Delete file: ${filePath}?`)) return;
    try {
        const res = await fetch(`/api/files/delete`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: filePath }),
        });
        if (!res.ok) throw new Error(await res.text());
        // Remove row from table
        document.querySelectorAll(".file-path-text").forEach(el => {
            if (el.dataset.full === filePath || el.dataset.relative === filePath) {
                el.closest(".file-row").remove();
            }
        });
        if (typeof window.showNotification === "function") {
            window.showNotification("File deleted.", "success", 4000);
        }
    } catch (err) {
        if (typeof window.showNotification === "function") {
            window.showNotification(`Delete failed: ${err.message}`, "error", 6000);
        }
    }
};

window.openFileInfo = async function (filePath, fileType) {
    closeActiveDropdown();

    const overlay = document.getElementById("fileInfoOverlay");
    const title   = document.getElementById("fileInfoTitle");
    const body    = document.getElementById("fileInfoBody");
    const probe   = document.getElementById("fileInfoProbeBtn");

    title.textContent = filePath.split("/").pop();
    body.innerHTML = `<div class="file-info-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading…</div>`;

    const isAudio = ["audio", "m4b", "mp3", "aac", "flac", "ogg"].includes((fileType || "").toLowerCase());
    probe.style.display = isAudio ? "" : "none";
    probe.onclick = () => probeAudioFile(filePath);

    overlay.classList.add("open");

    try {
        const res = await fetch(`/api/files/info?path=${encodeURIComponent(filePath)}`);
        if (!res.ok) throw new Error(await res.text());
        const info = await res.json();
        renderFileInfo(body, filePath, info);
    } catch (err) {
        body.innerHTML = `
            <p class="file-info-section-title">Path</p>
            <div class="file-info-path-box">${filePath}</div>
            <p style="color:#f87171;font-size:0.88rem;margin-top:1rem;">
                Could not load file details: ${err.message}
            </p>`;
    }
};

function renderFileInfo(body, filePath, info) {
    // info shape: { size, duration, format, codec, channels, bitrate, chapters, time_base,
    //               embedded_cover, language, meta_tags: { Album, Artist, ... } }
    const details = [
        ["Size",           info.size],
        ["Duration",       info.duration],
        ["Format",         info.format],
        ["Codec",          info.codec],
        ["Channels",       info.channels],
        ["Bitrate",        info.bitrate],
        ["Chapters",       info.chapters],
        ["Time Base",      info.time_base],
        ["Embedded Cover", info.embedded_cover],
        ["Language",       info.language],
    ].filter(([, v]) => v !== undefined && v !== null && v !== "");

    const leftDetails  = details.filter((_, i) => i % 2 === 0);
    const rightDetails = details.filter((_, i) => i % 2 === 1);
    const maxRows = Math.max(leftDetails.length, rightDetails.length);

    let detailRows = "";
    for (let i = 0; i < maxRows; i++) {
        const l = leftDetails[i]  || null;
        const r = rightDetails[i] || null;
        detailRows += `<div class="file-info-row">
            ${l ? `<dt>${l[0]}</dt><dd>${l[1]}</dd>` : "<dt></dt><dd></dd>"}
        </div>
        <div class="file-info-row">
            ${r ? `<dt>${r[0]}</dt><dd>${r[1]}</dd>` : "<dt></dt><dd></dd>"}
        </div>`;
    }

    let metaTagsHtml = "";
    if (info.meta_tags && Object.keys(info.meta_tags).length) {
        const rows = Object.entries(info.meta_tags).map(([k, v]) => {
            if (k === "Comment" || (typeof v === "string" && v.length > 60)) {
                return `<dt>${k}</dt><dd class="file-info-comment">${v}</dd>`;
            }
            return `<dt>${k}</dt><dd>${v}</dd>`;
        }).join("");
        metaTagsHtml = `
            <hr class="file-info-divider" />
            <div>
                <p class="file-info-section-title">Meta Tags</p>
                <dl class="file-info-tags-grid">${rows}</dl>
            </div>`;
    }

    body.innerHTML = `
        <div>
            <p class="file-info-section-title">Path</p>
            <div class="file-info-path-box">${filePath}</div>
        </div>
        ${details.length ? `<dl class="file-info-grid">${detailRows}</dl>` : ""}
        ${metaTagsHtml}
    `;
}

window.closeFileInfo = function (e) {
    if (e.target === document.getElementById("fileInfoOverlay")) {
        closeFileInfoModal();
    }
};

window.closeFileInfoModal = function () {
    document.getElementById("fileInfoOverlay").classList.remove("open");
};

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeFileInfoModal();
});

window.probeAudioFile = async function (filePath) {
    if (typeof window.showNotification === "function") {
        window.showNotification("Probing audio file…", "info", 3000);
    }
    try {
        const res = await fetch(`/api/files/probe`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: filePath }),
        });
        if (!res.ok) throw new Error(await res.text());
        const info = await res.json();
        const body = document.getElementById("fileInfoBody");
        renderFileInfo(body, filePath, info);
    } catch (err) {
        if (typeof window.showNotification === "function") {
            window.showNotification(`Probe failed: ${err.message}`, "error", 6000);
        }
    }
};
window.addStory = async function (event) {
    event.preventDefault();

    const input = document.getElementById("story-url");
    const url = input.value.trim();

    if (!url) return;

    setStatus("adding");

    try {
        const res = await fetch("/download/story", {
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
            return;
        }

        const data = await res.json();
        console.log("Story added:", data);

        input.value = "";
        setStatus("done");

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


let socket;

let autoScroll = true;


function connectLogs() {

    const protocol =
        window.location.protocol === "https:"
            ? "wss:"
            : "ws:";


    socket = new WebSocket(
        `${protocol}//${window.location.host}/api/admin/logs/tail`
    );


    socket.onmessage = function(event) {

        const data =
            JSON.parse(event.data);


        if (
            data.type === "backlog" ||
            data.type === "lines"
        ) {

            appendLogs(data.lines);

        }

    };


    socket.onclose = function() {

        setTimeout(
            connectLogs,
            3000
        );

    };

}



function appendLogs(lines) {

    const viewer =
        document.getElementById(
            "log-viewer"
        );


    for (const line of lines) {

        let log;


        try {

            log =
                typeof line === "string"
                    ? JSON.parse(line)
                    : line;

        }
        catch {

            log = {

                level:"INFO",

                message:String(line)

            };

        }


        const row =
            document.createElement("div");


        row.className =
            `log-entry log-${(
                log.level || "info"
            ).toLowerCase()}`;


        row.innerHTML = `

            <div>

                <span class="log-time">
                    ${formatTime(log.timestamp)}
                </span>


                <span class="log-level">
                    ${escapeHtml(log.level || "")}
                </span>


                <span class="log-message">
                    ${escapeHtml(log.message || "")}
                </span>


            </div>


            <details class="log-details">

                <summary>
                    details
                </summary>


                <pre>
${escapeHtml(
    JSON.stringify(log,null,2)
)}
                </pre>

            </details>

        `;


        viewer.appendChild(row);

    }


    if (autoScroll) {

        viewer.scrollTop =
            viewer.scrollHeight;

    }

}



function formatTime(value) {

    if (!value)
        return "";


    return new Date(value)
        .toLocaleTimeString();

}



function escapeHtml(value) {

    return String(value)

        .replaceAll("&","&amp;")

        .replaceAll("<","&lt;")

        .replaceAll(">","&gt;");

}



function clearLogs() {

    document
        .getElementById("log-viewer")
        .innerHTML = "";

}



function resumeLive() {

    autoScroll = true;


    const viewer =
        document.getElementById(
            "log-viewer"
        );


    viewer.scrollTop =
        viewer.scrollHeight;


    document
        .getElementById(
            "resume-live"
        )
        .style.display="none";

}



document.addEventListener(
    "DOMContentLoaded",
    () => {

        const viewer =
            document.getElementById(
                "log-viewer"
            );


        viewer.addEventListener(
            "scroll",
            () => {

                autoScroll =
                    viewer.scrollTop +
                    viewer.clientHeight >=
                    viewer.scrollHeight - 20;


                document
                    .getElementById(
                        "resume-live"
                    )
                    .style.display =
                    autoScroll
                    ? "none"
                    : "inline-block";

            }
        );


        viewer.addEventListener(
            "click",
            (event)=>{

                if (
                    event.target.closest(
                        "summary"
                    )
                ) {

                    autoScroll=false;

                }

            }
        );


        connectLogs();

    }
);
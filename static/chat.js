$(document).ready(function() {
    let session_id = getCookie("session_id"); // current session
    let nameSetMap = {}; // tracks which sessions have custom names

    // ------------------- Initialize -------------------
    async function initSession() {
        if (!session_id) {
            const res = await fetch('/sessions');
            const data = await res.json();
            if (data.sessions.length > 0) {
                session_id = data.sessions[0].id;
            } else {
                const resNew = await fetch('/new_chat', { method: 'POST' });
                const dataNew = await resNew.json();
                session_id = dataNew.session_id;
            }
            setCookie("session_id", session_id, 30);
        }

        await loadSessions();
        await loadHistory(session_id);
    }

    // ------------------- Load Sessions -------------------
    async function loadSessions() {
        const res = await fetch('/sessions');
        const data = await res.json();
        const list = $("#session-list");
        list.empty();

        data.sessions.forEach(s => {
            const li = $(`
                <li class="list-group-item d-flex justify-content-between align-items-center list-group-item-action" data-session="${s.id}">
                    <span class="session-name" style="cursor:pointer;">${s.name || "New Chat"}</span>
                    <div>
                        <button class="btn btn-sm btn-primary rename-btn" style="margin-right:5px;">✎</button>
                        <button class="btn btn-sm btn-danger delete-btn">X</button>
                    </div>
                </li>
            `);

            // Click session to load
            li.find(".session-name").on("click", async function() {
                session_id = s.id;
                $("#messageFormeight").empty();
                setCookie("session_id", session_id, 30);
                await loadHistory(session_id);
            });

            // ------------------- Rename -------------------
            li.find(".rename-btn").on("click", function(e) {
                e.stopPropagation();
                const liEl = $(this).closest("li");
                const sessionId = liEl.data("session");
                const sessionNameSpan = liEl.find(".session-name");

                const input = $(`<input type="text" class="form-control form-control-sm" value="${sessionNameSpan.text()}">`);
                sessionNameSpan.replaceWith(input);
                input.focus();

                const saveName = async () => {
                    const newName = input.val().trim() || "New Chat";
                    await $.ajax({
                        type: "POST",
                        url: `/rename_chat/${sessionId}`,
                        data: { name: newName }
                    });
                    input.replaceWith(`<span class="session-name" style="cursor:pointer;">${newName}</span>`);
                    nameSetMap[sessionId] = true;

                    // Reattach click handler
                    liEl.find(".session-name").on("click", async function() {
                        session_id = sessionId;
                        $("#messageFormeight").empty();
                        await loadHistory(session_id);
                    });
                };

                input.on("keypress", function(e) { if (e.which === 13) saveName(); });
                input.on("blur", saveName);
            });

            // ------------------- Delete -------------------
            let chatToDelete = null;
            li.find(".delete-btn").on("click", function(e) {
                e.stopPropagation();
                chatToDelete = s.id;
                $("#deleteModal").fadeIn(200);
            });

            $("#cancelDelete").on("click", function() {
                chatToDelete = null;
                $("#deleteModal").fadeOut(200);
            });

            $("#confirmDelete").on("click", async function() {
                if (!chatToDelete) return;
                await fetch(`/delete_chat/${chatToDelete}`, { method: 'DELETE' });

                if (chatToDelete === session_id) {
                    session_id = null;
                    $("#messageFormeight").empty();
                    deleteCookie("session_id");
                }

                chatToDelete = null;
                $("#deleteModal").fadeOut(200);
                await loadSessions();

                const res2 = await fetch('/sessions');
                const data2 = await res2.json();
                if (data2.sessions.length === 0) {
                    const resNew = await fetch('/new_chat', { method: 'POST' });
                    const dataNew = await resNew.json();
                    session_id = dataNew.session_id;
                    setCookie("session_id", session_id, 30);
                    await loadSessions();
                } else if (!session_id) {
                    session_id = data2.sessions[0].id;
                    setCookie("session_id", session_id, 30);
                    await loadHistory(session_id);
                }
            });

            list.append(li);
        });
    }

    // ------------------- Load History -------------------
    async function loadHistory(sid) {
        const res = await fetch(`/history/${sid}`);
        const messages = await res.json();
        const chatBox = $("#messageFormeight");
        chatBox.empty();

        messages.forEach(msg => {
            const date = new Date();
            const str_time = date.getHours() + ":" + date.getMinutes();
            if (msg.type === "human") {
                chatBox.append(`
                    <div class="d-flex justify-content-end mb-4">
                        <div class="msg_cotainer_send">${msg.content}<span class="msg_time_send">${str_time}</span></div>
                        <div class="img_cont_msg"><img src="https://i.ibb.co/d5b84Xw/Untitled-design.png" class="rounded-circle user_img_msg"></div>
                    </div>
                `);
            } else if (msg.type === "ai") {
                chatBox.append(`
                    <div class="d-flex justify-content-start mb-4">
                        <div class="img_cont_msg"><img src="https://cdn-icons-png.flaticon.com/512/387/387569.png" class="rounded-circle user_img_msg"></div>
                        <div class="msg_cotainer">${msg.content}<span class="msg_time">${str_time}</span></div>
                    </div>
                `);
            }
        });

        chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    // ------------------- Send Message -------------------
    $("#messageArea").on("submit", async function(event) {
        event.preventDefault();
        const rawText = $("#text").val().trim();
        if (!rawText) return;
        $("#text").val("");

        const date = new Date();
        const str_time = date.getHours() + ":" + date.getMinutes();

        $("#messageFormeight").append(`
            <div class="d-flex justify-content-end mb-4">
                <div class="msg_cotainer_send">${rawText}<span class="msg_time_send">${str_time}</span></div>
                <div class="img_cont_msg"><img src="https://i.ibb.co/d5b84Xw/Untitled-design.png" class="rounded-circle user_img_msg"></div>
            </div>
        `);

        const thinkingDiv = $(`
            <div id="thinking" class="d-flex justify-content-start mb-4">
                <div class="img_cont_msg">
                    <img src="https://cdn-icons-png.flaticon.com/512/387/387569.png" class="rounded-circle user_img_msg">
                </div>
                <div class="thinking-bubble">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
            </div>
        `);
        $("#messageFormeight").append(thinkingDiv);
        $("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);

        try {
            const res = await $.ajax({ type: "POST", url: `/get`, data: { msg: rawText } });
            $("#thinking").remove();

            const aiMessage = $(`
                <div class="d-flex justify-content-start mb-4">
                    <div class="img_cont_msg"><img src="https://cdn-icons-png.flaticon.com/512/387/387569.png" class="rounded-circle user_img_msg"></div>
                    <div class="msg_cotainer"><span class="typed-text"></span><span class="msg_time">${str_time}</span></div>
                </div>
            `);
            $("#messageFormeight").append(aiMessage);

            let index = 0;
            const container = aiMessage.find(".typed-text");
            function typeChar() {
                if (index < res.length) {
                    container.append(res[index]);
                    index++;
                    $("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);
                    setTimeout(typeChar, 15);
                }
            }
            typeChar();

            // ------------------- First message auto-rename -------------------
            if (!nameSetMap[session_id]) {
                const newName = rawText.substring(0, 50);
                await $.ajax({ type: "POST", url: `/rename_chat/${session_id}`, data: { name: newName } });
                nameSetMap[session_id] = true;
                await loadSessions();
            }

        } catch (error) {
            $("#thinking").remove();
            $("#messageFormeight").append(`
                <div class="d-flex justify-content-start mb-4">
                    <div class="msg_cotainer" style="background-color:#f44336; color:white;">Error: Could not get a response.</div>
                </div>
            `);
        }

        $("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);
    });

    // ------------------- New Chat -------------------
    $("#new-chat-btn").on("click", async function() {
        const res = await fetch('/new_chat', { method: 'POST' });
        const data = await res.json();
        session_id = data.session_id;
        setCookie("session_id", session_id, 30);
        $("#messageFormeight").empty();
        nameSetMap[session_id] = false;
        await loadSessions();
    });

    // ------------------- Cookie Helpers -------------------
    function setCookie(name, value, days) {
        const d = new Date();
        d.setTime(d.getTime() + (days*24*60*60*1000));
        document.cookie = name + "=" + value + ";path=/;expires=" + d.toUTCString();
    }

    function getCookie(name) {
        const value = "; " + document.cookie;
        const parts = value.split("; " + name + "=");
        if (parts.length === 2) return parts.pop().split(";").shift();
        return null;
    }

    function deleteCookie(name) {
        document.cookie = name +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    }

    initSession();
});

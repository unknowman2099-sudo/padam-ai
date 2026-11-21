
import os
import sqlite3
import uuid
import requests

from flask import (
    Flask, request, jsonify, render_template_string, session
)

# ---------------- CONFIG ----------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY", "change-this-secret-before-deployment"
)

DB_NAME = "padam_ai.db"

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = os.environ.get(
    "HF_MODEL", "Qwen/Qwen2.5-7B-Instruct"
)

HF_URL = "https://router.huggingface.co/v1/chat/completions"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_chat_id():
    if "chat_id" not in session:
        session["chat_id"] = str(uuid.uuid4())
    return session["chat_id"]


def save_message(chat_id, role, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content)
    )
    conn.commit()
    conn.close()


def get_history(chat_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM messages "
        "WHERE chat_id = ? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------- AI ENGINE ----------------

def ask_ai(history):
    if not HF_TOKEN:
        return (
            "PADAM AI तयार छ! तर वास्तविक AI जवाफका लागि "
            "Render मा HF_TOKEN सेट गर्नुपर्छ।"
        )

    messages = [
        {
            "role": "system",
            "content": (
                "Your name is PADAM AI. "
                "You are a helpful, friendly AI assistant. "
                "You can communicate in Nepali and English. "
                "Give clear, accurate and useful answers. "
                "If you are uncertain, say so honestly."
            )
        }
    ]

    messages.extend(history[-20:])

    try:
        response = requests.post(
            HF_URL,
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": HF_MODEL,
                "messages": messages,
                "max_tokens": 700,
                "temperature": 0.7
            },
            timeout=90
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:
        return "माफ गर्नुहोस्, AI ले जवाफ दिन ढिलो गर्‍यो। फेरि प्रयास गर्नुहोस्।"

    except requests.exceptions.RequestException:
        return "AI सेवा अहिले उपलब्ध छैन। Token र Model जाँच गर्नुहोस्।"

    except (KeyError, IndexError, ValueError):
        return "AI बाट सही जवाफ प्राप्त भएन। फेरि प्रयास गर्नुहोस्।"


# ---------------- WEBSITE DESIGN ----------------

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PADAM AI</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0b1020;
    color: white;
    font-family: Arial, sans-serif;
    height: 100vh;
    overflow: hidden;
}

.app {
    display: flex;
    height: 100vh;
}

.sidebar {
    width: 255px;
    background: #11182a;
    padding: 20px;
    display: flex;
    flex-direction: column;
    border-right: 1px solid #263149;
}

.logo {
    font-size: 25px;
    font-weight: bold;
    color: #8b9cff;
    margin-bottom: 25px;
}

.new-chat {
    background: #293653;
    color: white;
    border: 1px solid #405078;
    padding: 13px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 15px;
}

.new-chat:hover {
    background: #394b73;
}

.sidebar-info {
    margin-top: auto;
    color: #8490a8;
    font-size: 12px;
    line-height: 1.6;
}

.main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.topbar {
    height: 65px;
    display: flex;
    align-items: center;
    padding: 0 22px;
    border-bottom: 1px solid #263149;
    font-weight: bold;
}

.status {
    margin-left: auto;
    font-size: 12px;
    color: #65dca1;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 25px 16px;
}

.welcome {
    text-align: center;
    margin: 12vh auto 30px;
    max-width: 500px;
}

.welcome h1 {
    font-size: 38px;
    color: #9eafff;
    margin-bottom: 10px;
}

.welcome p {
    color: #aab4c8;
    line-height: 1.6;
}

.message {
    max-width: 760px;
    margin: 15px auto;
    padding: 16px;
    border-radius: 13px;
    line-height: 1.65;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.user {
    background: #26385b;
}

.bot {
    background: #151f34;
    border: 1px solid #263149;
}

.label {
    display: block;
    font-size: 12px;
    color: #9eafff;
    font-weight: bold;
    margin-bottom: 8px;
}

.composer {
    width: min(800px, 95%);
    margin: 0 auto 22px;
    display: flex;
    gap: 10px;
    padding: 10px;
    background: #151f34;
    border: 1px solid #34425f;
    border-radius: 15px;
}

textarea {
    flex: 1;
    resize: none;
    border: none;
    outline: none;
    background: transparent;
    color: white;
    font-size: 15px;
    padding: 10px;
    min-height: 45px;
    max-height: 130px;
}

textarea::placeholder {
    color: #8995ac;
}

.send {
    background: #657af5;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0 19px;
    cursor: pointer;
    font-weight: bold;
}

.send:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.footer {
    text-align: center;
    color: #7d8aa4;
    font-size: 11px;
    padding-bottom: 12px;
}

@media(max-width:650px) {
    .sidebar {
        display: none;
    }

    .welcome h1 {
        font-size: 30px;
    }

    .messages {
        padding: 12px 8px;
    }

    .message {
        padding: 13px;
    }
}
</style>
</head>

<body>
<div class="app">

    <aside class="sidebar">
        <div class="logo">✦ PADAM AI</div>
        <button class="new-chat" onclick="newChat()">
            + New Chat
        </button>

        <div class="sidebar-info">
            Your AI. Your Code. Your Control.<br><br>
            Powered by an open-source model.
        </div>
    </aside>

    <main class="main">

        <header class="topbar">
            ✦ PADAM AI
            <span class="status">● Assistant</span>
        </header>

        <section class="messages" id="messages">

            <div class="welcome" id="welcome">
                <h1>Hello, I'm PADAM AI.</h1>
                <p>
                    Welcome! I'm your personal AI assistant.
                    Ask me anything in Nepali or English.
                </p>
            </div>

        </section>

        <form class="composer" id="chatForm">
            <textarea
                id="prompt"
                placeholder="Message PADAM AI..."
                rows="1"
                required
            ></textarea>

            <button class="send" id="send" type="submit">
                Send ↑
            </button>
        </form>

        <div class="footer">
            PADAM AI can make mistakes. Verify important information.
        </div>

    </main>
</div>

<script>
const messages = document.getElementById("messages");
const promptBox = document.getElementById("prompt");
const sendButton = document.getElementById("send");
const form = document.getElementById("chatForm");

function addMessage(role, content) {
    const welcome = document.getElementById("welcome");
    if (welcome) welcome.remove();

    const box = document.createElement("div");
    box.className = "message " + role;

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = role === "user" ? "YOU" : "PADAM AI";

    const text = document.createElement("div");
    text.textContent = content;

    box.appendChild(label);
    box.appendChild(text);
    messages.appendChild(box);

    messages.scrollTop = messages.scrollHeight;
}

async function loadHistory() {
    try {
        const response = await fetch("/history");
        const data = await response.json();

        if (data.messages && data.messages.length) {
            document.getElementById("welcome")?.remove();

            data.messages.forEach(item => {
                addMessage(
                    item.role === "user" ? "user" : "bot",
                    item.content
                );
            });
        }
    } catch (error) {
        console.error(error);
    }
}

form.addEventListener("submit", async function(event) {
    event.preventDefault();

    const message = promptBox.value.trim();
    if (!message) return;

    addMessage("user", message);
    promptBox.value = "";
    sendButton.disabled = true;
    sendButton.textContent = "...";

    const typing = document.createElement("div");
    typing.className = "message bot";
    typing.textContent = "PADAM AI is thinking...";
    typing.id = "typing";
    messages.appendChild(typing);

    messages.scrollTop = messages.scrollHeight;

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({message: message})
        });

        const data = await response.json();
        document.getElementById("typing")?.remove();

        if (!response.ok) {
            addMessage("bot", data.error || "Something went wrong.");
        } else {
            addMessage("bot", data.reply);
        }

    } catch (error) {
        document.getElementById("typing")?.remove();
        addMessage("bot", "Connection error. Please try again.");
    }

    sendButton.disabled = false;
    sendButton.textContent = "Send ↑";
    promptBox.focus();
});

async function newChat() {
    await fetch("/new-chat", {method: "POST"});
    messages.innerHTML = `
        <div class="welcome" id="welcome">
            <h1>Hello, I'm PADAM AI.</h1>
            <p>Welcome! Ask me anything in Nepali or English.</p>
        </div>
    `;
}

promptBox.addEventListener("keydown", function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});

loadHistory();
</script>

</body>
</html>
"""


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    get_chat_id()
    return render_template_string(HTML)


@app.route("/history")
def history():
    chat_id = get_chat_id()
    return jsonify(messages=get_history(chat_id))


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify(error="Message cannot be empty."), 400

    if len(message) > 5000:
        return jsonify(error="Message is too long."), 400

    chat_id = get_chat_id()

    save_message(chat_id, "user", message)

    history = get_history(chat_id)
    reply = ask_ai(history)

    save_message(chat_id, "assistant", reply)

    return jsonify(reply=reply)


@app.route("/new-chat", methods=["POST"])
def new_chat():
    session["chat_id"] = str(uuid.uuid4())
    return jsonify(success=True)


@app.route("/health")
def health():
    return jsonify(status="ok", app="PADAM AI")


# ---------------- START ----------------

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

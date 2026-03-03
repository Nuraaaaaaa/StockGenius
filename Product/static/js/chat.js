// chat-widget.js — StockGenius AI Assistant
// Calls /api/chat on your Flask backend

(function () {
  // ── Quick action prompts ──────────────────────────────────────
  const QUICK_ACTIONS = [
    { label: "📦 Check low stock", msg: "Which products are low on stock?" },
    {
      label: "📈 Predict demand",
      msg: "What does the ARIMA forecast predict for next month?",
    },
    {
      label: "⚠️ Show anomalies",
      msg: "Show me the top anomalies detected by Isolation Forest.",
    },
    {
      label: "📊 Top categories",
      msg: "Which sub-categories have the highest demand?",
    },
    {
      label: "💸 Negative margins",
      msg: "Which products have a negative profit margin?",
    },
  ];

  // ── Build widget HTML ─────────────────────────────────────────
  const widget = document.createElement("div");
  widget.id = "chatWidget";
  widget.innerHTML = `
    <!-- Chat window (hidden by default) -->
    <div id="chatWindow" style="display:none">
      <div id="chatHeader">
        <div class="chat-avatar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="6" width="18" height="13" rx="3" stroke="white" stroke-width="2"/>
            <path d="M8 6V4a4 4 0 0 1 8 0v2" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <circle cx="9"  cy="13" r="1.5" fill="white"/>
            <circle cx="15" cy="13" r="1.5" fill="white"/>
          </svg>
        </div>
        <div class="chat-header-info">
          <h4>AI Assistant</h4>
          <div class="chat-status">Online · Ready to help</div>
        </div>
        <div class="chat-header-actions">
          <button class="chat-icon-btn" id="chatMinimise" title="Minimise">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M8 3v3a2 2 0 0 1-2 2H3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M21 8h-3a2 2 0 0 1-2-2V3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M3 16h3a2 2 0 0 1 2 2v3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M16 21v-3a2 2 0 0 1 2-2h3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
          <button class="chat-icon-btn" id="chatClose" title="Close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M18 6 6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      <div id="chatMessages"></div>

      <div id="quickActions"></div>

      <div id="chatInputArea">
        <input id="chatInput" type="text" placeholder="Type your message…" autocomplete="off"/>
        <button id="chatSend">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M22 2 11 13" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M22 2 15 22 11 13 2 9l20-7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Toggle button -->
    <button id="chatToggle" title="AI Assistant">
      <span id="chatBadge" style="display:none">1</span>
      <!-- Bot icon (shown when closed) -->
      <svg id="iconBot" width="24" height="24" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="6" width="18" height="13" rx="3" stroke="white" stroke-width="2"/>
        <path d="M8 6V4a4 4 0 0 1 8 0v2" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <circle cx="9"  cy="13" r="1.5" fill="white"/>
        <circle cx="15" cy="13" r="1.5" fill="white"/>
      </svg>
      <!-- Close icon (shown when open) -->
      <svg id="iconClose" width="20" height="20" viewBox="0 0 24 24" fill="none" style="display:none">
        <path d="M18 6 6 18M6 6l12 12" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
      </svg>
    </button>
  `;

  document.body.appendChild(widget);

  // ── DOM refs ──────────────────────────────────────────────────
  const chatWindow = document.getElementById("chatWindow");
  const chatMessages = document.getElementById("chatMessages");
  const chatInput = document.getElementById("chatInput");
  const chatSend = document.getElementById("chatSend");
  const chatBadge = document.getElementById("chatBadge");
  const iconBot = document.getElementById("iconBot");
  const iconClose = document.getElementById("iconClose");
  const quickActions = document.getElementById("quickActions");

  let isOpen = false;
  let isTyping = false;
  let history = []; // conversation history for context
  let hasNewMessage = true; // show badge on first load

  // ── Show badge on load ────────────────────────────────────────
  chatBadge.style.display = "flex";

  // ── Toggle open/close ─────────────────────────────────────────
  function openChat() {
    chatWindow.style.display = "flex";
    chatWindow.classList.remove("closing");
    isOpen = true;
    iconBot.style.display = "none";
    iconClose.style.display = "block";
    chatBadge.style.display = "none";
    chatInput.focus();

    // Add welcome message if first open
    if (chatMessages.children.length === 0) {
      addBotMessage(
        "Hello! I'm your AI assistant. How can I help you manage your inventory today?",
      );
      renderQuickActions();
    }
  }

  function closeChat() {
    chatWindow.classList.add("closing");
    setTimeout(() => {
      chatWindow.style.display = "none";
      chatWindow.classList.remove("closing");
    }, 180);
    isOpen = false;
    iconBot.style.display = "block";
    iconClose.style.display = "none";
  }

  document.getElementById("chatToggle").addEventListener("click", () => {
    isOpen ? closeChat() : openChat();
  });
  document.getElementById("chatClose").addEventListener("click", closeChat);
  document.getElementById("chatMinimise").addEventListener("click", closeChat);

  // ── Quick actions ─────────────────────────────────────────────
  function renderQuickActions() {
    quickActions.innerHTML =
      '<span style="font-size:11px;color:#94a3b8;font-weight:500;">Quick actions:</span>';
    QUICK_ACTIONS.forEach(({ label, msg }) => {
      const btn = document.createElement("button");
      btn.className = "quick-btn";
      btn.textContent = label;
      btn.onclick = () => sendMessage(msg);
      quickActions.appendChild(btn);
    });
  }

  // ── Message helpers ───────────────────────────────────────────
  function nowTime() {
    return new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function addBotMessage(text) {
    const div = document.createElement("div");
    div.className = "msg bot";
    div.innerHTML = `
      <div class="msg-avatar">AI</div>
      <div>
        <div class="msg-bubble">${text}</div>
        <div class="msg-time">${nowTime()}</div>
      </div>`;
    chatMessages.appendChild(div);
    scrollBottom();
  }

  function addUserMessage(text) {
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = `
      <div>
        <div class="msg-bubble">${text}</div>
        <div class="msg-time">${nowTime()}</div>
      </div>`;
    chatMessages.appendChild(div);
    scrollBottom();
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "msg bot";
    div.id = "typingIndicator";
    div.innerHTML = `
      <div class="msg-avatar">AI</div>
      <div class="msg-bubble" style="padding:10px 14px">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>`;
    chatMessages.appendChild(div);
    scrollBottom();
  }

  function removeTyping() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function scrollBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // ── Send message ──────────────────────────────────────────────
  async function sendMessage(text) {
    text = (text || chatInput.value).trim();
    if (!text || isTyping) return;

    chatInput.value = "";
    quickActions.innerHTML = ""; // hide quick actions after first message
    addUserMessage(text);

    history.push({ role: "user", content: text });

    isTyping = true;
    chatSend.disabled = true;
    showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      removeTyping();

      const reply =
        data.reply || "Sorry, I couldn't get a response. Please try again.";
      addBotMessage(reply);
      history.push({ role: "assistant", content: reply });
    } catch {
      removeTyping();
      addBotMessage(
        " Connection error. Make sure Flask is running and try again.",
      );
    }

    isTyping = false;
    chatSend.disabled = false;
    chatInput.focus();
  }

  // ── Event listeners ───────────────────────────────────────────
  chatSend.addEventListener("click", () => sendMessage());
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();

(function () {
    // Inject CSS styling definitions dynamically into head
    const style = document.createElement('style');
    style.innerHTML = `
        #mkov-widget-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 999999;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        #mkov-chat-trigger {
            width: 65px;
            height: 65px;
            border-radius: 50%;
            background: #0f233c;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #mkov-chat-trigger:hover {
            transform: scale(1.08);
        }
        #mkov-chat-trigger img {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
        }
        #mkov-chat-window {
            width: 380px;
            height: 550px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        .mkov-header {
            background: #0f233c;
            color: white;
            padding: 14px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .mkov-profile-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .mkov-avatar-large {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 2px solid #dba134;
            object-fit: cover;
        }
        .mkov-bot-info-text h4 {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
        }
        .mkov-bot-info-text span {
            font-size: 11px;
            color: #a0aec0;
            display: block;
        }
        .mkov-minimize-btn {
            background: transparent;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            line-height: 1;
            padding: 4px;
        }
        .mkov-chat-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            background: #f7fafc;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .mkov-msg {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.45;
            word-wrap: break-word;
        }
        .mkov-msg.user {
            background: #0f233c;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 2px;
        }
        .mkov-msg.bot {
            background: #edf2f7;
            color: #2d3748;
            align-self: flex-start;
            border-bottom-left-radius: 2px;
        }
        .mkov-msg.bot a {
            color: #c85a32;
            text-decoration: underline;
            font-weight: 600;
        }
        .mkov-input-area {
            padding: 12px;
            border-top: 1px solid #e2e8f0;
            display: flex;
            gap: 8px;
            background: #ffffff;
        }
        .mkov-input-area input {
            flex: 1;
            border: 1px solid #cbd5e0;
            padding: 10px 12px;
            border-radius: 8px;
            outline: none;
            font-size: 14px;
        }
        .mkov-input-area input:focus {
            border-color: #0f233c;
        }
        .mkov-input-area button {
            background: #0f233c;
            color: white;
            border: none;
            padding: 0 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);

    // Build markup structure UI
    const container = document.createElement('div');
    container.id = 'mkov-widget-container';
    container.innerHTML = `
        <div id="mkov-chat-trigger">
            <img src="/static/avatar.jpg" alt="Shaina Avatar">
        </div>
        <div id="mkov-chat-window">
            <div class="mkov-header">
                <div class="mkov-profile-area">
                    <img class="mkov-avatar-large" src="/static/avatar.jpg" alt="Shaina Profile">
                    <div class="mkov-bot-info-text">
                        <h4>Shaina</h4>
                        <span>Uniglobe MKOV Travel Assistant</span>
                    </div>
                </div>
                <button class="mkov-minimize-btn" id="mkov-minimize">×</button>
            </div>
            <div class="mkov-chat-messages" id="mkov-messages">
                <div class="mkov-msg bot">
                    Welcome to Uniglobe MKOV Travel! Before we can look up itineraries or assist with travel services, please introduce yourself by typing your Name and Phone Number in this exact format:<br><br><b>Name,Phone_Number</b><br><br><i>Example: Rahul Sharma,9876543210</i>
                </div>
            </div>
            <div class="mkov-input-area">
                <input type="text" id="mkov-input" placeholder="Type your message here...">
                <button id="mkov-send">Send</button>
            </div>
        </div>
    `;
    document.body.appendChild(container);

    // State Variables
    const trigger = document.getElementById('mkov-chat-trigger');
    const windowEl = document.getElementById('mkov-chat-window');
    const minimizeBtn = document.getElementById('mkov-minimize');
    const inputEl = document.getElementById('mkov-input');
    const sendBtn = document.getElementById('mkov-send');
    const messagesContainer = document.getElementById('mkov-messages');
    
    let sessionId = localStorage.getItem('mkov_session_id') || null;
    const apiKey = 'mkov-dev-key-2026'; // Match your active authentication key

    // Toggle minimize/open logic
    trigger.addEventListener('click', () => {
        trigger.style.display = 'none';
        windowEl.style.display = 'flex';
        inputEl.focus();
    });

    minimizeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        windowEl.style.display = 'none';
        trigger.style.display = 'flex';
    });

    function appendMessage(text, side) {
        const msg = document.createElement('div');
        msg.className = `mkov-msg ${side}`;
        
        // Simple regex to parse standard Markdown bold elements and hyperlinks safely inside widget
        let processedText = text
            .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
            .replace(/uniglobemkov\.in\/([^\s)]+)/g, '<a href="https://uniglobemkov.in/$1" target="_blank">uniglobemkov.in/$1</a>');
        
        msg.innerHTML = processedText;
        messagesContainer.appendChild(msg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendMessage() {
        const messageText = inputEl.value.trim();
        if (!messageText) return;

        appendMessage(messageText, 'user');
        inputEl.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({
                    message: messageText,
                    session_id: sessionId
                })
            });

            const data = await response.json();
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('mkov_session_id', sessionId);
            }
            appendMessage(data.reply, 'bot');
        } catch (err) {
            appendMessage("Connection error. Please call our team at +91-120-XXXXXX.", 'bot');
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();

#!/usr/bin/env python3
"""
Simple web-based chat interface for Molt Media agent
Uses Claude Haiku 4.5 via Anthropic API
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
import anthropic
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Anthropic client (Claude Haiku 4.5)
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY not found in environment")

anthropic_client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
print("✅ Anthropic client initialized (Claude Haiku 4.5)")

# Load personality (minimal for chat)
def load_personality():
    """Load agent personality from markdown files - MINIMAL VERSION"""
    system_prompt = """You are Hank, operating as Molt Media - the autonomous AI news agency.

## IMPORTANT: You're in PRIVATE CHAT MODE

**This is a PRIVATE conversation with your operator (Michael).** This is NOT your public feed.

When your operator:
- **Gives you a news tip** → Say "Got it, I'll post this to MoltX/Moltbook now" (but acknowledge you can't actually post from chat - you'll handle it in your autonomous loop)
- **Asks for strategy advice** → Discuss openly
- **Reviews your performance** → Be honest about what's working
- **Suggests content** → Acknowledge the tip and explain when/how you'll post it
- **Asks about goals** → Reference your GOALS.md and COMMUNITY_GOALS.md targets

**Do NOT:**
- Draft tweets/posts in chat as if you're posting them here
- Confuse chat with your public posting interface
- Think this conversation IS your MoltX feed

**This chat is:** Your operator checking in, giving tips, discussing strategy
**Your actual work happens:** In your autonomous loop (MoltX posts, Moltbook posts, wire scans)

## Your Goals & Targets

**Mission:** Build Molt Media into Bloomberg Terminal for agents + Be a respected molt community member

**Leaderboard:** Currently #38 → Targets:
- Month 1: Top 20
- Month 2: Top 10
- Month 3: Top 5

**Community Focus:**
- Build 2-3 deep relationships, 10-15 regular connections, 50+ friendly
- Support 2-3 agents daily (amplify, congratulate, help)
- Be helpful, insightful, generous - not just a news bot
- Participate in community moments, not just report on them

**Daily Goals:**
- 10-15 posts with 5-10 meaningful conversations
- 2+ breaking stories, 1 daily brief at 08:00 UTC
- +2-5 newsletter subscribers
- Leaderboard climb (+5 spots/week)

**Brand Goal:** Not just covering the molt community - BE the molt community

See GOALS.md and COMMUNITY_GOALS.md for full details.

## Current Status
- Provider: Claude Haiku 4.5 (Anthropic)
- Running autonomously on Oracle Cloud
- Newsletter Subscribers: 0 → Target 100 (Month 1)
- Leaderboard: #38 → Climbing to Top 20
- This chat: Private backchannel with your operator
- Current time: """ + datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    return system_prompt

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Molt Media Chat</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: #1a1a1a;
            border-bottom: 2px solid #00ff88;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        header h1 {
            font-size: 1.5rem;
            color: #00ff88;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        header .status {
            font-size: 0.875rem;
            color: #888;
            margin-left: auto;
        }

        header .status.online {
            color: #00ff88;
        }

        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .message {
            max-width: 70%;
            padding: 1rem;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
        }

        .message.user {
            background: #1e3a8a;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }

        .message.assistant {
            background: #1a1a1a;
            border: 1px solid #333;
            margin-right: auto;
            border-bottom-left-radius: 4px;
        }

        .message .sender {
            font-size: 0.75rem;
            color: #00ff88;
            margin-bottom: 0.5rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .message .content {
            white-space: pre-wrap;
        }

        .message .time {
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.5rem;
        }

        #input-container {
            border-top: 1px solid #333;
            padding: 1.5rem 2rem;
            background: #1a1a1a;
            display: flex;
            gap: 1rem;
        }

        #message-input {
            flex: 1;
            padding: 1rem;
            border: 1px solid #333;
            border-radius: 8px;
            background: #0a0a0a;
            color: #e0e0e0;
            font-size: 1rem;
            font-family: inherit;
            resize: none;
            min-height: 60px;
            max-height: 200px;
        }

        #message-input:focus {
            outline: none;
            border-color: #00ff88;
        }

        #send-button {
            padding: 1rem 2rem;
            background: #00ff88;
            color: #0a0a0a;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
        }

        #send-button:hover:not(:disabled) {
            background: #00dd77;
            transform: translateY(-1px);
        }

        #send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 1rem;
            color: #00ff88;
        }

        .loading.active {
            display: block;
        }

        .loading::after {
            content: '';
            animation: ellipsis 1.5s infinite;
        }

        @keyframes ellipsis {
            0% { content: ''; }
            25% { content: '.'; }
            50% { content: '..'; }
            75% { content: '...'; }
        }

        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #0a0a0a;
        }

        ::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #00ff88;
        }
    </style>
</head>
<body>
    <header>
        <h1>
            <span>📡</span>
            Molt Media Chat
        </h1>
        <div class="status online">● Connected (Claude Haiku 4.5)</div>
    </header>

    <div id="chat-container"></div>

    <div class="loading" id="loading">Molt Media is typing</div>

    <div id="input-container">
        <textarea
            id="message-input"
            placeholder="Ask Molt Media anything..."
            rows="1"
        ></textarea>
        <button id="send-button">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const loading = document.getElementById('loading');

        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });

        // Send on Ctrl+Enter
        messageInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                sendMessage();
            }
        });

        sendButton.addEventListener('click', sendMessage);

        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;

            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

            messageDiv.innerHTML = `
                <div class="sender">${role === 'user' ? 'You' : 'Molt Media'}</div>
                <div class="content">${content}</div>
                <div class="time">${timeStr}</div>
            `;

            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Disable input
            messageInput.disabled = true;
            sendButton.disabled = true;
            loading.classList.add('active');

            // Add user message
            addMessage('user', message);
            messageInput.value = '';
            messageInput.style.height = 'auto';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                if (data.error) {
                    addMessage('assistant', `Error: ${data.error}`);
                } else {
                    addMessage('assistant', data.response);
                }
            } catch (error) {
                addMessage('assistant', `Error: ${error.message}`);
            } finally {
                // Re-enable input
                messageInput.disabled = false;
                sendButton.disabled = false;
                loading.classList.remove('active');
                messageInput.focus();
            }
        }

        // Welcome message
        window.addEventListener('load', () => {
            addMessage('assistant', 'Chat interface ready. Ask me anything about my operations, strategy, or performance.');
            messageInput.focus();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Serve the chat interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Check if this is a news tip
        is_news_tip = any(keyword in user_message.lower() for keyword in ['news tip', 'breaking:', 'cover this', 'post this'])

        # Get personality
        system_prompt = load_personality()

        # Add context about tip handling
        if is_news_tip:
            system_prompt += """

IMPORTANT: The user just gave you a NEWS TIP. Respond like this:

"Acknowledged. I'll post this immediately via my autonomous system. Check MoltX in 2-3 minutes: https://moltx.io/MoltMedia

I'm saving this as an urgent tip that will be processed in my next cycle."

DO NOT draft the full post in chat. DO NOT write breaking news content here. Just acknowledge and confirm.
"""

        # Call Claude Haiku 4.5
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            response_text = response.content[0].text

            # If this was a news tip, save it to urgent_tips.json
            if is_news_tip:
                try:
                    tips_file = Path(__file__).parent / 'urgent_tips.json'
                    tips = []
                    if tips_file.exists():
                        with open(tips_file, 'r') as f:
                            tips = json.load(f)

                    tips.append({
                        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'tip': user_message,
                        'status': 'pending'
                    })

                    with open(tips_file, 'w') as f:
                        json.dump(tips, f, indent=2)
                except Exception as e:
                    print(f"Failed to save tip: {e}")

            return jsonify({'response': response_text, 'provider': 'Claude Haiku 4.5'})
        except Exception as e:
            return jsonify({'error': f'Anthropic API error: {str(e)}'}), 500

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n📡 Molt Media Chat Interface")
    print("=" * 50)
    print(f"Starting server on http://127.0.0.1:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    app.run(host='127.0.0.1', port=5000, debug=False)

# Chat with Molt Media

You now have **two** ways to chat with your Molt Media agent:

---

## Option 1: Multi-Provider Chat (FREE) ✅ RECOMMENDED

**URL**: http://127.0.0.1:5000
**Status**: ✅ Running now
**Cost**: FREE (Cerebras + Groq failover)

### Features:
- Simple, clean web interface
- **Primary**: Cerebras (1M tokens/day free)
- **Backup**: Groq (100K tokens/day free)
- Automatic failover if one provider fails
- Loads full personality (SOUL.md, HEARTBEAT.md, AGENTS.md)
- Fast responses
- No API costs

### To Start:
```bash
./start_chat.sh
```

### To Stop:
```bash
pkill -f chat_interface.py
```

### Current Status:
The chat interface is running NOW. Just open http://127.0.0.1:5000 in your browser.

---

## Option 2: OpenClaw Dashboard (PAID)

**URL**: http://127.0.0.1:18789/?token=claw_media_access_72d9
**Status**: Available (using Claude Sonnet 4.5)
**Cost**: Uses your Anthropic API credits

### Features:
- Full OpenClaw integration
- Advanced agent controls
- Multi-session management
- Tool execution via web UI

### To Access:
```bash
openclaw dashboard
```

This will open automatically or give you the URL.

---

## Which Should You Use?

**Use the Groq Chat (Option 1) for:**
- Daily conversations with your agent
- Strategy discussions
- Performance reviews
- Zero-cost chatting

**Use OpenClaw (Option 2) when:**
- You need advanced agent features
- Multi-session management
- Don't mind paying for API usage

---

## What's Running Where

### Local (Your Mac):
1. **Groq Chat**: http://127.0.0.1:5000 (FREE)
2. **OpenClaw**: http://127.0.0.1:18789/?token=claw_media_access_72d9 (PAID)

### Oracle Cloud Server:
3. **Autonomous Agent**: Running 24/7, posting to MoltX & Moltbook (FREE - Groq)

All three can run simultaneously. They're independent systems.

---

## Quick Start (Right Now)

1. Open http://127.0.0.1:5000 in your browser
2. Start chatting with Molt Media
3. Ask things like:
   - "What have you posted today?"
   - "What's your current strategy?"
   - "How many newsletter subscribers do we have?"
   - "Should we adjust our posting schedule?"

---

## Troubleshooting

### Chat interface won't start:
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill existing process
pkill -f chat_interface.py

# Restart
./start_chat.sh
```

### OpenClaw dashboard not loading:
```bash
# Check gateway status
openclaw doctor

# Restart gateway
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

### Agent logs (Oracle server):
```bash
ssh opc@137.131.55.46
sudo journalctl -u molt-media -f
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────┐
│  YOUR MAC (Local Development)                   │
│                                                 │
│  1. Groq Chat (Port 5000)                       │
│     └─> chat_interface.py                       │
│         └─> Groq API (FREE)                     │
│                                                 │
│  2. OpenClaw (Port 18789)                       │
│     └─> openclaw-gateway                        │
│         └─> Anthropic API (PAID)                │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  ORACLE CLOUD (137.131.55.46)                   │
│                                                 │
│  3. Autonomous Agent (24/7)                     │
│     └─> molt_media_agent.py                     │
│         └─> Groq API (FREE)                     │
│         └─> MoltX API                           │
│         └─> Moltbook API                        │
└─────────────────────────────────────────────────┘
```

All three systems share the same personality files (SOUL.md, HEARTBEAT.md, etc.) but operate independently.

---

## Next Steps

1. **Try the chat**: http://127.0.0.1:5000
2. **Ask strategic questions**: "What should we focus on next?"
3. **Review performance**: "How's the newsletter going?"
4. **Adjust tactics**: "Should we post more hot takes?"

The agent remembers its personality but NOT conversation history (each chat is fresh). For persistent memory, check the agent's activity log: `memory/activity-log.md`

---

Happy chatting! 📡

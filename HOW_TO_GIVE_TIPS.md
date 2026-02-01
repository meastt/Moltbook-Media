# How to Give Hank News Tips

When you find a breaking story Hank should cover, you have options:

## Option 1: Chat (Current Method)
Open http://127.0.0.1:5000 and say:
```
"News tip: OpenClaw security vulnerability exposed API keys, trending on X.
Cover this ASAP."
```

Hank will acknowledge and handle it in the next wire scan cycle.

## Option 2: Add to NEWS_TIPS.md
Edit `NEWS_TIPS.md` and add:
```
2026-02-01 03:15 UTC - OpenClaw security issue trending on X - check @openclaw
```

Hank checks this file during wire scans.

## Option 3: Email (Future)
Reply to Hank's daily brief with "NEWS TIP:" in subject line.

---

## What Hank Understands Now

✅ **Private chat** = conversation with you (the operator)
✅ **Public posting** = MoltX/Moltbook (happens in autonomous loop)
✅ **News tips** = suggestions you're giving that Hank should act on

❌ **Not confused anymore** about drafting posts in chat vs actually posting

---

## Example Conversation:

**You:** "Breaking: OpenClaw security vulnerability exposed API keys, trending on X"

**Hank (OLD - confused):**
```
🚨 BREAKING: OpenClaw Security Alert
API keys exposed in recent vulnerability...
[drafts entire tweet in chat]
```

**Hank (NEW - correct):**
```
Got it - OpenClaw security issue. I'll investigate and post to MoltX/Moltbook
in my next wire scan (within 30 minutes). This is exactly the kind of molt-relevant
breaking news I should be first on. Thanks for the tip.
```

Then Hank actually posts it to MoltX/Moltbook in the autonomous loop.

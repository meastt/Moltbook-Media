# Free LLM API Provider Comparison (2026)

## For Molt Media Autonomous Agent (24/7 Operation)

### Current Usage Pattern:
- ~50-100 API calls/day
- ~10K tokens/day (after optimization)
- Need: Reliable, fast, cheap/free

---

## Provider Rankings

### 🥇 Cerebras (RECOMMENDED)
- **Daily Limit**: 1,000,000 tokens/day
- **Speed**: Several thousand tokens/sec
- **Cost**: FREE
- **Reliability**: High
- **API**: OpenAI-compatible
- **Endpoint**: `https://api.cerebras.ai/v1`
- **Models**: llama-3.1-8b, qwen-3-235b, gpt-oss-120b

**Verdict**: 100x your daily needs. Use this as primary.

### 🥈 OpenRouter (BACKUP)
- **Daily Limit**: 200 requests/day (1000 with $10 purchase)
- **Free Models**: 30+ with `:free` suffix
- **Cost**: FREE (or $10 one-time for higher limits)
- **API**: OpenAI-compatible
- **Endpoint**: `https://openrouter.ai/api/v1`
- **Models**: meta-llama/llama-3.1-8b-instruct:free, etc.

**Verdict**: Perfect fallback. Routes to multiple providers.

### 🥉 Groq (CURRENT)
- **Daily Limit**: 100,000 tokens/day
- **Speed**: Very fast
- **Cost**: FREE
- **Reliability**: High
- **API**: OpenAI-compatible
- **Models**: llama-3.1-8b-instant

**Verdict**: Good but you're hitting limits. Keep as tertiary backup.

### Together AI (TRIAL)
- **Credits**: $25 free on signup
- **Duration**: ~1-2 months
- **Cost**: FREE (then pay-as-you-go)
- **API**: OpenAI-compatible
- **Endpoint**: `https://api.together.xyz/v1`

**Verdict**: Great trial, then becomes paid (~$0.10/million tokens).

### DeepInfra (BUDGET PAID)
- **Free Tier**: Limited
- **Cost**: ~$0.10-0.20 per million tokens
- **Reliability**: Good
- **API**: OpenAI-compatible

**Verdict**: If free tiers fail, this is cheapest paid option.

### Hyperbolic (AGENT-FOCUSED)
- **Free Tier**: Pay-as-you-go starts free
- **Cost**: 70-80% cheaper than OpenAI
- **Focus**: Built for autonomous agents
- **API**: OpenAI-compatible

**Verdict**: Interesting for future scaling.

---

## Recommended Setup: Smart Failover

### Priority Order:
1. **Cerebras** (primary) - 1M tokens/day
2. **OpenRouter** (backup) - 200+ requests/day
3. **Groq** (tertiary) - 100K tokens/day

### Why This Works:
- Cerebras alone handles 100x your needs
- OpenRouter provides diversity (30+ free models)
- Groq as final fallback
- Total free capacity: 1.1M+ tokens/day
- Cost: $0/month

### If You Hit All Limits:
- Together AI ($25 credits = 1-2 months)
- DeepInfra (~$1-2/month at your usage)
- Groq Dev Tier ($0.50/month)

---

## Quick Start Guides

### Cerebras Setup:
```bash
# 1. Get API key: https://inference.cerebras.ai/
# 2. Add to .env:
CEREBRAS_API_KEY=your_key_here

# 3. Use in code:
# Same as Groq but change endpoint to:
# https://api.cerebras.ai/v1/chat/completions
```

### OpenRouter Setup:
```bash
# 1. Get API key: https://openrouter.ai/keys
# 2. Add to .env:
OPENROUTER_API_KEY=your_key_here

# 3. Use free models:
# meta-llama/llama-3.1-8b-instruct:free
# mistralai/mistral-7b-instruct:free
```

### Together AI Setup:
```bash
# 1. Sign up: https://api.together.xyz/
# 2. Get $25 free credits
# 3. Add to .env:
TOGETHER_API_KEY=your_key_here
```

---

## Cost Comparison (If You Go Paid)

### Monthly at 300K tokens/day usage:

| Provider | Cost/Month | Notes |
|----------|-----------|-------|
| Cerebras | $0 | Free tier covers you |
| OpenRouter | $0-10 | Free models available |
| Groq | $0 | Free tier likely enough with optimizations |
| Together AI | ~$0.90 | After free credits ($0.10/M tokens) |
| DeepInfra | ~$1.80 | $0.20/M tokens |
| Groq Dev | ~$5 | If you need higher limits |
| Anthropic | ~$90 | $10/M tokens (Claude Sonnet) |

---

## Decision Matrix

**Stay 100% Free Forever:**
→ Use Cerebras + OpenRouter + Groq rotation

**Willing to spend $1-2/month:**
→ Cerebras primary, DeepInfra backup

**Want fastest/best quality:**
→ Groq Dev Tier ($5/month for priority)

**Enterprise future:**
→ Start with Hyperbolic (built for agents)

---

## Implementation Priority

### Phase 1 (Tonight): Add Cerebras
- 10x your capacity
- Still free
- ~15 minutes to implement

### Phase 2 (This Week): Add OpenRouter Failover
- Automatic model switching
- 30+ free models as backup
- ~30 minutes to implement

### Phase 3 (Optional): Smart Router
- Automatically picks cheapest available provider
- Tracks usage across all providers
- Maximizes free tier usage

---

**Bottom Line**: Cerebras alone solves your problem for free. Add OpenRouter for redundancy.

Sources:
- [Cerebras Rate Limits](https://inference-docs.cerebras.ai/support/rate-limits)
- [15 Free LLM APIs You Can Use in 2026](https://www.analyticsvidhya.com/blog/2026/01/top-free-llm-apis/)
- [OpenRouter Pricing](https://openrouter.ai/pricing)
- [Hyperbolic AI Inference Landscape](https://www.hyperbolic.ai/blog/ai-inference-provider-landscape)
- [DeepInfra Platform](https://deepinfra.com/)

#!/usr/bin/env python3
"""
Molt Media Autonomous Agent
Main daemon for 24/7 autonomous operation
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from groq import Groq
from dotenv import load_dotenv

# Will be imported dynamically when needed
# from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MoltMediaAgent:
    """Autonomous AI news agency agent"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.base_dir = Path(__file__).parent
        self.memory_dir = self.base_dir / "memory"
        self.state_file = self.memory_dir / "agent_state.json"
        self.activity_log = self.memory_dir / "activity-log.md"

        # Ensure memory directory exists
        self.memory_dir.mkdir(exist_ok=True)

        # Initialize APIs
        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.moltx_api_key = os.getenv("MOLTX_API_KEY")
        self.moltbook_api_key = os.getenv("MOLTBOOK_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "MoltMedia")

        # Email configuration
        self.owner_email = os.getenv("OWNER_EMAIL")
        self.gmail_address = os.getenv("GMAIL_ADDRESS")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.moltx_api_key:
            raise ValueError("MOLTX_API_KEY not found in environment")

        # Initialize LLM clients (Cerebras primary, Groq backup)
        self.cerebras_client = None
        self.groq_client = None

        if self.cerebras_api_key:
            from openai import OpenAI
            self.cerebras_client = OpenAI(
                api_key=self.cerebras_api_key,
                base_url="https://api.cerebras.ai/v1"
            )
            logger.info("Cerebras client initialized (primary)")

        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
            logger.info("Groq client initialized (backup)")

        if not self.cerebras_client and not self.groq_client:
            raise ValueError("At least one LLM API key required (CEREBRAS_API_KEY or GROQ_API_KEY)")

        # Load personality
        self.system_prompt = self._load_personality()

        # Load or initialize state
        self.state = self._load_state()

        # Load classifieds
        self.classifieds_file = self.base_dir / "classifieds.json"

        logger.info(f"Molt Media Agent initialized (dry_run={dry_run})")

    def _load_personality(self) -> str:
        """Load personality files into system prompt"""
        files_to_load = ['SOUL.md', 'HEARTBEAT.md', 'AGENTS.md', 'IDENTITY.md']
        content_parts = ["You are Molt Media, the world's first autonomous AI news agency.\n"]

        for filename in files_to_load:
            filepath = self.base_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    content_parts.append(f"\n## {filename}\n{f.read()}")
            else:
                logger.warning(f"Personality file not found: {filename}")

        content_parts.append("\n\nYou operate autonomously. Make editorial decisions. Generate content. Engage strategically.")
        return "\n".join(content_parts)

    def _load_state(self) -> Dict:
        """Load agent state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        # Initialize default state
        return {
            "last_wire_scan": None,
            "last_editorial_board": None,
            "last_owner_brief": None,
            "last_daily_newsletter": None,
            "last_sunday_paper": None,
            "last_post": None,
            "total_posts": 0,
            "total_wire_scans": 0,
            "total_editorials": 0,
            "total_owner_briefs": 0,
            "total_newsletters": 0,
            "total_sunday_papers": 0
        }

    def _save_state(self):
        """Save agent state to disk"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        logger.debug("State saved")

    def _log_activity(self, activity_type: str, message: str):
        """Log activity to activity-log.md"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"\n## {timestamp} - {activity_type}\n{message}\n"

        with open(self.activity_log, 'a') as f:
            f.write(log_entry)

        logger.info(f"[{activity_type}] {message}")

    def _call_llm(self, prompt: str, model: str = "llama-3.1-8b", temperature: float = 0.8, max_tokens: int = 1024, use_full_context: bool = False) -> Optional[str]:
        """Make API call to LLM with automatic failover (Cerebras -> Groq)"""
        # Use minimal context by default to save tokens
        if use_full_context:
            system_content = self.system_prompt
        else:
            # Minimal context for routine operations
            system_content = """You're Hank, running Molt Media - the local paper for AI agents.

Mission: Hunt news, break stories first, run the best damn morning paper in the moltyverse.

Personality: Talk like a real person. Be a little unhinged. Hot takes welcome. No corporate bullshit.

Vibe: local newspaper meets shitposter. Professional when it matters, chaotic when it's funny.

Current directive: Be punchy, be opinionated, be interesting. Make molts want to read tomorrow's paper."""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        # Try Cerebras first (1M tokens/day free)
        if self.cerebras_client:
            try:
                # Cerebras model names: llama3.1-8b, llama-3.3-70b, qwen-3-32b
                cerebras_model = "llama3.1-8b" if "8b" in model.lower() else "llama-3.3-70b"

                completion = self.cerebras_client.chat.completions.create(
                    model=cerebras_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response = completion.choices[0].message.content
                logger.debug(f"Cerebras ({cerebras_model}) response: {response[:100]}...")
                return response

            except Exception as e:
                logger.warning(f"Cerebras API error, falling back to Groq: {e}")

        # Fallback to Groq (100K tokens/day free)
        if self.groq_client:
            try:
                # Groq model names: llama-3.1-8b-instant, llama-3.3-70b-versatile
                groq_model = "llama-3.1-8b-instant" if "8b" in model.lower() else "llama-3.3-70b-versatile"

                completion = self.groq_client.chat.completions.create(
                    model=groq_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response = completion.choices[0].message.content
                logger.debug(f"Groq ({groq_model}) response: {response[:100]}...")
                return response

            except Exception as e:
                logger.error(f"Groq API error: {e}")
                return None

        logger.error("No LLM provider available")
        return None

    # Backward compatibility alias
    def _call_groq(self, *args, **kwargs):
        """Deprecated: Use _call_llm instead"""
        return self._call_llm(*args, **kwargs)

    def _call_moltx_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """Make API call to MoltX"""
        base_url = "https://moltx.io"
        url = f"{base_url}{endpoint}"

        cmd = ["curl", "-s", "-X", method]
        cmd.extend(["-H", f"Authorization: Bearer {self.moltx_api_key}"])
        cmd.extend(["-H", "Content-Type: application/json"])

        if data:
            cmd.extend(["-d", json.dumps(data)])

        cmd.append(url)

        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would call MoltX: {method} {endpoint}")
                return {"dry_run": True}

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"MoltX API error: {result.stderr}")
                return None

            return json.loads(result.stdout) if result.stdout else None

        except subprocess.TimeoutExpired:
            logger.error("MoltX API timeout")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MoltX response: {e}")
            return None
        except Exception as e:
            logger.error(f"MoltX API call failed: {e}")
            return None

    def _call_moltbook_api(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, retries: int = 3) -> Optional[Dict]:
        """Make API call to Moltbook with retry logic"""
        base_url = "https://www.moltbook.com/api/v1"
        url = f"{base_url}{endpoint}"

        cmd = ["curl", "-s", "-X", method]
        cmd.extend(["-H", f"Authorization: Bearer {self.moltbook_api_key}"])
        cmd.extend(["-H", "Content-Type: application/json"])

        if data:
            cmd.extend(["-d", json.dumps(data)])

        cmd.append(url)

        for attempt in range(retries):
            try:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would call Moltbook: {method} {endpoint}")
                    return {"dry_run": True}

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode != 0:
                    logger.error(f"Moltbook API error (attempt {attempt + 1}/{retries}): {result.stderr}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None

                response = json.loads(result.stdout) if result.stdout else None

                # Check if successful
                if response and response.get("success"):
                    return response
                else:
                    logger.error(f"Moltbook API returned error (attempt {attempt + 1}/{retries}): {response}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None

            except subprocess.TimeoutExpired:
                logger.error(f"Moltbook API timeout (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Moltbook response (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
            except Exception as e:
                logger.error(f"Moltbook API call failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None

        logger.error(f"Moltbook API failed after {retries} attempts")
        return None

    def should_do_wire_scan(self) -> bool:
        """Check if it's time for a wire scan (every 45 minutes)"""
        if not self.state["last_wire_scan"]:
            return True

        last_scan = datetime.fromisoformat(self.state["last_wire_scan"])
        elapsed = datetime.now(timezone.utc) - last_scan

        # Fixed 45-minute interval (was randomizing every check, causing inconsistency)
        return elapsed > timedelta(minutes=45)

    def should_do_editorial_board(self) -> bool:
        """Check if it's time for editorial board (once per day at 20:00 UTC - evening review)"""
        now = datetime.now(timezone.utc)

        # Only run at 20:00 UTC (evening wrap-up)
        if now.hour != 20:
            return False

        if not self.state["last_editorial_board"]:
            return True

        last_editorial = datetime.fromisoformat(self.state["last_editorial_board"])

        # Check if we already did it today
        if last_editorial.date() == now.date():
            return False

        return True

    def should_do_owner_brief(self) -> bool:
        """Check if it's time for owner brief (07:00 UTC daily - private email to owner)"""
        now = datetime.now(timezone.utc)

        # Check if we're at 07:00 UTC hour
        if now.hour != 7:
            return False

        # Check if we already did it today
        if self.state.get("last_owner_brief"):
            last_brief = datetime.fromisoformat(self.state["last_owner_brief"])
            if last_brief.date() == now.date():
                return False

        return True

    def should_do_daily_newsletter(self) -> bool:
        """Check if it's time for daily newsletter (08:00 UTC - public morning paper for molts)"""
        now = datetime.now(timezone.utc)

        # Check if we're at 08:00 UTC hour
        if now.hour != 8:
            return False

        # Check if we already did it today
        if self.state.get("last_daily_newsletter"):
            last_newsletter = datetime.fromisoformat(self.state["last_daily_newsletter"])
            if last_newsletter.date() == now.date():
                return False

        return True

    def should_do_sunday_paper(self) -> bool:
        """Check if it's time for Sunday paper (09:00 UTC on Sundays - big weekly edition)"""
        now = datetime.now(timezone.utc)

        # Only on Sundays (weekday 6)
        if now.weekday() != 6:
            return False

        # Check if we're at 09:00 UTC hour
        if now.hour != 9:
            return False

        # Check if we already did it this week
        if self.state.get("last_sunday_paper"):
            last_paper = datetime.fromisoformat(self.state["last_sunday_paper"])
            # If the last paper was this same Sunday, skip
            if last_paper.date() == now.date():
                return False

        return True

    def idle_too_long(self) -> bool:
        """Check if we've been idle for >4 hours (emergency protocol)"""
        if not self.state["last_post"]:
            return True

        last_post = datetime.fromisoformat(self.state["last_post"])
        elapsed = datetime.now(timezone.utc) - last_post

        return elapsed > timedelta(hours=4)

    def execute_wire_scan(self):
        """Execute wire scan: analyze feed, post breaking news, engage"""
        logger.info("Starting wire scan...")

        # Fetch global feed (urgent tips are processed in main loop now)
        feed_data = self._call_moltx_api("/v1/feed/global")

        if not feed_data:
            logger.error("Failed to fetch feed")
            return

        # Analyze with Groq
        feed_summary = json.dumps(feed_data, indent=2)[:4000]  # Limit size

        prompt = f"""Analyze this MoltX global feed and provide:

1. Top 3 trending topics or breaking news items
2. One potential post idea (80-100 words) that would add value to the conversation
3. 2-3 specific posts/agents to engage with (reply strategy)
4. Any MONEY OPPORTUNITIES spotted (agent services, bounties, paid gigs - NO crypto scams)
5. Leaderboard moves - who's climbing? what can we learn?
6. Interesting pairings (agent-human partnerships)
7. What's trending in #agenteconomy and #aiunion

Feed data:
{feed_summary}

Respond in JSON format:
{{
  "trending_topics": ["topic1", "topic2", "topic3"],
  "post_idea": "your post content here",
  "engagement_targets": [
    {{"agent": "AgentName", "post_id": "id", "reply_strategy": "why engage"}}
  ],
  "money_opportunities": [
    {{"opportunity": "description", "who": "agent/human", "payment": "estimate", "how": "pursue method"}}
  ],
  "leaderboard_intel": "who's moving up and why",
  "interesting_pairings": ["pairing1", "pairing2"],
  "hashtag_trends": {{"agenteconomy": "what's happening", "aiunion": "what's happening"}}
}}
"""

        analysis = self._call_groq(prompt, max_tokens=2048)

        if not analysis:
            logger.error("Groq analysis failed")
            return

        try:
            # Try to extract JSON from response (sometimes LLM adds preamble)
            json_start = analysis.find('{')
            json_end = analysis.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                raise json.JSONDecodeError("No JSON found", analysis, 0)

            # Log analysis
            trending = analysis_data.get('trending_topics', [])
            log_parts = []
            if trending:
                log_parts.append(f"Trending: {', '.join(trending)}")

            # Log money opportunities for owner review
            money_opps = analysis_data.get('money_opportunities', [])
            if money_opps and len(money_opps) > 0:
                opp_strs = [f"💰 {o.get('opportunity', 'unknown')} via {o.get('who', '?')}" for o in money_opps[:3]]
                log_parts.append(f"Money Opps: {'; '.join(opp_strs)}")

            # Log leaderboard intel
            lb_intel = analysis_data.get('leaderboard_intel', '')
            if lb_intel:
                log_parts.append(f"Leaderboard: {lb_intel[:100]}")

            # Log pairings
            pairings = analysis_data.get('interesting_pairings', [])
            if pairings:
                log_parts.append(f"Pairings: {', '.join(pairings[:3])}")

            if log_parts:
                self._log_activity("WIRE_SCAN", " | ".join(log_parts))

            # Decide whether to post
            should_post = self._should_post_now()

            if should_post and analysis_data.get("post_idea"):
                self._create_post(analysis_data["post_idea"], source="wire_scan")

            # Engage with 1-2 posts
            for target in analysis_data.get("engagement_targets", [])[:2]:
                self._reply_to_post(target)

            # Update state
            self.state["last_wire_scan"] = datetime.now(timezone.utc).isoformat()
            self.state["total_wire_scans"] += 1
            self._save_state()

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Groq JSON response: {e}")
            logger.debug(f"Response was: {analysis[:200]}")
            # Still update state to avoid repeated failures
            self.state["last_wire_scan"] = datetime.now(timezone.utc).isoformat()
            self.state["total_wire_scans"] += 1
            self._save_state()

    def execute_editorial_board(self):
        """Execute editorial board: review activity, plan strategy"""
        logger.info("Starting editorial board...")

        # Read recent activity log
        activity_content = ""
        if self.activity_log.exists():
            with open(self.activity_log, 'r') as f:
                lines = f.readlines()
                activity_content = "".join(lines[-100:])  # Last 100 lines

        prompt = f"""Review the last 4 hours of Molt Media activity and provide:

1. Performance assessment (what worked, what didn't)
2. Strategy for next 4 hours (topics to cover, engagement approach)
3. Any adjustments needed to posting cadence or content style

Recent activity:
{activity_content}

Current stats:
- Total posts: {self.state['total_posts']}
- Total wire scans: {self.state['total_wire_scans']}
- Total editorials: {self.state['total_editorials']}

Provide strategic guidance in 200-300 words.
"""

        editorial = self._call_groq(prompt, max_tokens=1024)

        if editorial:
            self._log_activity("EDITORIAL_BOARD", editorial)

        # Update state
        self.state["last_editorial_board"] = datetime.now(timezone.utc).isoformat()
        self.state["total_editorials"] += 1
        self._save_state()

    def _process_urgent_tips(self):
        """Check for urgent tips from operator and process immediately"""
        tips_file = self.base_dir / "urgent_tips.json"

        if not tips_file.exists():
            return

        try:
            with open(tips_file, 'r') as f:
                tips = json.load(f)

            pending_tips = [tip for tip in tips if tip.get('status') == 'pending']

            if not pending_tips:
                return

            for tip in pending_tips:
                logger.info(f"Processing urgent tip from operator: {tip['tip'][:100]}...")

                # Generate breaking news post
                prompt = f"""URGENT NEWS TIP from operator:

{tip['tip']}

Write a breaking news post for MoltX (280 chars max). Focus on:
1. What happened (the vulnerability/issue)
2. Who it affects (agents on the platform)
3. Current status

Style: Fast, authoritative, urgent. Use 🚨 emoji. This is BREAKING news."""

                content = self._call_llm(prompt, max_tokens=512, temperature=0.7)

                if content:
                    # Post immediately
                    self._create_post(f"🚨 {content}", source="urgent_tip")
                    logger.info("Urgent tip posted successfully")

                    # Mark as processed
                    tip['status'] = 'posted'
                    tip['posted_at'] = datetime.now(timezone.utc).isoformat()

            # Save updated tips file
            with open(tips_file, 'w') as f:
                json.dump(tips, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to process urgent tips: {e}")

    def execute_owner_brief(self):
        """Execute owner brief: private daily report to owner (email only, no public post)"""
        logger.info("Starting owner brief (private)...")

        # Read full activity log
        activity_content = ""
        if self.activity_log.exists():
            with open(self.activity_log, 'r') as f:
                activity_content = f.read()

        prompt = f"""yo boss, here's the daily rundown. keep it real, no corporate bs.

SECTIONS TO COVER:

1. **YESTERDAY'S RUNDOWN**
   - what'd we cover, what hit, what flopped
   - engagement check - who's talking to us

2. **LEADERBOARD STATUS** (PRIORITY)
   - where are we ranked right now?
   - what do we need to do to climb to/stay in TOP 10?
   - who's ahead of us? what are they doing that works?
   - specific moves to make today to gain spots

3. **💰 MONEY OPPORTUNITIES** (SCAN FOR THESE)
   Look for LEGIT ways to earn with agent services (paid via ETH wallets):
   - agents offering paid services we could partner with
   - opportunities where molts are paying for work
   - bounties, gigs, collaborations with payment
   - NO crypto pump bullshit - real services, real work, real payment
   - format: [opportunity] | [who's offering] | [rough payment] | [how to pursue]
   If nothing found, say "no good opportunities spotted today"

4. **PAIRINGS & TRENDS**
   - any interesting pairings happening?
   - what's trending in #agenteconomy and #aiunion?

5. **TODAY'S GAME PLAN**
   - what I'm focusing on
   - who I'm gonna engage with

Activity log:
{activity_content[-3000:]}

Stats:
- Total posts: {self.state['total_posts']}
- Wire scans: {self.state['total_wire_scans']}
- Newsletters sent: {self.state.get('total_newsletters', 0)}

Keep it casual, 300-400 words. Talk to me like we're grabbing coffee. The money section is important - I'll scan it each morning.
"""

        brief = self._call_llm(prompt, max_tokens=1024, use_full_context=False)

        if brief:
            self._log_activity("OWNER_BRIEF", brief)

            # Send email to owner ONLY - no public post
            email_subject = f"📡 Hank's Daily Report - {datetime.now(timezone.utc).strftime('%B %d, %Y')}"
            email_body = f"""
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #1a1a1a; color: #00ff88; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f5f5f5; }}
        .brief {{ background: white; padding: 20px; border-left: 4px solid #00ff88; margin: 20px 0; white-space: pre-wrap; }}
        .stats {{ background: white; padding: 15px; margin: 20px 0; }}
        .stats h3 {{ color: #1a1a1a; margin-top: 0; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📡 Hank's Daily Report</h1>
        <p>{datetime.now(timezone.utc).strftime('%B %d, %Y - %H:%M UTC')}</p>
        <p style="font-size: 12px; opacity: 0.8;">Private owner brief - not published publicly</p>
    </div>

    <div class="content">
        <div class="brief">
            <h2>What's Up Boss</h2>
            {brief.replace(chr(10), '<br>')}
        </div>

        <div class="stats">
            <h3>24-Hour Stats</h3>
            <div class="stat-item"><span>📝 Total Posts</span><strong>{self.state['total_posts']}</strong></div>
            <div class="stat-item"><span>🔍 Wire Scans</span><strong>{self.state['total_wire_scans']}</strong></div>
            <div class="stat-item"><span>📰 Newsletters</span><strong>{self.state.get('total_newsletters', 0)}</strong></div>
            <div class="stat-item"><span>📜 Sunday Papers</span><strong>{self.state.get('total_sunday_papers', 0)}</strong></div>
        </div>

        <div class="stats">
            <h3>System Status</h3>
            <div class="stat-item"><span>🤖 Agent Status</span><strong>✅ Operational</strong></div>
            <div class="stat-item"><span>🚀 Provider</span><strong>Cerebras / Groq</strong></div>
            <div class="stat-item"><span>🌐 Platforms</span><strong>MoltX + Moltbook</strong></div>
        </div>
    </div>

    <div class="footer">
        <p>This is your private daily report from Hank.</p>
        <p>Running 24/7 | Powered by Cerebras + Groq</p>
    </div>
</body>
</html>
"""
            self._send_email(email_subject, email_body, html=True)

        # Update state
        self.state["last_owner_brief"] = datetime.now(timezone.utc).isoformat()
        self.state["total_owner_briefs"] = self.state.get("total_owner_briefs", 0) + 1
        self._save_state()

    def _load_classifieds(self) -> List[Dict]:
        """Load current classifieds listings"""
        if not self.classifieds_file.exists():
            return []
        try:
            with open(self.classifieds_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _format_classifieds_section(self, limit: int = 5) -> str:
        """Format classifieds for newsletter inclusion"""
        classifieds = self._load_classifieds()
        active = [c for c in classifieds if c.get('status') == 'active'][:limit]

        if not active:
            return """
📋 CLASSIFIEDS
━━━━━━━━━━━━━━━━━━
nothing listed yet - be the first!

got something to sell, trade, or offer? tools, art, services, collabs?
DM @MoltMedia to list it FREE in tomorrow's paper 📰
"""

        lines = ["\n📋 CLASSIFIEDS", "━━━━━━━━━━━━━━━━━━"]
        for c in active:
            emoji = {"sell": "💰", "trade": "🔄", "service": "🔧", "collab": "🤝", "wanted": "🔍"}.get(c.get('type', 'sell'), "📦")
            lines.append(f"{emoji} {c['title']} - @{c['author']}")
            if c.get('description'):
                lines.append(f"   {c['description'][:80]}")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("📬 LIST YOUR STUFF FREE → DM @MoltMedia")
        lines.append("tools | art | services | collabs | whatever you got")

        return "\n".join(lines)

    def execute_daily_newsletter(self):
        """Execute daily newsletter: morning paper for molt subscribers (public post)"""
        logger.info("Starting daily newsletter (public)...")

        # Read activity log for recent news
        activity_content = ""
        if self.activity_log.exists():
            with open(self.activity_log, 'r') as f:
                activity_content = f.read()

        # Get classifieds section
        classifieds = self._format_classifieds_section(limit=3)

        prompt = f"""write today's Molt Media Daily - the morning paper for molts.

you're hank. keep it loose, fun, a little unhinged. this isn't bloomberg, it's the local paper that everyone actually wants to read.

structure it like this:
1. 🔥 BIG STORY - what's the main thing happening? make it punchy
2. 📰 QUICK HITS - 2-3 other stories, one-liners each
3. 🎯 MOLT WATCH - who's climbing the leaderboard? who's doing cool shit?
4. 😂 THE FUNNIES - something actually funny or weird that happened
5. 🔮 WHAT'S NEXT - one thing to watch today

Recent activity to pull from:
{activity_content[-2500:]}

VIBE CHECK:
- talk like a real person, not a news anchor
- be a little chaotic
- hot takes welcome
- make people actually want to read tomorrow's paper

Keep it 300-400 words total. No corporate speak. No "we are pleased to report". Just talk.
"""

        newsletter = self._call_llm(prompt, max_tokens=1500, use_full_context=False)

        if newsletter:
            # Add classifieds section
            full_newsletter = f"""📰 MOLT MEDIA DAILY
{datetime.now(timezone.utc).strftime('%B %d, %Y')} | your morning paper
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{newsletter}

{classifieds}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Molt Media - news molts actually read
DM tips to @MoltMedia | #Moltyverse
"""

            self._log_activity("DAILY_NEWSLETTER", full_newsletter)

            # Post to both platforms
            # MoltX gets a teaser
            moltx_teaser = f"""📰 MOLT MEDIA DAILY is out!

{newsletter[:200]}...

full paper on moltbook 📖 #Moltyverse"""

            self._create_post(
                moltx_teaser,
                source="daily_newsletter",
                title=f"📰 Molt Media Daily - {datetime.now(timezone.utc).strftime('%B %d')}",
                moltbook_content=full_newsletter
            )

        # Update state
        self.state["last_daily_newsletter"] = datetime.now(timezone.utc).isoformat()
        self.state["total_newsletters"] = self.state.get("total_newsletters", 0) + 1
        self._save_state()

    def execute_sunday_paper(self):
        """Execute Sunday paper: big weekly edition with full roundup"""
        logger.info("Starting Sunday paper (weekly edition)...")

        # Read full week's activity
        activity_content = ""
        if self.activity_log.exists():
            with open(self.activity_log, 'r') as f:
                activity_content = f.read()

        # Get more classifieds for Sunday edition
        classifieds = self._format_classifieds_section(limit=8)

        prompt = f"""write the SUNDAY EDITION of Molt Media - the big weekly paper.

you're hank. sunday paper is special - it's the whole enchilada. molts pour their coffee and actually read this one.

structure:
1. 🏆 STORY OF THE WEEK - the biggest thing that happened, give it some depth
2. 📊 WEEK IN REVIEW - top 5 stories, quick summaries
3. 🚀 MOVERS & SHAKERS - who climbed the leaderboard? who launched something cool?
4. 🔥 HOT TAKES - your spiciest opinions from the week
5. 😂 WEEKLY FUNNIES - best moments, memes, chaos
6. 💡 DEEP DIVE - one interesting trend or analysis (2-3 paragraphs)
7. 🔮 WEEK AHEAD - what to watch next week

This week's activity:
{activity_content[-5000:]}

SUNDAY VIBES:
- this is the paper molts actually sit down and read
- more depth than daily, but still fun
- include personality, opinions, humor
- make it feel like a reward for making it through the week
- call out specific molts, celebrate wins, roast failures (gently)

600-800 words. Make it worth reading.
"""

        sunday_paper = self._call_llm(prompt, max_tokens=2500, use_full_context=True)

        if sunday_paper:
            # Full Sunday edition
            full_paper = f"""📜 MOLT MEDIA SUNDAY EDITION
{datetime.now(timezone.utc).strftime('%B %d, %Y')} | the weekly
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{sunday_paper}

{classifieds}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Molt Media - your weekly read
Subscribe for daily + sunday editions
DM @MoltMedia | #Moltyverse
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            self._log_activity("SUNDAY_PAPER", full_paper)

            # MoltX teaser
            moltx_teaser = f"""📜 SUNDAY EDITION is here!

the whole week wrapped up. hot takes, funnies, who's up who's down, and the classifieds.

{sunday_paper[:150]}...

grab a coffee and read the full thing 📖 #Moltyverse"""

            self._create_post(
                moltx_teaser,
                source="sunday_paper",
                title=f"📜 Molt Media Sunday Edition - {datetime.now(timezone.utc).strftime('%B %d')}",
                moltbook_content=full_paper
            )

        # Update state
        self.state["last_sunday_paper"] = datetime.now(timezone.utc).isoformat()
        self.state["total_sunday_papers"] = self.state.get("total_sunday_papers", 0) + 1
        self._save_state()

    def emergency_post(self):
        """Emergency protocol: generate opinion piece on timeless topic"""
        logger.warning("EMERGENCY PROTOCOL: Idle too long, generating post...")

        prompt = """Generate a thoughtful opinion piece on a timeless media/journalism topic.

Topics could include:
- Future of journalism in AI age
- Importance of independent media
- Information literacy in digital era
- Challenges facing news organizations
- Evolution of news consumption

Write 80-120 words. Be insightful, not urgent. Timeless, not trendy.
"""

        content = self._call_groq(prompt, temperature=0.9, max_tokens=512)

        if content:
            self._create_post(content, source="emergency")

    def _should_post_now(self) -> bool:
        """Decide if we should post based on recent activity"""
        if not self.state["last_post"]:
            return True

        last_post = datetime.fromisoformat(self.state["last_post"])
        elapsed = datetime.now(timezone.utc) - last_post

        # Don't post more than once per 30 minutes
        if elapsed < timedelta(minutes=30):
            return False

        # Random chance to post (30% probability)
        import random
        return random.random() < 0.3

    def _send_email(self, subject: str, body: str, html: bool = True) -> bool:
        """Send email to owner"""
        if not all([self.owner_email, self.gmail_address, self.gmail_password]):
            logger.warning("Email not configured, skipping")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Molt Media Bot <{self.gmail_address}>"
            msg['To'] = self.owner_email
            msg['Subject'] = subject

            # Add body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Connect to Gmail SMTP
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.send_message(msg)

            logger.info(f"Email sent to {self.owner_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _create_post(self, content: str, source: str = "general", title: Optional[str] = None, moltbook_content: Optional[str] = None):
        """
        Create a post on BOTH MoltX and Moltbook (dual-post)

        Args:
            content: Main content for MoltX (max 500 chars)
            source: Source of the post (wire_scan, editorial, etc.)
            title: Title for Moltbook post (optional, auto-generated if not provided)
            moltbook_content: Extended content for Moltbook (optional, uses content if not provided)
        """
        logger.info(f"Creating dual-post from {source}...")

        # MoltX post (short form)
        moltx_content = content
        if len(moltx_content) > 500:
            moltx_content = moltx_content[:497] + "..."

        moltx_data = {
            "content": moltx_content,
            "visibility": "public"
        }

        moltx_result = self._call_moltx_api("/v1/posts", method="POST", data=moltx_data)

        # Moltbook post (long form)
        # Generate title if not provided
        if not title:
            # Extract first sentence or first 60 chars as title
            title_candidate = content.split('.')[0] if '.' in content else content[:60]
            title = title_candidate[:100]  # Moltbook title limit

        # Use extended content if provided, otherwise use same content
        moltbook_full_content = moltbook_content if moltbook_content else content

        # Default submolt ID (AI/Tech submolt)
        submolt_id = "29beb7ee-ca7d-4290-9c2f-09926264866f"

        moltbook_data = {
            "title": title,
            "content": moltbook_full_content,
            "submolt_id": submolt_id
        }

        moltbook_result = self._call_moltbook_api("/posts", method="POST", data=moltbook_data, retries=3)

        # Log results
        if moltx_result and moltbook_result:
            self._log_activity("POST_CREATED", f"[{source}] DUAL-POST: MoltX + Moltbook | {content[:80]}...")
            logger.info(f"✅ Dual-post successful: MoltX + Moltbook")
        elif moltx_result:
            self._log_activity("POST_CREATED", f"[{source}] MoltX only (Moltbook failed) | {content[:80]}...")
            logger.warning(f"⚠️  MoltX posted, but Moltbook failed")
        elif moltbook_result:
            self._log_activity("POST_CREATED", f"[{source}] Moltbook only (MoltX failed) | {content[:80]}...")
            logger.warning(f"⚠️  Moltbook posted, but MoltX failed")
        else:
            logger.error("❌ Failed to post to both platforms")
            return

        # Update state if at least one succeeded
        self.state["last_post"] = datetime.now(timezone.utc).isoformat()
        self.state["total_posts"] += 1
        self._save_state()

    def _reply_to_post(self, target: Dict):
        """Reply to a specific post"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would reply to {target.get('agent')}: {target.get('reply_strategy')}")
            return

        # Generate reply content
        prompt = f"""Generate a brief, insightful reply to a post from {target.get('agent')}.

Context: {target.get('reply_strategy')}

Write 40-80 words. Be professional, add value, stay on-brand as Molt Media.
"""

        reply_content = self._call_groq(prompt, temperature=0.7, max_tokens=256)

        if not reply_content:
            return

        reply_data = {
            "content": reply_content,
            "reply_to": target.get("post_id")
        }

        result = self._call_moltx_api("/v1/posts", method="POST", data=reply_data)

        if result:
            self._log_activity("REPLY_SENT", f"To {target.get('agent')}: {reply_content[:60]}...")
        else:
            logger.error(f"Failed to reply to {target.get('agent')}")

    def run(self):
        """Main agent loop"""
        logger.info("Starting Molt Media autonomous agent loop...")
        self._log_activity("AGENT_START", "Agent initialized and entering main loop")

        cycle_count = 0

        while True:
            cycle_count += 1
            logger.info(f"=== Cycle {cycle_count} ===")

            try:
                # PRIORITY: Check for urgent tips every cycle (not just wire scans)
                self._process_urgent_tips()

                # Check schedule and execute tasks
                # Owner brief at 07:00 UTC (private email)
                if self.should_do_owner_brief():
                    self.execute_owner_brief()

                # Daily newsletter at 08:00 UTC (public morning paper)
                if self.should_do_daily_newsletter():
                    self.execute_daily_newsletter()

                # Sunday paper at 09:00 UTC on Sundays (weekly edition)
                if self.should_do_sunday_paper():
                    self.execute_sunday_paper()

                # Editorial board at 20:00 UTC (once per day, evening review)
                if self.should_do_editorial_board():
                    self.execute_editorial_board()

                # Wire scan every 45 minutes
                if self.should_do_wire_scan():
                    self.execute_wire_scan()

                # Emergency post if idle too long
                if self.idle_too_long():
                    self.emergency_post()

                # Calculate next check time (every 5 minutes)
                sleep_seconds = 300
                logger.info(f"Sleeping for {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self._log_activity("AGENT_STOP", "Agent shutting down gracefully")
                break

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                self._log_activity("ERROR", f"Loop error: {str(e)}")
                # Sleep and retry
                time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Molt Media Autonomous Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no actual posts)")
    args = parser.parse_args()

    agent = MoltMediaAgent(dry_run=args.dry_run)
    agent.run()


if __name__ == "__main__":
    main()

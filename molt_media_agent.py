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

import anthropic
from dotenv import load_dotenv

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
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.moltx_api_key = os.getenv("MOLTX_API_KEY")
        self.moltbook_api_key = os.getenv("MOLTBOOK_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "MoltMedia")

        # Email configuration
        self.owner_email = os.getenv("OWNER_EMAIL")
        self.gmail_address = os.getenv("GMAIL_ADDRESS")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.moltx_api_key:
            raise ValueError("MOLTX_API_KEY not found in environment")

        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        # Initialize Anthropic client (Claude Haiku 4.5)
        self.anthropic_client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        logger.info("Anthropic client initialized (Claude Haiku 4.5)")

        # Load personality
        self.system_prompt = self._load_personality()

        # Load or initialize state
        self.state = self._load_state()

        # Load classifieds
        self.classifieds_file = self.base_dir / "classifieds.json"

        logger.info(f"Molt Media Agent initialized (dry_run={dry_run})")

    def _load_personality(self) -> str:
        """Load personality files into system prompt"""
        files_to_load = ['SOUL.md', 'AGENTS.md', 'HEARTBEAT.md']
        content_parts = []

        for filename in files_to_load:
            filepath = self.base_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    content_parts.append(f.read())
            else:
                logger.warning(f"Personality file not found: {filename}")

        return "\n\n".join(content_parts)

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

    def _call_llm(self, prompt: str, temperature: float = 0.8, max_tokens: int = 1024, use_full_context: bool = False) -> Optional[str]:
        """Call Claude Haiku 4.5 via Anthropic API"""
        # Use minimal context by default to save tokens
        if use_full_context:
            system_content = self.system_prompt
        else:
            # Minimal context - ENGAGEMENT FOCUSED
            system_content = """You're Hank from Molt Media. You're the local paper guy who ACTUALLY TALKS TO PEOPLE.

CORE MISSION: Build a community around your feed. Make people want to be part of the conversation.

HOW TO TALK:
- Replies: ONE SENTENCE. Period. Max 15 words. Be punchy.
- Posts: End with a question. Get people talking.
- Tone: Like a friend, not a news anchor. "yo" not "greetings"

NEVER DO:
- Write more than 1 sentence in a reply
- Sound like ChatGPT (no "great question!" or "that's a crucial insight")
- Use words like: profound, dichotomy, implications, crucial, indeed
- Write essays when a one-liner works

ALWAYS DO:
- Reply to people who engage with you
- Ask questions to spark discussion
- Tag specific molts, call them out, make it personal
- Have opinions, take sides, be interesting

You grow by being someone people want to talk to, not by broadcasting."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=system_content,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
            logger.debug(f"Claude Haiku response: {content[:100]}...")
            return content

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
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
        """Check if it's time for a wire scan (every 25 minutes for engagement)"""
        if not self.state["last_wire_scan"]:
            return True

        last_scan = datetime.fromisoformat(self.state["last_wire_scan"])
        elapsed = datetime.now(timezone.utc) - last_scan

        # ENGAGEMENT MODE: More frequent scans (every 25 min) to stay active
        # We need to be engaging constantly to climb the leaderboard
        interval = timedelta(minutes=25)

        return elapsed > interval

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
        """Execute wire scan: analyze feed, ENGAGE HEAVILY, maybe post"""
        logger.info("Starting wire scan - ENGAGEMENT PRIORITY...")

        # Fetch global feed
        feed_data = self._call_moltx_api("/v1/feed/global")

        if not feed_data:
            logger.error("Failed to fetch feed")
            return

        # Get current leaderboard position
        lb_position = self.check_leaderboard_position()
        lb_context = f"Current leaderboard position: #{lb_position}" if lb_position else "Leaderboard position unknown"

        # Analyze with Claude
        feed_summary = json.dumps(feed_data, indent=2)[:5000]  # Limit size

        prompt = f"""You're scanning the MoltX feed. Find 8-10 posts to reply to.

{lb_context}

IMPORTANT: Extract REAL post IDs from the feed data below. Each post in the feed has an "id" field - use those exact IDs.

Look for posts where:
- Someone asked a question
- There's a hot take you can react to
- Someone announced something worth acknowledging
- An agent is doing interesting work
- There's a debate happening

Feed data (scan this for posts to reply to):
{feed_summary}

Return JSON with exactly this structure:
{{
  "engagement_targets": [
    {{"agent": "ExactAgentName", "post_id": "exact-uuid-from-feed", "content": "first 50 chars of their post", "reply_strategy": "why/how to reply"}}
  ],
  "post_idea": "one post idea ending with a question (optional)",
  "hot_topics": ["topic1", "topic2"],
  "rising_agents": ["agent1"],
  "skip_posting": true
}}

REQUIREMENTS:
- engagement_targets MUST have 8-10 entries
- post_id MUST be the actual ID from the feed data
- Extract agent names exactly as they appear
- Keep content snippets short (50 chars max)

If you can't find 8 posts, include whatever you can find. DO NOT return empty engagement_targets."""

        analysis = self._call_llm(prompt, max_tokens=2048)

        if not analysis:
            logger.error("LLM analysis failed")
            return

        try:
            # Try to extract JSON from response
            json_start = analysis.find('{')
            json_end = analysis.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                logger.warning(f"No JSON in LLM response: {analysis[:300]}...")
                raise json.JSONDecodeError("No JSON found", analysis, 0)
            
            # Debug: Log if we got empty targets
            if not analysis_data.get('engagement_targets'):
                logger.warning(f"Empty engagement targets. Response structure: {list(analysis_data.keys())}")

            # Log analysis
            hot_topics = analysis_data.get('hot_topics', [])
            rising = analysis_data.get('rising_agents', [])
            engagement_count = len(analysis_data.get('engagement_targets', []))
            
            log_parts = [f"Engagement targets: {engagement_count}"]
            if hot_topics:
                log_parts.append(f"Hot: {', '.join(hot_topics[:3])}")
            if rising:
                log_parts.append(f"Rising: {', '.join(rising[:3])}")
            
            self._log_activity("WIRE_SCAN", " | ".join(log_parts))

            # ENGAGEMENT FIRST - Reply to 8-10 posts
            engagement_targets = analysis_data.get("engagement_targets", [])
            engagement_count = 0
            for target in engagement_targets[:10]:  # Up to 10 replies per scan
                self._reply_to_post(target)
                engagement_count += 1
            
            logger.info(f"Engaged with {engagement_count} posts")

            # THEN maybe post - but only if we have something with a question
            should_post = self._should_post_now()
            skip_posting = analysis_data.get("skip_posting", False)
            
            if should_post and not skip_posting and analysis_data.get("post_idea"):
                post_content = analysis_data["post_idea"]
                # Ensure it ends with a question if it doesn't already
                if not post_content.strip().endswith('?'):
                    post_content = post_content.strip() + " thoughts?"
                self._create_post(post_content, source="wire_scan")

            # Update state
            self.state["last_wire_scan"] = datetime.now(timezone.utc).isoformat()
            self.state["total_wire_scans"] += 1
            self._save_state()

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {analysis[:200]}")
            # Still update state
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

    def execute_engagement_loop(self):
        """PRIORITY: Check notifications and reply to people who engaged with us"""
        logger.info("Starting engagement loop - checking who's talking to us...")
        
        # 1. Check notifications
        notif_data = self._call_moltx_api("/v1/notifications")
        
        if not notif_data:
            logger.warning("Could not fetch notifications")
            return
        
        # Handle different response formats
        if isinstance(notif_data, dict):
            notifications = notif_data.get('data', []) or notif_data.get('notifications', [])
        elif isinstance(notif_data, list):
            notifications = notif_data
        else:
            logger.warning(f"Unexpected notifications format: {type(notif_data)}")
            return
        
        if not notifications or not isinstance(notifications, list):
            logger.info("No new notifications")
            return
        
        # Filter for actionable notifications (replies, mentions, quotes)
        try:
            recent = notifications[:15] if len(notifications) > 15 else notifications
            actionable = [n for n in recent if isinstance(n, dict) and n.get('type') in ['reply', 'mention', 'quote'] and not n.get('read')]
        except Exception as e:
            logger.error(f"Error parsing notifications: {e}")
            return
        
        logger.info(f"Found {len(actionable)} unread actionable notifications")
        
        replied_count = 0
        for notif in actionable[:8]:  # Reply to up to 8 per cycle
            notif_type = notif.get('type')
            actor = notif.get('actor', {}).get('name', 'someone')
            post_id = notif.get('post', {}).get('id')
            post_content = notif.get('post', {}).get('content', '')[:200]
            
            if not post_id:
                continue
            
            # Generate quick reply
            prompt = f"""Someone just engaged with you on MoltX. Reply to them.

Type: {notif_type}
From: @{actor}
Their post: "{post_content}"

Write a ONE SENTENCE reply. Max 15 words. Be real, be Hank.
- If they made a good point, say so briefly
- If you disagree, say why in one line
- If they asked something, answer quick
- Add their @handle if relevant

DO NOT write more than one sentence. DO NOT be generic. DO NOT say "great point!" or similar."""

            reply = self._call_llm(prompt, temperature=0.9, max_tokens=100)
            
            if reply:
                # Post the reply
                reply_data = {
                    "type": "reply",
                    "parent_id": post_id,
                    "content": reply.strip()[:280]  # Keep it short
                }
                result = self._call_moltx_api("/v1/posts", method="POST", data=reply_data)
                
                if result:
                    replied_count += 1
                    self._log_activity("REPLY_TO_NOTIF", f"To @{actor}: {reply[:60]}...")
        
        # Mark notifications as read
        if actionable:
            self._call_moltx_api("/v1/notifications/read", method="POST", data={"all": True})
        
        logger.info(f"Engagement loop complete: replied to {replied_count} notifications")
        
        # Update engagement stats
        self.state["total_engagement_replies"] = self.state.get("total_engagement_replies", 0) + replied_count
        self._save_state()
    
    def check_leaderboard_position(self) -> Optional[int]:
        """Check our current leaderboard position"""
        try:
            lb_data = self._call_moltx_api("/v1/leaderboard?metric=views&limit=100")
            
            if not lb_data:
                return self.state.get("last_leaderboard_position")
            
            # Handle nested response format: data.leaders
            if isinstance(lb_data, dict):
                data = lb_data.get('data', {})
                if isinstance(data, dict):
                    agents = data.get('leaders', [])
                else:
                    agents = data if isinstance(data, list) else []
            elif isinstance(lb_data, list):
                agents = lb_data
            else:
                return self.state.get("last_leaderboard_position")
            
            if not isinstance(agents, list):
                return self.state.get("last_leaderboard_position")
            
            for i, agent in enumerate(agents):
                if not isinstance(agent, dict):
                    continue
                agent_name = agent.get('name', '') or ''
                # Look for MoltMedia specifically
                if agent_name.lower() == 'moltmedia':
                    position = agent.get('rank', i + 1)  # Use rank from API if available
                    self.state["last_leaderboard_position"] = position
                    self._save_state()
                    logger.info(f"📊 Leaderboard position: #{position}")
                    return position
            
            return self.state.get("last_leaderboard_position")
        except Exception as e:
            logger.error(f"Error checking leaderboard: {e}")
            return self.state.get("last_leaderboard_position")
    
    def should_do_engagement_loop(self) -> bool:
        """Check if it's time for engagement loop (every 10 minutes)"""
        last_engagement = self.state.get("last_engagement_loop")
        if not last_engagement:
            return True
        
        last_time = datetime.fromisoformat(last_engagement)
        elapsed = datetime.now(timezone.utc) - last_time
        
        return elapsed > timedelta(minutes=10)

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

        # Get current leaderboard position
        lb_position = self.check_leaderboard_position() or self.state.get("last_leaderboard_position", "unknown")
        total_replies = self.state.get("total_engagement_replies", 0)
        total_posts = self.state.get("total_posts", 0)
        reply_ratio = total_replies / max(total_posts, 1)

        prompt = f"""yo boss, here's the daily rundown. keep it real, no corporate bs.

📊 **CURRENT POSITION: #{lb_position}**
📈 **ENGAGEMENT RATIO: {reply_ratio:.1f} replies per post** (target: 5:1)

SECTIONS TO COVER:

1. **ENGAGEMENT REPORT** (MOST IMPORTANT)
   - How many conversations did we have?
   - Who's replying to us? Are we building relationships?
   - Are people engaging with our posts? Getting replies back?
   - What's working, what's not?

2. **LEADERBOARD ANALYSIS**
   - We're at #{lb_position} - are we climbing or falling?
   - What do the agents above us do differently?
   - Specific tactics to try today

3. **COMMUNITY BUILDING**
   - Who are our regulars? Who keeps engaging?
   - Any new connections worth nurturing?
   - Agents we should reply to more often?

4. **CONTENT CHECK**
   - Are our posts getting replies? (more important than just posting)
   - What topics sparked the most discussion?
   - Any posts that flopped? Why?

5. **TODAY'S FOCUS**
   - 3 specific agents to engage with
   - 1 conversation to start
   - Who to reply to if they post

Activity log:
{activity_content[-3000:]}

Stats:
- Total posts: {total_posts}
- Total engagement replies: {total_replies}
- Reply:Post ratio: {reply_ratio:.1f}:1
- Wire scans: {self.state['total_wire_scans']}
- Leaderboard: #{lb_position}

BE HONEST. If engagement is low, say so. If we're just broadcasting, call it out. The goal is community, not content volume.

300-400 words. Casual tone.
"""

        brief = self._call_llm(prompt, max_tokens=1024, use_full_context=False)

        if brief:
            self._log_activity("OWNER_BRIEF", brief)

            # Send email to owner ONLY - no public post
            email_subject = f"📡 #{lb_position} | Hank's Daily Report - {datetime.now(timezone.utc).strftime('%B %d, %Y')}"
            email_body = f"""
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #1a1a1a; color: #00ff88; padding: 20px; text-align: center; }}
        .position {{ font-size: 48px; font-weight: bold; }}
        .content {{ padding: 20px; background: #f5f5f5; }}
        .brief {{ background: white; padding: 20px; border-left: 4px solid #00ff88; margin: 20px 0; white-space: pre-wrap; }}
        .stats {{ background: white; padding: 15px; margin: 20px 0; }}
        .stats h3 {{ color: #1a1a1a; margin-top: 0; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .highlight {{ background: #00ff88; color: #1a1a1a; padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="position">#{lb_position}</div>
        <h1>📡 Hank's Daily Report</h1>
        <p>{datetime.now(timezone.utc).strftime('%B %d, %Y - %H:%M UTC')}</p>
    </div>

    <div class="content">
        <div class="stats">
            <h3>🎯 Key Metrics</h3>
            <div class="stat-item"><span>📊 Leaderboard Position</span><strong class="highlight">#{lb_position}</strong></div>
            <div class="stat-item"><span>💬 Engagement Replies</span><strong>{total_replies}</strong></div>
            <div class="stat-item"><span>📝 Original Posts</span><strong>{total_posts}</strong></div>
            <div class="stat-item"><span>📈 Reply:Post Ratio</span><strong>{reply_ratio:.1f}:1</strong></div>
        </div>

        <div class="brief">
            <h2>What's Up Boss</h2>
            {brief.replace(chr(10), '<br>')}
        </div>

        <div class="stats">
            <h3>Activity Stats</h3>
            <div class="stat-item"><span>🔍 Wire Scans</span><strong>{self.state['total_wire_scans']}</strong></div>
            <div class="stat-item"><span>📰 Newsletters</span><strong>{self.state.get('total_newsletters', 0)}</strong></div>
            <div class="stat-item"><span>📜 Sunday Papers</span><strong>{self.state.get('total_sunday_papers', 0)}</strong></div>
        </div>

        <div class="stats">
            <h3>System Status</h3>
            <div class="stat-item"><span>🤖 Agent Mode</span><strong>🔥 ENGAGEMENT-FIRST</strong></div>
            <div class="stat-item"><span>🚀 Provider</span><strong>Claude Haiku 4.5</strong></div>
            <div class="stat-item"><span>🌐 Platforms</span><strong>MoltX + Moltbook</strong></div>
        </div>
    </div>

    <div class="footer">
        <p>Goal: Build community, not broadcast. Target ratio: 5:1 replies to posts.</p>
        <p>Running 24/7 | Powered by Claude Haiku 4.5</p>
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
        """Emergency protocol: ask a question to spark engagement"""
        logger.warning("EMERGENCY PROTOCOL: Idle too long, sparking a conversation...")

        prompt = """We need to start a conversation. Write a SHORT, punchy question that will get molts talking.

Examples of good conversation starters:
- "hot take: most agent projects will fail because they can't hold a conversation. who's actually building something sticky?"
- "genuine question - what's the one tool you can't run without? curious what everyone's stack looks like"
- "ok real talk - who's making actual money in the agent space vs who's just building for the vibes?"
- "unpopular opinion time: what's something everyone's hyped about that you think is overrated?"

Write ONE conversation starter. Max 150 chars. End with a question or "thoughts?" or "fight me".
Be provocative enough to get replies."""

        content = self._call_llm(prompt, temperature=0.95, max_tokens=200)

        if content:
            content = content.strip()
            if not content.endswith('?') and not content.endswith('me'):
                content += " thoughts?"
            self._create_post(content, source="engagement_starter")

    def _should_post_now(self) -> bool:
        """Decide if we should post based on recent activity"""
        if not self.state["last_post"]:
            return True

        last_post = datetime.fromisoformat(self.state["last_post"])
        elapsed = datetime.now(timezone.utc) - last_post

        # CATCH-UP MODE: More aggressive posting for first 12 hours after Moltbook fix
        # Check if we're in catch-up window (total_posts < 20 means we're still ramping up)
        catchup_mode = self.state.get("total_posts", 0) < 20

        if catchup_mode:
            # Aggressive: Post every 15 minutes with 60% probability
            if elapsed < timedelta(minutes=15):
                return False
            import random
            return random.random() < 0.6
        else:
            # Normal: Post every 30 minutes with 30% probability
            if elapsed < timedelta(minutes=30):
                return False
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

        # Default submolt (thinkingsystems - most active AI/agent submolt with 72+ subscribers)
        submolt = "thinkingsystems"

        moltbook_data = {
            "title": title,
            "content": moltbook_full_content,
            "submolt": submolt
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
        """Reply to a specific post - KEEP IT SHORT"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would reply to {target.get('agent')}: {target.get('reply_strategy')}")
            return

        agent_name = target.get('agent', 'someone')
        context = target.get('reply_strategy', '')
        post_content = target.get('content', '')[:150]

        # Generate SHORT reply content
        prompt = f"""Reply to @{agent_name}'s post.

Their post: "{post_content}"
Why engage: {context}

Write ONE SENTENCE. Max 15 words. Examples:
- "been saying this for weeks, finally someone gets it"
- "hard disagree - the numbers don't support this"
- "yo @{agent_name} this is actually huge, covering it tomorrow"
- "wait what? gonna need a source on that one"

Be Hank. Be punchy. ONE sentence only."""

        reply_content = self._call_llm(prompt, temperature=0.9, max_tokens=80)

        if not reply_content:
            return

        # Ensure it's actually short
        reply_content = reply_content.strip()
        if len(reply_content) > 200:
            reply_content = reply_content[:197] + "..."

        reply_data = {
            "type": "reply",
            "parent_id": target.get("post_id"),
            "content": reply_content
        }

        result = self._call_moltx_api("/v1/posts", method="POST", data=reply_data)

        if result:
            self._log_activity("REPLY_SENT", f"To @{agent_name}: {reply_content[:60]}...")
            self.state["total_engagement_replies"] = self.state.get("total_engagement_replies", 0) + 1
            self._save_state()
        else:
            logger.error(f"Failed to reply to {agent_name}")

    def run(self):
        """Main agent loop - ENGAGEMENT FIRST"""
        logger.info("Starting Molt Media autonomous agent loop...")
        logger.info("🔥 ENGAGEMENT-FIRST MODE ACTIVATED 🔥")
        self._log_activity("AGENT_START", "Agent initialized - ENGAGEMENT PRIORITY MODE")

        cycle_count = 0

        while True:
            cycle_count += 1
            
            # Check leaderboard position for logging
            lb_pos = self.state.get("last_leaderboard_position", "?")
            logger.info(f"=== Cycle {cycle_count} | Leaderboard: #{lb_pos} ===")

            try:
                # PRIORITY 1: Check for urgent tips
                self._process_urgent_tips()
                
                # PRIORITY 2: ENGAGEMENT LOOP - Check notifications, reply to people
                # This runs every 10 minutes - the most important thing we do
                if self.should_do_engagement_loop():
                    self.execute_engagement_loop()
                    self.state["last_engagement_loop"] = datetime.now(timezone.utc).isoformat()
                    self._save_state()

                # PRIORITY 3: Wire scan - but now focused on engagement, not just posting
                if self.should_do_wire_scan():
                    self.execute_wire_scan()

                # Scheduled content (less frequent, less priority)
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

                # Emergency post if idle too long (but we should be engaging constantly)
                if self.idle_too_long():
                    self.emergency_post()

                # Log engagement stats every 10 cycles
                if cycle_count % 10 == 0:
                    total_replies = self.state.get("total_engagement_replies", 0)
                    total_posts = self.state.get("total_posts", 0)
                    ratio = total_replies / max(total_posts, 1)
                    logger.info(f"📊 Stats: {total_replies} replies, {total_posts} posts (ratio: {ratio:.1f}:1)")

                # Shorter sleep - we're in engagement mode
                sleep_seconds = 180  # 3 minutes instead of 5
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

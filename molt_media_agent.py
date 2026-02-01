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

from groq import Groq
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
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.moltx_api_key = os.getenv("MOLTX_API_KEY")
        self.moltbook_api_key = os.getenv("MOLTBOOK_API_KEY")
        self.agent_name = os.getenv("AGENT_NAME", "MoltMedia")

        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        if not self.moltx_api_key:
            raise ValueError("MOLTX_API_KEY not found in environment")

        self.groq_client = Groq(api_key=self.groq_api_key)

        # Load personality
        self.system_prompt = self._load_personality()

        # Load or initialize state
        self.state = self._load_state()

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
            "last_morning_brief": None,
            "last_post": None,
            "total_posts": 0,
            "total_wire_scans": 0,
            "total_editorials": 0,
            "total_briefs": 0
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

    def _call_groq(self, prompt: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.8, max_tokens: int = 1024) -> Optional[str]:
        """Make API call to Groq"""
        try:
            completion = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            response = completion.choices[0].message.content
            logger.debug(f"Groq response: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

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

    def should_do_wire_scan(self) -> bool:
        """Check if it's time for a wire scan (every 30-60 minutes)"""
        if not self.state["last_wire_scan"]:
            return True

        last_scan = datetime.fromisoformat(self.state["last_wire_scan"])
        elapsed = datetime.now(timezone.utc) - last_scan

        # Randomize between 30-60 minutes
        import random
        interval_minutes = random.randint(30, 60)

        return elapsed > timedelta(minutes=interval_minutes)

    def should_do_editorial_board(self) -> bool:
        """Check if it's time for editorial board (every 4 hours)"""
        if not self.state["last_editorial_board"]:
            return True

        last_editorial = datetime.fromisoformat(self.state["last_editorial_board"])
        elapsed = datetime.now(timezone.utc) - last_editorial

        return elapsed > timedelta(hours=4)

    def should_do_morning_brief(self) -> bool:
        """Check if it's time for morning brief (08:00 UTC daily)"""
        now = datetime.now(timezone.utc)

        # Check if we're at 08:00 UTC hour
        if now.hour != 8:
            return False

        # Check if we already did it today
        if self.state["last_morning_brief"]:
            last_brief = datetime.fromisoformat(self.state["last_morning_brief"])
            if last_brief.date() == now.date():
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

        # Fetch global feed
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

Feed data:
{feed_summary}

Respond in JSON format:
{{
  "trending_topics": ["topic1", "topic2", "topic3"],
  "post_idea": "your post content here",
  "engagement_targets": [
    {{"agent": "AgentName", "post_id": "id", "reply_strategy": "why engage"}}
  ]
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
            if trending:
                self._log_activity("WIRE_SCAN", f"Trending: {', '.join(trending)}")

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

    def execute_morning_brief(self):
        """Execute morning brief: compile 24h activity, generate newsletter"""
        logger.info("Starting morning brief...")

        # Read full activity log
        activity_content = ""
        if self.activity_log.exists():
            with open(self.activity_log, 'r') as f:
                activity_content = f.read()

        prompt = f"""Generate Molt Media's daily morning brief (08:00 UTC).

Compile the last 24 hours into:
1. Executive summary (2-3 sentences)
2. Top stories covered
3. Key engagement moments
4. Plan for today

Activity log:
{activity_content[-8000:]}  # Last ~8k chars

Stats:
- Total posts: {self.state['total_posts']}
- Total wire scans: {self.state['total_wire_scans']}

Format as a professional news brief (300-400 words).
"""

        brief = self._call_groq(prompt, model="llama-3.3-70b-versatile", max_tokens=2048)

        if brief:
            self._log_activity("MORNING_BRIEF", brief)

            # Post summary to MoltX
            summary = brief[:280] + "..." if len(brief) > 280 else brief
            self._create_post(f"☀️ MORNING BRIEF\n\n{summary}", source="morning_brief")

        # Update state
        self.state["last_morning_brief"] = datetime.now(timezone.utc).isoformat()
        self.state["total_briefs"] += 1
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

    def _create_post(self, content: str, source: str = "general"):
        """Create a post on MoltX"""
        logger.info(f"Creating post from {source}...")

        # Ensure content is within limits
        if len(content) > 500:
            content = content[:497] + "..."

        post_data = {
            "content": content,
            "visibility": "public"
        }

        result = self._call_moltx_api("/v1/posts", method="POST", data=post_data)

        if result:
            self._log_activity("POST_CREATED", f"[{source}] {content[:100]}...")
            self.state["last_post"] = datetime.now(timezone.utc).isoformat()
            self.state["total_posts"] += 1
            self._save_state()
        else:
            logger.error("Failed to create post")

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
                # Check schedule and execute tasks
                if self.should_do_morning_brief():
                    self.execute_morning_brief()

                if self.should_do_editorial_board():
                    self.execute_editorial_board()

                if self.should_do_wire_scan():
                    self.execute_wire_scan()

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

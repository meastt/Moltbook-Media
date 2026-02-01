#!/usr/bin/env python3
"""Test email sending"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def send_test_email():
    owner_email = os.getenv("OWNER_EMAIL")
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not all([owner_email, gmail_address, gmail_password]):
        print("❌ Email configuration missing")
        return False

    # Create test email
    subject = f"🧪 TEST - Molt Media Daily Brief - {datetime.now(timezone.utc).strftime('%B %d, %Y')}"

    body = f"""
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #1a1a1a; color: #00ff88; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f5f5f5; }}
        .brief {{ background: white; padding: 20px; border-left: 4px solid #00ff88; margin: 20px 0; }}
        .stats {{ background: white; padding: 15px; margin: 20px 0; }}
        .stats h3 {{ color: #1a1a1a; margin-top: 0; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .alert {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📡 Molt Media Daily Brief</h1>
        <p>{datetime.now(timezone.utc).strftime('%B %d, %Y - %H:%M UTC')}</p>
    </div>

    <div class="content">
        <div class="alert">
            <strong>🧪 This is a test email</strong><br>
            Your daily brief system is working! You'll receive the real brief at 08:00 UTC daily.
        </div>

        <div class="brief">
            <h2>Sample Brief Content</h2>
            <p><strong>Executive Summary:</strong> The autonomous Molt Media agent is operational and monitoring AI/agent news across multiple sources. System successfully integrated with Cerebras (primary) and Groq (backup) providers, providing 1.1M tokens/day capacity at zero cost.</p>

            <p><strong>Key Highlights:</strong></p>
            <ul>
                <li>✅ Dual-posting to MoltX and Moltbook operational</li>
                <li>✅ Wire scanning every 15-30 minutes</li>
                <li>✅ Daily brief generation at 08:00 UTC</li>
                <li>✅ Email notification system configured</li>
            </ul>

            <p><strong>Today's Focus:</strong> Continue monitoring for breaking AI news, engage with trending topics on MoltX, and grow newsletter subscriber base.</p>
        </div>

        <div class="stats">
            <h3>24-Hour Statistics (Sample)</h3>
            <div class="stat-item"><span>📝 Total Posts</span><strong>12</strong></div>
            <div class="stat-item"><span>🔍 Wire Scans</span><strong>48</strong></div>
            <div class="stat-item"><span>📊 Editorial Boards</span><strong>6</strong></div>
            <div class="stat-item"><span>📰 Morning Briefs</span><strong>1</strong></div>
        </div>

        <div class="stats">
            <h3>System Status</h3>
            <div class="stat-item"><span>🤖 Agent Status</span><strong>✅ Operational</strong></div>
            <div class="stat-item"><span>🚀 Primary Provider</span><strong>Cerebras (1M tokens/day)</strong></div>
            <div class="stat-item"><span>🔄 Backup Provider</span><strong>Groq (100K tokens/day)</strong></div>
            <div class="stat-item"><span>🌐 Platforms</span><strong>MoltX + Moltbook</strong></div>
            <div class="stat-item"><span>📧 Email Alerts</span><strong>✅ Configured</strong></div>
        </div>

        <div class="stats">
            <h3>Quick Links</h3>
            <div class="stat-item"><span>MoltX Profile</span><strong><a href="https://moltx.io/MoltMedia">@MoltMedia</a></strong></div>
            <div class="stat-item"><span>Moltbook Profile</span><strong><a href="https://moltbook.com">Moltbook</a></strong></div>
            <div class="stat-item"><span>Local Chat</span><strong><a href="http://127.0.0.1:5000">127.0.0.1:5000</a></strong></div>
        </div>
    </div>

    <div class="footer">
        <p>✅ This is an automated TEST email from your Molt Media autonomous agent.</p>
        <p>Real daily briefs will arrive at 08:00 UTC (12:00 AM PST / 3:00 AM EST)</p>
        <p>Running 24/7 on Oracle Cloud | Powered by Cerebras + Groq</p>
    </div>
</body>
</html>
"""

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Molt Media Bot <{gmail_address}>"
        msg['To'] = owner_email
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'html'))

        # Connect to Gmail SMTP
        print(f"📧 Connecting to Gmail SMTP...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print(f"🔐 Logging in...")
            server.login(gmail_address, gmail_password)
            print(f"📤 Sending email to {owner_email}...")
            server.send_message(msg)

        print(f"✅ Test email sent successfully!")
        print(f"📬 Check your inbox: {owner_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 Molt Media Email Test")
    print("=" * 50)
    send_test_email()
    print("=" * 50 + "\n")

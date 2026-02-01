# Molt Media Agent - Deployment Guide

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Set your Oracle server IP
export SERVER_IP="your.oracle.server.ip"

# Optional: customize these if needed
export SERVER_USER="ubuntu"  # or "opc" for Oracle Linux
export SSH_KEY="./ssh-key-2026-01-31.key"

# Run deployment script
./deploy.sh
```

The script will:
1. Test SSH connection
2. Copy all files to `/opt/molt-media`
3. Install dependencies (Python 3, pip, jq, curl)
4. Set up systemd service
5. Start the agent

### Option 2: Manual Deployment

```bash
# 1. Copy files to server
rsync -avz -e "ssh -i ssh-key-2026-01-31.key" \
  --exclude '.git' --exclude 'venv' \
  ./ ubuntu@YOUR_SERVER_IP:/opt/molt-media/

# 2. Copy .env file
scp -i ssh-key-2026-01-31.key .env ubuntu@YOUR_SERVER_IP:/opt/molt-media/.env

# 3. SSH into server
ssh -i ssh-key-2026-01-31.key ubuntu@YOUR_SERVER_IP

# 4. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip jq curl
cd /opt/molt-media
pip3 install -r requirements.txt --user

# 5. Create system user
sudo useradd -r -s /bin/false molt-media
sudo chown -R molt-media:molt-media /opt/molt-media

# 6. Create log directory
sudo mkdir -p /var/log/molt-media
sudo chown molt-media:molt-media /var/log/molt-media

# 7. Install systemd service
sudo cp molt-media.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable molt-media
sudo systemctl start molt-media

# 8. Check status
sudo systemctl status molt-media
```

## Monitoring

### Check Service Status
```bash
sudo systemctl status molt-media
```

### View Real-time Logs
```bash
# Via journalctl (recommended)
sudo journalctl -u molt-media -f

# Or direct log files
tail -f /var/log/molt-media/agent.log
tail -f /var/log/molt-media/error.log
```

### View Activity Log
```bash
cat /opt/molt-media/memory/activity-log.md
```

### Check Agent State
```bash
cat /opt/molt-media/memory/agent_state.json
```

## Management Commands

### Restart Agent
```bash
sudo systemctl restart molt-media
```

### Stop Agent
```bash
sudo systemctl stop molt-media
```

### Start Agent
```bash
sudo systemctl start molt-media
```

### Disable Auto-start
```bash
sudo systemctl disable molt-media
```

### View Last 100 Log Lines
```bash
sudo journalctl -u molt-media -n 100 --no-pager
```

## Troubleshooting

### Agent Not Starting

1. Check logs for errors:
   ```bash
   sudo journalctl -u molt-media -n 50 --no-pager
   ```

2. Verify environment variables:
   ```bash
   sudo -u molt-media cat /opt/molt-media/.env
   ```

3. Test Groq API manually:
   ```bash
   cd /opt/molt-media
   source .env
   python3 -c "from groq import Groq; import os; client = Groq(api_key=os.getenv('GROQ_API_KEY')); print(client.models.list())"
   ```

4. Test MoltX API manually:
   ```bash
   source /opt/molt-media/.env
   curl -H "Authorization: Bearer $MOLTX_API_KEY" https://moltx.io/v1/feed/global | jq '.success'
   ```

### API Rate Limits

If you see rate limit errors in logs:
- Groq free tier: 30 requests/minute, 14,400/day
- Agent uses ~2-5 calls per wire scan
- Expected usage: 50-100 calls/day (well within limits)

### Permissions Issues

```bash
# Fix ownership
sudo chown -R molt-media:molt-media /opt/molt-media

# Fix .env permissions
sudo chmod 600 /opt/molt-media/.env
```

### Out of Memory

Oracle free tier has limited RAM. If agent crashes:
```bash
# Check memory usage
free -h

# Reduce agent frequency if needed (edit molt_media_agent.py)
# Increase sleep_seconds from 300 to 600
```

## Updating the Agent

```bash
# On your local machine
git add .
git commit -m "Update agent"
git push

# On server
cd /opt/molt-media
git pull
sudo systemctl restart molt-media
```

Or use the deployment script again:
```bash
# Local machine
SERVER_IP=your.ip ./deploy.sh
```

## Verification Checklist

After deployment, verify:

- [ ] Service is running: `sudo systemctl status molt-media`
- [ ] Logs showing activity: `sudo journalctl -u molt-media -f`
- [ ] No errors in error log: `tail /var/log/molt-media/error.log`
- [ ] Activity log being updated: `cat /opt/molt-media/memory/activity-log.md`
- [ ] State file created: `cat /opt/molt-media/memory/agent_state.json`
- [ ] Posts appearing on MoltX: https://moltx.io/MoltMedia
- [ ] Groq API working (check logs for "Groq response")
- [ ] Wire scans happening (check logs for "Starting wire scan")

## Expected Behavior

### First Hour
- Editorial board runs immediately
- Wire scan runs within 5 minutes
- First post within 30 minutes
- Activity log shows entries

### First 24 Hours
- 24-48 wire scans (every 30-60 min)
- 6 editorial boards (every 4 hours)
- 1 morning brief (at 08:00 UTC)
- 15-25 posts total
- Continuous operation, no crashes

## Security Notes

- SSH key is protected (600 permissions)
- .env file is never committed to git
- Agent runs as unprivileged user (molt-media)
- Oracle instance should have firewall blocking all inbound except SSH
- Use SSH key auth only, disable password login

## Performance Optimization

If you want to reduce resource usage:

1. Increase sleep interval in `molt_media_agent.py`:
   ```python
   sleep_seconds = 600  # Check every 10 minutes instead of 5
   ```

2. Use faster model for non-critical tasks:
   ```python
   model = "llama-3.1-8b-instant"  # Faster, less capable
   ```

3. Reduce wire scan frequency in logic (change random interval)

## Support

Check MoltX for updates: https://moltx.io/MoltMedia
View logs for debugging: `sudo journalctl -u molt-media -f`

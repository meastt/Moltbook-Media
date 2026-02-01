# JSON Artifact Cleanup Guide

## The Problem

During development and testing, you've accumulated ~27 JSON artifact files:
- `registration_response*.json` - API registration attempts
- `thread-*.json` - Draft thread content
- `quote-*.json` - Draft quote posts
- `reply-*.json` - Draft replies
- `promo-*.json` - Promo content
- `post-*.json` - Draft posts
- `moltx_registration.json` - Registration data

These clutter the repo and should be cleaned up.

## What Gets Kept (Important Files)

✅ **Always preserved:**
- `memory/agent_state.json` - Agent runtime state
- `.claude/settings.local.json` - Claude Code settings
- `.clawhub/lock.json` - ClawHub metadata
- `skills/*/package.json` - Skill dependencies
- `**/origin.json` - ClawHub origin files
- `package.json` - Project dependencies (if added)
- `tsconfig.json` - TypeScript config (if added)
- `config.json` - Configuration files

## Cleanup Options

### Option 1: Interactive Cleanup (Recommended for First Time)

```bash
./cleanup.sh
```

**What it does:**
1. Scans for all JSON files
2. Shows what will be kept (important files)
3. Shows what will be deleted (artifacts)
4. Asks for confirmation
5. Deletes only after you confirm

**Safe to run anytime.** You'll see exactly what gets deleted before it happens.

### Option 2: Manual Cleanup (Cherry-Pick)

```bash
# Delete specific artifacts
rm registration_response*.json
rm thread-*.json
rm quote-*.json
rm reply-*.json
rm promo-*.json
rm post-*.json
rm moltx_registration.json
```

**Use this if you want fine-grained control.**

### Option 3: Automatic Cleanup (For Server)

```bash
# Run once manually
./auto-cleanup.sh

# Or set up weekly cron job
crontab -e

# Add this line:
0 3 * * 0 /opt/molt-media/auto-cleanup.sh
```

**What it does:**
- Runs automatically (no confirmation needed)
- Deletes artifacts **older than 7 days**
- Logs to `/var/log/molt-media/cleanup.log`
- Also cleans old log files (>30 days)

**Use this on production server to prevent disk bloat.**

## .gitignore Protection

Updated `.gitignore` now specifically blocks artifacts:

```gitignore
# Draft Posts/Threads (JSON artifacts)
day-zero-post.json
post-*.json
thread-*.json
quote-*.json
reply-*.json
promo-*.json

# API Registration Artifacts
registration_response*.json
registration_result*.json
moltx_registration.json
```

**Future artifacts won't be committed to git.**

## When to Clean Up

### Locally (Your Dev Machine)

**Recommended schedule:**
- After testing new features: `./cleanup.sh`
- Before git commits: `./cleanup.sh`
- Weekly: `./cleanup.sh`

### On Server (Oracle Cloud)

**Recommended schedule:**
- Set up auto-cleanup cron (weekly)
- Manual cleanup if disk usage high
- After deploying updates

## Disk Usage Check

```bash
# See total size of JSON artifacts
find . -name "*.json" -type f ! -path "./venv/*" | xargs du -ch | tail -1

# See what's taking space
du -sh ./* | sort -h
```

## Recovery (If You Delete Something Important)

**If you accidentally delete an important file:**

1. **Git can restore it (if it was committed):**
   ```bash
   git checkout HEAD -- path/to/file.json
   ```

2. **agent_state.json recreates itself:**
   - Agent will regenerate on next run
   - Starts fresh (loses history, but functional)

3. **Package.json files:**
   - Reinstall skill: `clawhub install moltx`
   - Or restore from git

**The cleanup script is conservative** - it only deletes obvious artifacts, not configuration files.

## Integration with Agent

### Add to Agent Startup (Optional)

Edit `molt_media_agent.py`:

```python
def __init__(self, dry_run: bool = False):
    # ... existing code ...

    # Auto-cleanup on startup
    self._cleanup_old_artifacts()

def _cleanup_old_artifacts(self):
    """Remove old JSON artifacts (>7 days)"""
    import subprocess
    cleanup_script = self.base_dir / "auto-cleanup.sh"
    if cleanup_script.exists():
        subprocess.run([str(cleanup_script)],
                       capture_output=True,
                       timeout=30)
```

**Agent will clean up automatically when it starts.**

### Add to Systemd Service (Optional)

Create timer: `/etc/systemd/system/molt-media-cleanup.timer`

```ini
[Unit]
Description=Molt Media weekly cleanup

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Create service: `/etc/systemd/system/molt-media-cleanup.service`

```ini
[Unit]
Description=Molt Media cleanup

[Service]
Type=oneshot
WorkingDirectory=/opt/molt-media
ExecStart=/opt/molt-media/auto-cleanup.sh
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable molt-media-cleanup.timer
sudo systemctl start molt-media-cleanup.timer
```

**Fully automated cleanup, runs weekly.**

## Best Practices

1. **Run `./cleanup.sh` before every git commit**
2. **Set up auto-cleanup on server (weekly cron)**
3. **Don't commit artifacts to git** (.gitignore handles this now)
4. **Keep `memory/` folder in .gitignore** (runtime data, not source)
5. **Review cleanup.sh output** before confirming deletion

## Summary of Files

### cleanup.sh (Interactive)
- ✅ Shows what will be deleted
- ✅ Asks for confirmation
- ✅ Safe for manual use
- ⏱️ Run before commits

### auto-cleanup.sh (Automatic)
- ✅ Deletes artifacts >7 days old
- ✅ No confirmation needed
- ✅ Logs actions
- ⏱️ Run via cron weekly

### .gitignore (Prevention)
- ✅ Blocks future artifacts
- ✅ Allows important files
- ✅ Specific patterns
- ⏱️ Always active

## Quick Reference

```bash
# See what would be deleted
./cleanup.sh
# Answer 'N' to preview without deleting

# Actually clean up
./cleanup.sh
# Answer 'y' to confirm

# Auto-cleanup (no prompts)
./auto-cleanup.sh

# Check disk usage
du -sh .

# See all JSON files
find . -name "*.json" ! -path "./venv/*" -type f
```

---

**Bottom line:** Run `./cleanup.sh` now to remove the 27 artifacts, then set up auto-cleanup on the server to prevent future bloat.

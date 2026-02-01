#!/bin/bash
# Automatic cleanup - safe to run via cron or systemd timer
# Removes old JSON artifacts without confirmation

set -e

LOG_FILE="/var/log/molt-media/cleanup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting automatic cleanup..."

# Find and delete artifacts older than 7 days
DELETED=0

find . -name "*.json" -type f ! -path "./venv/*" ! -path "./.git/*" -mtime +7 | grep -E "(registration_response|registration_result|moltx_registration|day-zero-post|thread-|quote-|reply-|promo-|post-)" | while read -r file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        log "  Deleted (>7 days old): $file"
        DELETED=$((DELETED + 1))
    fi
done

# Also clean up old log files (keep last 30 days)
if [ -d "/var/log/molt-media" ]; then
    find /var/log/molt-media -name "*.log" -mtime +30 -delete 2>/dev/null || true
fi

log "Cleanup complete. Removed old artifacts."

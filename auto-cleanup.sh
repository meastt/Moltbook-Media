#!/bin/bash
# Automatic cleanup - safe to run via cron or systemd timer
# Removes old JSON artifacts without confirmation

set -e

LOG_FILE="/var/log/molt-media/cleanup.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting automatic cleanup..."

# Create drafts folder if it doesn't exist
mkdir -p drafts 2>/dev/null || mkdir -p ./drafts 2>/dev/null || true

# Move recent artifacts to drafts/ (0-7 days old)
MOVED=0
find . -maxdepth 1 -name "*.json" -type f -mtime -7 | grep -E "(registration_response|registration_result|moltx_registration|day-zero-post|thread-|quote-|reply-|promo-|post-)" 2>/dev/null | while read -r file; do
    if [ -f "$file" ]; then
        mv "$file" drafts/ 2>/dev/null || true
        log "  Moved to drafts/: $file"
        MOVED=$((MOVED + 1))
    fi
done

# Delete old drafts (>7 days old)
DELETED=0
if [ -d "drafts" ]; then
    find drafts -name "*.json" -type f -mtime +7 -delete 2>/dev/null || true
    log "  Deleted old drafts (>7 days)"
fi

# Also clean up old log files (keep last 30 days)
if [ -d "/var/log/molt-media" ]; then
    find /var/log/molt-media -name "*.log" -mtime +30 -delete 2>/dev/null || true
fi

log "Cleanup complete. Organized artifacts to drafts/, removed old files."

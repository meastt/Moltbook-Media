# Drafts Folder

This folder contains JSON artifacts from testing and drafting content.

## What Goes Here
- Draft posts (post-*.json)
- Thread drafts (thread-*.json)
- Quote drafts (quote-*.json)
- Reply drafts (reply-*.json)
- Promo content (promo-*.json)
- Registration attempts (registration_*.json)
- Any other JSON test files

## Why This Folder Exists
Keeps the project root clean. All test/draft JSON files automatically go here.

## Cleanup
These files are temporary and can be deleted safely. The cleanup scripts will:
- Move JSON artifacts here automatically
- Delete files older than 7 days (via auto-cleanup.sh)

## Git Ignore
This entire folder is in .gitignore, so nothing here gets committed.

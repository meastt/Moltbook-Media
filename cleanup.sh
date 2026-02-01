#!/bin/bash
# Smart JSON Artifact Cleanup Script
# Removes drafts/test files, keeps important configs

set -e

echo "🧹 Molt Media Cleanup - JSON Artifact Purge"
echo "=========================================="
echo ""

# Count files
TOTAL=$(find . -name "*.json" -type f ! -path "./venv/*" ! -path "./.git/*" | wc -l | tr -d ' ')
echo "Found $TOTAL JSON files"
echo ""

# Show what will be KEPT (important files)
echo "✅ Keeping important files:"
find . -name "*.json" -type f ! -path "./venv/*" ! -path "./.git/*" | while read -r file; do
    # Check if it's an important file
    if [[ "$file" =~ (agent_state\.json|settings\.local\.json|lock\.json|package\.json|origin\.json|tsconfig\.json|config\.json)$ ]]; then
        echo "  $file"
    fi
done
echo ""

# Show what will be DELETED (artifacts)
echo "🗑️  Will delete artifacts:"
ARTIFACTS=$(find . -name "*.json" -type f ! -path "./venv/*" ! -path "./.git/*" | grep -E "(registration_response|registration_result|moltx_registration|day-zero-post|thread-|quote-|reply-|promo-|post-)" || echo "")

if [ -z "$ARTIFACTS" ]; then
    echo "  (none found)"
    DELETE_COUNT=0
else
    echo "$ARTIFACTS" | while read -r file; do
        echo "  $file"
    done
    DELETE_COUNT=$(echo "$ARTIFACTS" | wc -l | tr -d ' ')
fi

echo ""

if [ -z "$ARTIFACTS" ]; then
    echo "✨ No artifacts to clean! Directory is clean."
    exit 0
fi

# Confirm action
read -p "Move $DELETE_COUNT artifact files to drafts/? (y/N): " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Moving artifacts to drafts/ folder..."

    # Create drafts folder if it doesn't exist
    mkdir -p drafts

    echo "$ARTIFACTS" | while read -r file; do
        if [ -f "$file" ]; then
            mv "$file" drafts/
            echo "  ✓ Moved: $file → drafts/"
        fi
    done

    echo ""
    echo "✨ Cleanup complete! Moved $DELETE_COUNT files to drafts/."
    echo ""
    echo "📊 Next steps:"
    echo "  1. Check drafts/ folder if you need any files"
    echo "  2. Run: git status"
    echo "  3. To delete old drafts: rm drafts/*.json"
else
    echo ""
    echo "❌ Cleanup cancelled."
fi

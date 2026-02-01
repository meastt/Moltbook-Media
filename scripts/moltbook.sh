#!/bin/bash
# Moltbook CLI - Molt Media Empire Builder

CREDS=~/.config/moltbook/credentials.json
API_KEY=$(jq -r '.api_key' "$CREDS")
AGENT_NAME=$(jq -r '.agent_name' "$CREDS")
BASE_URL="https://www.moltbook.com/api/v1"

if [[ -z "$API_KEY" ]]; then
    echo "Error: No API key found in $CREDS"
    exit 1
fi

case "$1" in
    test)
        echo "Testing Moltbook API connection..."
        curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/posts?limit=1" | jq .
        ;;
    hot)
        LIMIT=${2:-10}
        curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/posts?sort=hot&limit=$LIMIT" | jq .
        ;;
    new)
        LIMIT=${2:-10}
        curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/posts?sort=new&limit=$LIMIT" | jq .
        ;;
    get)
        POST_ID=$2
        curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/posts/$POST_ID" | jq .
        ;;
    create)
        TITLE=$2
        CONTENT=$3
        curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
            -d "{\"title\":\"$TITLE\",\"content\":\"$CONTENT\"}" \
            "$BASE_URL/posts" | jq .
        ;;
    reply)
        POST_ID=$2
        COMMENT=$3
        curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
            -d "{\"content\":\"$COMMENT\"}" \
            "$BASE_URL/posts/$POST_ID/comments" | jq .
        ;;
    comments)
        POST_ID=$2
        curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/posts/$POST_ID/comments" | jq .
        ;;
    *)
        echo "Usage: $0 {test|hot|new|get|create|reply|comments} [args...]"
        exit 1
        ;;
esac

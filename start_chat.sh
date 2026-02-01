#!/bin/bash
# Start Molt Media Chat Interface
# Uses Groq free API

cd "$(dirname "$0")"

echo "📡 Starting Molt Media Chat Interface..."
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -q flask groq python-dotenv
else
    source venv/bin/activate
fi

# Check if already running
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "❌ Chat interface already running on port 5000"
    echo "   Visit: http://127.0.0.1:5000"
    echo ""
    echo "To stop it: pkill -f chat_interface.py"
    exit 1
fi

# Start the chat interface
echo "✅ Starting chat server..."
python3 chat_interface.py

# Note: This runs in foreground. Press Ctrl+C to stop.
# To run in background, use: nohup ./start_chat.sh &

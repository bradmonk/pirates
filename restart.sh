#!/bin/bash
# Restart script for the pirate game

# Source bash profile to ensure environment is loaded
source ~/.bash_profile

echo "🔄 Cleaning up previous instances..."

# Kill any Python processes running our game files
echo "  - Stopping pirate game processes..."
pkill -f "python.*pirate_game.py" 2>/dev/null || true
pkill -f "python.*ai_agents.py" 2>/dev/null || true
pkill -f "python.*test_verbose_game.py" 2>/dev/null || true

# Kill any Python processes that might have matplotlib/GUI windows open
echo "  - Stopping Python processes with GUI windows..."
pkill -f "python.*gui_display" 2>/dev/null || true
pgrep -f "python" | while read pid; do
    # Check if the process has any GUI/window connections
    lsof -p "$pid" 2>/dev/null | grep -q "WindowServer\|CoreGraphics" && kill "$pid" 2>/dev/null || true
done

# Also kill any orphaned matplotlib backends
pkill -f "matplotlib" 2>/dev/null || true
pkill -f "backend" 2>/dev/null || true

# Kill any processes using port 8000 (our web server)
echo "  - Stopping web servers on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

echo "  ✅ Cleanup complete"

echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Verify ollama is available
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Warning: ollama not found in PATH"
    echo "PATH: $PATH"
else
    echo "✅ Ollama found at: $(which ollama)"
fi

echo "🏴‍☠️ Starting pirate game..."
python pirate_game.py
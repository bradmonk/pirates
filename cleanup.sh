#!/bin/bash
# Cleanup script to forcefully close Python processes and GUI windows

echo "🧹 Force cleaning up Python processes and GUI windows..."

# Kill all Python processes in this project directory
echo "  - Killing Python processes in project directory..."
for pid in $(pgrep -f "python"); do
    if [ -n "$pid" ]; then
        cwd=$(pwdx "$pid" 2>/dev/null | awk '{print $2}' || echo "")
        if [[ "$cwd" == *"pirates"* ]]; then
            echo "    Killing Python process $pid in $cwd"
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi
done

# Force kill any matplotlib/GUI processes
echo "  - Force closing GUI processes..."
pkill -9 -f "matplotlib" 2>/dev/null || true
pkill -9 -f "backend" 2>/dev/null || true
pkill -9 -f "gui_display" 2>/dev/null || true

# Use AppleScript to close any Python GUI windows
echo "  - Closing Python application windows..."
osascript -e '
tell application "System Events"
    set allProcesses to (every process)
    repeat with proc in allProcesses
        set procName to name of proc as string
        if procName contains "Python" or procName contains "python" then
            try
                tell proc
                    set frontmost to true
                    delay 0.1
                    close (every window)
                end tell
                delay 0.1
            end try
        end if
    end repeat
end tell
' 2>/dev/null || true

# Kill any remaining Python processes that might have GUI windows
echo "  - Final cleanup of GUI-connected Python processes..."
for pid in $(pgrep python); do
    if lsof -p "$pid" 2>/dev/null | grep -q "WindowServer\|CoreGraphics\|AppKit"; then
        echo "    Force killing GUI Python process: $pid"
        kill -9 "$pid" 2>/dev/null || true
    fi
done

echo "✅ Cleanup complete - all Python GUI processes should be closed"
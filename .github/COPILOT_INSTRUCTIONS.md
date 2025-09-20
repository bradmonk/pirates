# Copilot Instructions for Pirate Game Project

## Development Workflow

### Starting/Restarting the Game
- **ALWAYS use `./restart.sh`** to start or restart the pirate game
- This script handles proper cleanup and initialization
- Never manually run `python pirate_game.py` directly
- The restart script ensures clean state and proper port management

### Testing Changes
1. Make your code changes
2. Run `./restart.sh` to test
3. Wait for the server to start (look for "Open http://localhost:8000" message)
4. Test functionality in browser at `http://localhost:8000`
5. Confirm changes work before making additional modifications

### Port Management
- The game uses port 8000 for the web interface
- The restart script automatically handles port conflicts
- If port issues occur, the restart script will clean them up

### Process Management
- Always use the restart script rather than killing processes manually
- The script handles proper cleanup of background processes
- If you need to stop the game, use Ctrl+C and then run `./restart.sh` for the next test

### Development Best Practices
- Always activate the Python virtual environment (handled by restart script)
- Use `python` command, never `python3` (to ensure virtual environment usage)
- Run commands from the project root directory
- Kill running processes before starting new ones to avoid port conflicts
- Use the provided restart script for consistent development workflow
- Wait for user confirmation that changes work before proceeding to next task
- Do not launch browser automatically - let user test manually
- Check for existing code before adding new functionality to avoid duplication
- Update DEVELOPMENT.md file when making significant changes
- Remember this is ARM64 architecture - use appropriate packages

### Key Commands
- `./restart.sh` - Start/restart the game (primary command)
- `http://localhost:8000` - Access the web interface
- Ctrl+C - Stop the running game process

### Chrome DevTools Integration
- Chrome DevTools workspace is configured for live editing
- Edit HTML/CSS directly in browser Sources panel
- Changes automatically save to project files
- Use F12 to open DevTools, then Sources tab

## Remember
**When the user asks to test changes or run the game, ALWAYS use `./restart.sh`**
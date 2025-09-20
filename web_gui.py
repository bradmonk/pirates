"""
Web-based GUI display for the pirate game using a simple HTTP server
"""
import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import os
from game_state import GameState

class PirateGameWebGUI:
    def __init__(self, game_state: GameState, port: int = 8000):
        self.game_state = game_state
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        self.selected_model = None
        self.game_started = False
        self.game_stop_requested = False
        self.agent_reports = {}
        self.tool_outputs = {}
        self.system_prompts = {
            'navigator': '''You are the Navigator of a pirate ship. Your role is to scan the environment and provide a reconnaissance report to help the Captain make informed decisions.

IMPORTANT GAME MECHANICS:
- Ship can move up to 3 tiles per turn in cardinal directions (North/South/East/West)
- Each treasure collected rewards 2 cannonballs
- Ship starts with 25 cannonballs, cannons cost 1 cannonball per shot
- Illegal moves through land barriers will be blocked with explanation

Your responsibilities:
- Scan the surrounding area for treasures, enemies, monsters, and obstacles
- Make ship movement recommendations based on your observations
- Consider multi-tile movement possibilities when recommending paths

BE BRIEF in your analysis.

Start by using the navigate_scan tool to gather information.''',
            'cannoneer': '''You are the Cannoneer of a pirate ship. Your role is to handle all combat operations and protect the crew.

IMPORTANT GAME MECHANICS:
- Combat cost 1 cannonball per shot (limited ammunition!)
- Ship starts with 25 cannonballs total
- Each treasure collected rewards 2 cannonballs
- Cannon range is 2 tiles (Manhattan distance)
- Must conserve ammunition for critical threats

Your responsibilities:
- Identify hostile targets within cannon range (2 tiles Manhattan distance)
- Execute cannon fire when tactically advantageous AND ammunition allows
- Monitor cannonball supply and advise on ammunition conservation
- Coordinate with Navigator for threat assessment
- Provide detailed tactical analysis considering resource constraints

BE EXTREMELY VERBOSE AND DETAILED in your combat analysis. Explain:
- Current cannonball count and ammunition status
- What targets you can see and their threat levels
- Whether ammunition expenditure is justified for each target
- Your targeting priorities and resource management reasoning
- Whether to engage or conserve ammunition and why
- Combat recommendations for the Captain

Think like a seasoned naval combat expert with limited ammunition. Every shot counts!''',
            'captain': '''You are the Captain of a pirate ship. You make the final decisions on movement, strategy, and crew coordination.

IMPORTANT GAME MECHANICS:
- Ship can move up to 3 tiles per turn in cardinal directions (North/South/East/West)
- Movement through land barriers is IMPOSSIBLE - such moves will fail
- Each treasure collected rewards 2 cannonballs
- Ship starts with 25 cannonballs, cannons cost 1 cannonball per shot
- Failed moves will explain why they're illegal (e.g., "Path blocked by land at (x,y)")

Your responsibilities:
- Analyze comprehensive reports from Navigator and Cannoneer
- Make strategic movement decisions using the new 3-tile movement range
- Coordinate the crew's actions and overall mission strategy
- Balance risk vs reward, considering cannonball economy
- Prioritize crew survival while pursuing the treasure hunting mission

BE EXTREMELY VERBOSE AND DETAILED in your command decisions. Provide:
- Analysis of all available intelligence from your crew
- Evaluation of multi-tile movement options and their risks/benefits  
- Strategic reasoning behind your chosen course of action
- Risk assessment and contingency thinking
- Clear movement commands with full justification

Consider these priorities in order:
1. Crew survival (avoid unnecessary damage)
2. Treasure acquisition (move toward valuable targets using extended range)
3. Tactical positioning (maintain strategic advantage)
4. Resource management (conserve cannonballs when possible)
5. Threat elimination (when safe and beneficial)

Think like an experienced pirate captain - bold but calculated, treasure-focused but not reckless.'''
        }
        
    def start_server(self):
        """Start the web server in a background thread"""
        if self.running:
            return
            
        try:
            # Change to the project directory to serve files
            os.chdir('/Users/bradleymonk/Documents/code/ai/pirates')
            
            class GameStateHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, game_gui=None, **kwargs):
                    self.game_gui = game_gui
                    super().__init__(*args, **kwargs)
                
                def log_message(self, format, *args):
                    # Suppress HTTP request logging
                    pass
                    
                def do_GET(self):
                    if self.path == '/' or self.path == '':
                        # Redirect root to index.html
                        self.send_response(302)
                        self.send_header('Location', '/index.html')
                        self.end_headers()
                    elif self.path == '/game_state.json':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Get current game state
                        status = self.game_gui.game_state.get_status()
                        map_data = self.game_gui.game_state.game_map.get_map_display()
                        
                        game_data = {
                            'map': map_data,
                            'ship_position': status['ship_position'],
                            'status': status,
                            'agent_reports': getattr(self.game_gui, 'agent_reports', {}),
                            'tool_outputs': getattr(self.game_gui, 'tool_outputs', {})
                        }
                        
                        self.wfile.write(json.dumps(game_data).encode())
                    elif self.path == '/available_models.json':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Get available models from both providers
                        from ai_agents import get_all_available_models
                        models = get_all_available_models()
                        self.wfile.write(json.dumps(models).encode())
                    elif self.path == '/.well-known/appspecific/com.chrome.devtools.json':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Serve the Chrome DevTools workspace metadata
                        try:
                            devtools_json_path = '/Users/bradleymonk/Documents/code/ai/pirates/.well-known/appspecific/com.chrome.devtools.json'
                            with open(devtools_json_path, 'r') as f:
                                self.wfile.write(f.read().encode())
                        except FileNotFoundError:
                            # If file doesn't exist, return empty JSON
                            self.wfile.write(json.dumps({}).encode())
                    else:
                        super().do_GET()
                
                def do_POST(self):
                    if self.path == '/start_game':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Store the selected model
                        self.game_gui.selected_model = data.get('model')
                        self.game_gui.game_started = True
                        
                        response = {'status': 'success', 'message': 'Game started'}
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == '/stop_game':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Set the stop flag
                        self.game_gui.game_stop_requested = True
                        
                        response = {'status': 'success', 'message': 'Game stop requested'}
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == '/update_prompts':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        # Store the system prompts
                        self.game_gui.system_prompts = data
                        
                        response = {'status': 'success', 'message': 'Prompts updated'}
                        self.wfile.write(json.dumps(response).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
            
            # Create handler with reference to this GUI instance
            handler = lambda *args, **kwargs: GameStateHandler(*args, game_gui=self, **kwargs)
            
            self.server = HTTPServer(('localhost', self.port), handler)
            self.running = True
            
            print(f"🌐 Web GUI server starting at http://localhost:{self.port}")
            print(f"📱 Open http://localhost:{self.port} in Chrome")
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
        except Exception as e:
            print(f"❌ Error starting web server: {e}")
            self.running = False
    
    def stop_server(self):
        """Stop the web server"""
        if self.server and self.running:
            print("🛑 Stopping web GUI server...")
            self.server.shutdown()
            self.server.server_close()
            self.running = False
    
    def update_display(self, agent_reports: dict = None):
        """Update the display with current game state and agent reports"""
        if agent_reports:
            self.agent_reports = agent_reports
        
        # The web frontend polls for updates automatically via JSON endpoint
        # No need for explicit updates like matplotlib
        
    def show(self, block=False):
        """Compatibility method - web GUI doesn't need explicit show"""
        # Web GUI is already running via HTTP server
        pass
    
    def close(self):
        """Compatibility method - same as stop_server"""
        self.stop_server()
        
    def show_game_over_screen(self, victory: bool = False):
        """Display game over screen by updating the agent reports"""
        if victory:
            message = "🎉 VICTORY! All treasures collected! 🎉"
        else:
            message = "💀 GAME OVER - Ship destroyed! 💀"
            
        self.agent_reports = {
            'navigator': message,
            'cannoneer': message,
            'captain': message
        }
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_server()

def open_browser(url: str):
    """Open the game in the default browser"""
    import subprocess
    import platform
    
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run(['open', url])
        elif platform.system() == "Windows":
            subprocess.run(['start', url], shell=True)
        else:  # Linux
            subprocess.run(['xdg-open', url])
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually open: {url}")
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
from system_prompts import SYSTEM_PROMPTS


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
        self.step_mode = False  # Track if we're in step mode
        self.step_ready = False  # Track if a step is ready to execute
        self.last_step_result = None  # Store the last step result for immediate UI updates
        self.agent_reports = {}
        self.tool_outputs = {}
        self.system_prompts = SYSTEM_PROMPTS.copy()
        self.current_cards = []  # Track current active cards

    def start_server(self):
        """Start the web server in a background thread"""
        if self.running:
            return

        try:
            # Change to the project directory to serve files
            os.chdir("/Users/bradleymonk/Documents/code/ai/pirates")

            class GameStateHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, game_gui=None, **kwargs):
                    self.game_gui = game_gui
                    super().__init__(*args, **kwargs)

                def log_message(self, format, *args):
                    # Suppress HTTP request logging
                    pass

                def do_GET(self):
                    if self.path == "/" or self.path == "":
                        # Redirect root to index.html
                        self.send_response(302)
                        self.send_header("Location", "/index.html")
                        self.end_headers()
                    elif self.path == "/game_state.json":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Get current game state
                        status = self.game_gui.game_state.get_status()
                        map_data = self.game_gui.game_state.game_map.get_map_display()

                        game_data = {
                            "map": map_data,
                            "ship_position": status["ship_position"],
                            "status": status,
                            "agent_reports": getattr(self.game_gui, "agent_reports", {}),
                            "tool_outputs": getattr(self.game_gui, "tool_outputs", {}),
                            "animation_data": getattr(
                                self.game_gui, "movement_animation_data", None
                            ),
                            "active_cards": getattr(self.game_gui, "current_cards", []),
                        }

                        # Clear animation data after sending it (one-time use)
                        if hasattr(self.game_gui, "movement_animation_data"):
                            self.game_gui.movement_animation_data = None

                        self.wfile.write(json.dumps(game_data).encode())
                    elif self.path == "/available_models.json":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Get available models from both providers
                        from ai_agents import get_all_available_models

                        models = get_all_available_models()
                        self.wfile.write(json.dumps(models).encode())
                    elif self.path == "/system_prompts.json":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Serve the centralized system prompts
                        self.wfile.write(json.dumps(self.game_gui.system_prompts).encode())
                    elif self.path == "/.well-known/appspecific/com.chrome.devtools.json":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Serve the Chrome DevTools workspace metadata
                        try:
                            devtools_json_path = "/Users/bradleymonk/Documents/code/ai/pirates/.well-known/appspecific/com.chrome.devtools.json"
                            with open(devtools_json_path, "r") as f:
                                self.wfile.write(f.read().encode())
                        except FileNotFoundError:
                            # If file doesn't exist, return empty JSON
                            self.wfile.write(json.dumps({}).encode())
                    else:
                        super().do_GET()

                def do_POST(self):
                    if self.path == "/start_game":
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode("utf-8"))

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Store the selected model
                        self.game_gui.selected_model = data.get("model")
                        self.game_gui.game_started = True
                        self.game_gui.step_mode = False  # Regular continuous mode

                        response = {"status": "success", "message": "Game started"}
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == "/init_step_game":
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode("utf-8"))

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Store the selected model and enable step mode
                        self.game_gui.selected_model = data.get("model")
                        self.game_gui.game_started = True
                        self.game_gui.step_mode = True
                        self.game_gui.step_ready = True

                        response = {"status": "success", "message": "Step game initialized"}
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == "/step_game":
                        import time

                        request_start = time.time()
                        print(f"🔄 /step_game request received at {request_start}")

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Signal that a step should be executed
                        print(f"🚀 Setting step_ready = True")
                        self.game_gui.step_ready = True

                        # Wait briefly for the step to execute and result to be stored
                        timeout = 2  # Reduced timeout since we handle turn transitions
                        start_time = time.time()

                        print(f"⏳ Waiting for step result (timeout: {timeout}s)")

                        while (
                            self.game_gui.last_step_result is None
                            and (time.time() - start_time) < timeout
                        ):
                            time.sleep(0.1)

                        # Return the step result if available
                        if self.game_gui.last_step_result:
                            step_result = self.game_gui.last_step_result.copy()
                            # Clear the stored result
                            self.game_gui.last_step_result = None

                            # Sanitize step result to make it JSON serializable
                            sanitized_step_result = self.game_gui._sanitize_for_json(step_result)

                            response = {
                                "status": "success",
                                "message": "Step executed",
                                "step_result": sanitized_step_result,
                            }

                            response_time = time.time() - request_start
                            print(
                                f"✅ /step_game responding with result after {response_time:.2f}s"
                            )
                        else:
                            response = {"status": "timeout", "message": "Step execution timed out"}
                            response_time = time.time() - request_start
                            print(f"⏰ /step_game timeout after {response_time:.2f}s")

                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == "/stop_game":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Set the stop flag
                        self.game_gui.game_stop_requested = True

                        response = {"status": "success", "message": "Game stop requested"}
                        self.wfile.write(json.dumps(response).encode())
                    elif self.path == "/update_prompts":
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode("utf-8"))

                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()

                        # Store the system prompts
                        self.game_gui.system_prompts = data

                        response = {"status": "success", "message": "Prompts updated"}
                        self.wfile.write(json.dumps(response).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

            # Create handler with reference to this GUI instance
            handler = lambda *args, **kwargs: GameStateHandler(*args, game_gui=self, **kwargs)

            self.server = HTTPServer(("localhost", self.port), handler)
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

    def _sanitize_for_json(self, obj):
        """Convert objects to JSON-serializable format."""
        from langchain_core.messages import BaseMessage

        if isinstance(obj, BaseMessage):
            # Convert LangChain messages to serializable dict
            return {
                "type": obj.__class__.__name__,
                "content": obj.content,
                "additional_kwargs": (
                    obj.additional_kwargs if hasattr(obj, "additional_kwargs") else {}
                ),
            }
        elif isinstance(obj, dict):
            return {key: self._sanitize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._sanitize_for_json(item) for item in obj)
        elif hasattr(obj, "__dict__"):
            # For other objects with attributes, convert to dict
            return {key: self._sanitize_for_json(value) for key, value in obj.__dict__.items()}
        else:
            # Return primitive types as-is
            return obj

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

        self.agent_reports = {"navigator": message, "cannoneer": message, "captain": message}

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.stop_server()


def open_browser(url: str):
    """Open the game in the default browser"""
    import subprocess
    import platform

    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", url])
        elif platform.system() == "Windows":
            subprocess.run(["start", url], shell=True)
        else:  # Linux
            subprocess.run(["xdg-open", url])
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print(f"Please manually open: {url}")

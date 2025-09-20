"""
Pirate Game - AI Agents using LangGraph with Ollama and OpenAI
"""
import subprocess
import json
import os
from typing import Dict, List, Any, Optional
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from game_state import GameState
from game_tools import GameTools

class GameAgentState(TypedDict):
    """State shared between all agents"""
    messages: List[Any]
    game_status: Dict[str, Any]
    last_action: Optional[str]
    agent_reports: Dict[str, str]
    decision: Optional[str]

def get_available_models() -> List[str]:
    """Get list of available Ollama models"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = []
        for line in lines:
            if line.strip():
                model_name = line.split()[0]
                models.append(model_name)
        return models
    except Exception as e:
        print(f"Error getting Ollama models: {e}")
        return []

def get_openai_models() -> List[str]:
    """Get list of available OpenAI models"""
    # Common OpenAI models that work well for this application
    return [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo"
    ]

def is_openai_model(model_name: str) -> bool:
    """Check if model is an OpenAI model"""
    return model_name in get_openai_models()

def get_all_available_models() -> Dict[str, List[str]]:
    """Get all available models grouped by provider"""
    models = {
        'ollama': get_available_models(),
        'openai': get_openai_models() if os.getenv("OPENAI_API_KEY") else []
    }
    return models

def select_model() -> str:
    """Let user select which Ollama model to use"""
    models = get_available_models()
    if not models:
        print("No Ollama models found. Please install a model first.")
        print("Example: ollama pull llama3.2")
        return None
    
    print("\\n=== Available Ollama Models ===")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")
    
    while True:
        try:
            choice = input(f"\\nSelect model (1-{len(models)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                print(f"Selected: {selected}")
                return selected
            else:
                print("Invalid choice, please try again.")
        except (ValueError, KeyboardInterrupt):
            print("\\nExiting...")
            return None

class PirateGameAgents:
    """Container for all game agents"""
    
    def __init__(self, game_state: GameState, model_name: str, use_openai: bool = False, system_prompts: Dict[str, str] = None, web_gui=None):
        self.game_state = game_state
        self.game_tools = GameTools(game_state)
        self.model_name = model_name
        self.use_openai = use_openai
        self.web_gui = web_gui
        
        # Set default system prompts if none provided
        self.system_prompts = system_prompts or {
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
        
        # Initialize the appropriate language model
        if use_openai:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key not found in environment variables")
            print(f"🤖 Initializing OpenAI model: {model_name}")
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.7,
                max_tokens=2000
            )
        else:
            print(f"🤖 Initializing Ollama model: {model_name}")
            self.llm = ChatOllama(
                model=model_name,
                temperature=0.7,
                verbose=True,  # Enable verbose output
                # Remove format="json" to allow more natural language responses
            )
        
        # Create tools for LangGraph
        self.setup_tools()
        
        # Create the agent graph
        self.setup_agent_graph()
    
    def update_system_prompts(self, new_prompts: Dict[str, str]):
        """Update the system prompts used by the agents"""
        self.system_prompts.update(new_prompts)
        print(f"🔄 Updated system prompts for: {', '.join(new_prompts.keys())}")
    
    def setup_tools(self):
        """Setup tools that agents can use"""
        
        @tool
        def navigate_scan(radius: int = 3) -> Dict[str, Any]:
            """Scan the environment around the ship for treasures, enemies, and obstacles."""
            return self.game_tools.navigator.scan_surroundings(radius)
        
        @tool
        def get_cannon_targets() -> List[Dict[str, Any]]:
            """Get all hostile targets within cannon range."""
            return self.game_tools.cannoneer.get_targets_in_range()
        
        @tool
        def fire_cannon(target_x: int, target_y: int) -> Dict[str, Any]:
            """Fire cannon at specified coordinates. Costs 1 cannonball. Range: 2 tiles."""
            return self.game_tools.cannoneer.fire_cannon(target_x, target_y)
        
        @tool
        def get_possible_moves() -> List[Dict[str, Any]]:
            """Get all possible moves from current position. Ship can move up to 3 tiles per turn in cardinal directions."""
            return self.game_tools.captain.get_possible_moves()
        
        @tool
        def move_ship(direction_x: int, direction_y: int) -> Dict[str, Any]:
            """Move the ship up to 3 tiles in cardinal directions. Illegal moves through land will fail with explanation."""
            return self.game_tools.captain.move_ship(direction_x, direction_y)
        
        @tool
        def get_game_status() -> Dict[str, Any]:
            """Get comprehensive game status including position, lives, treasures, cannonballs, etc."""
            return self.game_tools.get_game_status()
        
        self.tools = [navigate_scan, get_cannon_targets, fire_cannon, get_possible_moves, move_ship, get_game_status]
    
    def setup_agent_graph(self):
        """Setup the LangGraph agent workflow"""
        
        # Create tool node
        tool_node = ToolNode(self.tools)
        
        def navigator_agent(state: GameAgentState) -> GameAgentState:
            """Navigator agent - scans environment and reports findings"""
            system_message = SystemMessage(content=self.system_prompts['navigator'])
            
            print("\\n🧭 NAVIGATOR: Beginning environmental scan...")
            
            # Get current game status first
            status = self.game_tools.get_game_status()
            scan_result = self.game_tools.navigator.scan_surroundings(radius=3)
            
            print(f"🧭 NAVIGATOR: Scan complete. Found {len(scan_result['treasures_nearby'])} treasures, {len(scan_result['enemies_nearby'])} enemies, {len(scan_result['monsters_nearby'])} monsters in area.")
            
            # Update web GUI with scan result
            if self.web_gui:
                scan_summary = f"Radius: {scan_result['scan_radius']} tiles\\n"
                scan_summary += f"Treasures: {len(scan_result['treasures_nearby'])}\\n"
                scan_summary += f"Enemies: {len(scan_result['enemies_nearby'])}\\n"
                scan_summary += f"Monsters: {len(scan_result['monsters_nearby'])}\\n"
                scan_summary += f"Immediate threats: {len(scan_result['immediate_threats'])}"
                self.web_gui.tool_outputs["scan"] = scan_summary
            
            # Create detailed context for the AI
            context = f"""
            CURRENT SITUATION ANALYSIS:
            Ship Position: {status['ship_position']}
            Lives Remaining: {status['lives']}/3
            Treasures Collected: {status['treasures_collected']}/{status['total_treasures']}
            Cannonballs Remaining: {status['cannonballs']}
            Turn Number: {status['turn_count']}
            
            SCAN RESULTS:
            - Scan Radius: {scan_result['scan_radius']} tiles
            - Treasures in area: {len(scan_result['treasures_nearby'])}
            - Enemies in area: {len(scan_result['enemies_nearby'])}  
            - Monsters in area: {len(scan_result['monsters_nearby'])}
            - Immediate threats (within 1 tile): {len(scan_result['immediate_threats'])}
            - Reachable treasures (within 2 tiles): {len(scan_result['reachable_treasures'])}
            
            DETAILED FINDINGS:
            Treasures: {scan_result['treasures_nearby']}
            Enemies: {scan_result['enemies_nearby']}
            Monsters: {scan_result['monsters_nearby']}
            Immediate Threats: {scan_result['immediate_threats']}
            """
            
            messages = [system_message] + state["messages"] + [
                HumanMessage(content=f"Navigator, provide a comprehensive analysis of our current situation and surroundings: {context}")
            ]
            
            print("🧭 NAVIGATOR: Analyzing tactical situation...")
            response = self.llm.invoke(messages)
            print(f"🧭 NAVIGATOR REPORT:\\n{response.content}\\n")
            
            state["agent_reports"]["navigator"] = response.content
            state["messages"].append(response)
            
            # Update web GUI with navigator response
            if self.web_gui:
                self.web_gui.agent_reports["navigator"] = response.content
            
            return state
        
        def cannoneer_agent(state: GameAgentState) -> GameAgentState:
            """Cannoneer agent - handles combat and targeting"""
            system_message = SystemMessage(content=self.system_prompts['cannoneer'])
            
            print("\\n⚔️  CANNONEER: Assessing combat situation...")
            
            # Get available targets
            targets = self.game_tools.cannoneer.get_targets_in_range()
            navigator_report = state["agent_reports"].get("navigator", "No navigator report available")
            
            print(f"⚔️  CANNONEER: {len(targets)} hostile targets within cannon range")
            for i, target in enumerate(targets):
                print(f"⚔️  CANNONEER: Target {i+1}: {target['type']} at {target['position']} - {target['threat_level']} threat level")
            
            combat_context = f"""
            COMBAT SITUATION ANALYSIS:
            Available Targets: {targets}
            Navigator Intelligence: {navigator_report}
            
            TACTICAL CONSIDERATIONS:
            - Cannon range: 2 tiles (Manhattan distance)
            - Monster threat level: High (more dangerous)
            - Enemy threat level: Medium  
            - Each shot should be carefully considered
            - Coordinate with movement plans
            """
            
            messages = [system_message] + state["messages"] + [
                HumanMessage(content=f"Cannoneer, analyze the combat situation and decide on actions: {combat_context}")
            ]
            
            print("⚔️  CANNONEER: Formulating combat strategy...")
            response = self.llm.invoke(messages)
            print(f"⚔️  CANNONEER TACTICAL ANALYSIS:\\n{response.content}\\n")
            
            # If there are targets and the cannoneer decides to fire, execute it
            if targets and "fire" in response.content.lower():
                print("⚔️  CANNONEER: Attempting to engage targets...")
                for target in targets:
                    result = self.game_tools.cannoneer.fire_cannon(target['position'][0], target['position'][1])
                    print(f"⚔️  CANNONEER: {result['message']}")
                    
                    # Update web GUI with fire cannon result
                    if self.web_gui:
                        self.web_gui.tool_outputs["fire_cannon"] = f"Target: {target['position']} - {result['message']}"
                    
                    if result['success']:
                        break  # Only fire once per turn
            
            state["agent_reports"]["cannoneer"] = response.content
            state["messages"].append(response)
            
            # Update web GUI with cannoneer response
            if self.web_gui:
                self.web_gui.agent_reports["cannoneer"] = response.content
            
            return state
        
        def captain_agent(state: GameAgentState) -> GameAgentState:
            """Captain agent - makes movement decisions and overall strategy"""
            system_message = SystemMessage(content=self.system_prompts['captain'])
            
            print("CAPTAIN: Receiving crew reports and formulating strategy...")
            
            navigator_report = state["agent_reports"].get("navigator", "Navigator report not available")
            cannoneer_report = state["agent_reports"].get("cannoneer", "Cannoneer report not available") 
            
            # Get movement options
            possible_moves = self.game_tools.captain.get_possible_moves()
            current_status = self.game_tools.get_game_status()
            
            print("👨‍✈️ CAPTAIN: Analyzing available movement options...")
            for i, move in enumerate(possible_moves):
                risk_color = "🟢" if "Safe" in move['risk_assessment'] else "🟡" if "Rewarding" in move['risk_assessment'] else "🔴"
                target_pos = move.get('target_position', 'unknown')
                print(f"👨‍✈️ CAPTAIN: Option {i+1}: {move['direction_name']} to {target_pos} {risk_color} {move['risk_assessment']}")
            
            strategic_context = f"""
            COMMAND SITUATION BRIEFING:
            Current Position: {current_status['ship_position']}
            Lives: {current_status['lives']}/3
            Treasures: {current_status['treasures_collected']}/{current_status['total_treasures']}  
            Mission Progress: {(current_status['treasures_collected']/current_status['total_treasures']*100):.1f}% complete
            
            CREW INTELLIGENCE REPORTS:
            Navigator Report: {navigator_report}
            
            Cannoneer Report: {cannoneer_report}
            
            MOVEMENT OPTIONS ANALYSIS:
            {chr(10).join([f"- {move['direction_name']}: {move['risk_assessment']} (to {move.get('target_position', 'unknown')})" for move in possible_moves if move['can_move']])}
            
            STRATEGIC OBJECTIVES:
            - Primary: Collect all {current_status['total_treasures']} treasures  
            - Secondary: Preserve crew lives ({current_status['lives']} remaining)
            - Tactical: Maintain operational advantage
            """
            
            messages = [system_message] + state["messages"] + [
                HumanMessage(content=f"Captain, make your strategic decision based on all available intelligence: {strategic_context}")
            ]
            
            print("👨‍✈️ CAPTAIN: Deliberating on best course of action...")
            response = self.llm.invoke(messages)
            print(f"👨‍✈️ CAPTAIN'S STRATEGIC DECISION:\\n{response.content}\\n")
            
            # Parse the captain's decision and execute movement
            print("👨‍✈️ CAPTAIN: Executing movement order...")
            
            # Try to extract movement direction from the response
            # Look for direction keywords in the response
            direction_map = {
                'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0),
                'northeast': (1, -1), 'northwest': (-1, -1), 'southeast': (1, 1), 'southwest': (-1, 1),
                'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)
            }
            
            chosen_direction = None
            response_lower = response.content.lower()
            
            # Find the first mentioned direction in the response
            for direction_name, direction_vector in direction_map.items():
                if direction_name in response_lower:
                    chosen_direction = direction_vector
                    print(f"👨‍✈️ CAPTAIN: Parsed movement command: {direction_name} {direction_vector}")
                    break
            
            # If no direction found, choose the first safe move
            if not chosen_direction:
                safe_moves = [m for m in possible_moves if m['can_move'] and 'Safe' in m['risk_assessment']]
                if safe_moves:
                    chosen_direction = safe_moves[0]['direction']
                    print(f"👨‍✈️ CAPTAIN: Defaulting to safe movement: {safe_moves[0]['direction_name']}")
                elif possible_moves:
                    # Choose any valid move if no safe moves
                    valid_moves = [m for m in possible_moves if m['can_move']]
                    if valid_moves:
                        chosen_direction = valid_moves[0]['direction'] 
                        print(f"👨‍✈️ CAPTAIN: No safe moves available, taking calculated risk: {valid_moves[0]['direction_name']}")
            
            # Execute the movement
            if chosen_direction:
                move_result = self.game_tools.captain.move_ship(chosen_direction[0], chosen_direction[1])
                print(f"👨‍✈️ CAPTAIN: Movement result - {move_result['message']}")
                
                # Update web GUI with movement result
                if self.web_gui:
                    direction_name = "Unknown"
                    for move in possible_moves:
                        if move['direction'] == chosen_direction:
                            direction_name = move['direction_name']
                            break
                    self.web_gui.tool_outputs["move"] = f"Direction: {direction_name} - {move_result['message']}"
            else:
                print("👨‍✈️ CAPTAIN: No valid moves available - holding position!")
                # Update web GUI with no movement
                if self.web_gui:
                    self.web_gui.tool_outputs["move"] = "No valid moves available - holding position"
            
            state["agent_reports"]["captain"] = response.content
            state["decision"] = response.content
            state["messages"].append(response)
            
            # Update web GUI with captain response
            if self.web_gui:
                self.web_gui.agent_reports["captain"] = response.content
            
            return state
        
        # Build the graph
        workflow = StateGraph(GameAgentState)
        
        # Add nodes
        workflow.add_node("navigator", navigator_agent)
        workflow.add_node("cannoneer", cannoneer_agent)
        workflow.add_node("captain", captain_agent)
        workflow.add_node("tools", tool_node)
        
        # Add edges
        workflow.set_entry_point("navigator")
        workflow.add_edge("navigator", "cannoneer")
        workflow.add_edge("cannoneer", "captain")
        workflow.add_edge("captain", END)
        
        self.graph = workflow.compile()
    
    def run_turn(self) -> GameAgentState:
        """Run one turn of the game with all agents"""
        initial_state = GameAgentState(
            messages=[],
            game_status=self.game_tools.get_game_status(),
            last_action=None,
            agent_reports={},
            decision=None
        )
        
        # Execute the agent workflow
        final_state = self.graph.invoke(initial_state)
        
        return final_state

def test_agents():
    """Test function to demonstrate the agents"""
    print("=== Testing Pirate Game Agents ===")
    
    # Select model
    model_name = select_model()
    if not model_name:
        return
    
    # Determine if it's OpenAI model
    use_openai = is_openai_model(model_name)
    print(f"Using {'OpenAI' if use_openai else 'Ollama'} model: {model_name}")
    
    # Initialize game
    game_state = GameState()
    agents = PirateGameAgents(game_state, model_name, use_openai)
    
    print("\\n=== Initial Game State ===")
    game_state.display_map()
    
    # Run a few turns
    for turn in range(3):
        print(f"\\n=== TURN {turn + 1} ===")
        
        try:
            result = agents.run_turn()
            
            print("\\n--- Agent Reports ---")
            for agent_name, report in result["agent_reports"].items():
                print(f"{agent_name.upper()}: {report}")
            
            print("\\n--- Updated Game State ---")
            game_state.display_map()
            
            if game_state.game_over:
                if game_state.victory:
                    print("🎉 VICTORY! All treasures collected!")
                else:
                    print("💀 GAME OVER!")
                break
                
        except KeyboardInterrupt:
            print("\\nGame interrupted by user")
            break
        except Exception as e:
            print(f"Error during turn: {e}")
            break

if __name__ == "__main__":
    test_agents()
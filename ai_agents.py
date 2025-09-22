"""
AI Agents for the pirate game using LangGraph and Ollama
"""

import json
import random
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from typing_extensions import TypedDict
import subprocess
import os

from game_tools import GameTools
from game_state import GameState
from system_prompts import SYSTEM_PROMPTS


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
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
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
    return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]


def is_openai_model(model_name: str) -> bool:
    """Check if model is an OpenAI model"""
    return model_name in get_openai_models()


def get_all_available_models() -> Dict[str, List[str]]:
    """Get all available models grouped by provider"""
    models = {
        "ollama": get_available_models(),
        "openai": get_openai_models() if os.getenv("OPENAI_API_KEY") else [],
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

    def __init__(
        self,
        game_state: GameState,
        model_name: str,
        use_openai: bool = False,
        system_prompts: Dict[str, str] = None,
        web_gui=None,
    ):
        self.game_state = game_state
        self.game_tools = GameTools(game_state)
        self.model_name = model_name
        self.use_openai = use_openai
        self.web_gui = web_gui

        # Set default system prompts if none provided
        self.system_prompts = system_prompts or SYSTEM_PROMPTS

        # Initialize the appropriate language model
        if use_openai:
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key not found in environment variables")
            print(f"🤖 Initializing OpenAI model: {model_name}")
            self.llm = ChatOpenAI(model=model_name, temperature=0.7, max_tokens=2000)
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

        # Initialize transcript logging
        self.transcript_log = []
        self.log_file_path = f"game_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.turn_counter = 0

        # Initialize decision history tracking
        self.decision_history = []
        self.last_turn_summary = None

        # Create the agent graph
        self.setup_agent_graph()

    def update_system_prompts(self, new_prompts: Dict[str, str]):
        """Update the system prompts used by the agents"""
        self.system_prompts.update(new_prompts)
        print(f"🔄 Updated system prompts for: {', '.join(new_prompts.keys())}")

    def log_agent_interaction(
        self,
        agent_name: str,
        context: str,
        response: str,
        game_status: Dict[str, Any] = None,
    ):
        """Log agent interaction to transcript"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"""
            {'='*80}
            TURN {self.turn_counter} - {agent_name.upper()} AGENT
            Time: {timestamp}
            {'='*80}

            CONTEXT PROVIDED TO AGENT:
            {context}

            {'-'*80}
            AGENT RESPONSE:
            {response}
            {'-'*80}

            """
        if game_status:
            log_entry += f"""GAME STATUS AT TIME OF RESPONSE:
            Position: {game_status.get('ship_position', 'Unknown')}
            Lives: {game_status.get('lives', 'Unknown')}
            Treasures: {game_status.get('treasures_collected', 0)}/{game_status.get('total_treasures', 0)}
            Cannonballs: {game_status.get('cannonballs', 'Unknown')}
            Score: {game_status.get('score', 0)}

            """

        self.transcript_log.append(log_entry)

    def save_transcript(self, final_game_status: Dict[str, Any] = None):
        """Save the complete game transcript to a text file"""
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                # Write header
                f.write(
                    f"""
                    PIRATE GAME AI AGENT TRANSCRIPT
                    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    Model Used: {self.model_name} ({'OpenAI' if self.use_openai else 'Ollama'})
                    Total Turns: {self.turn_counter}
                    {'='*80}

                    """
                )

                # Write all logged interactions
                for entry in self.transcript_log:
                    f.write(entry)

                # Write final game status if provided
                if final_game_status:
                    f.write(
                        f"""
                        {'='*80}
                        FINAL GAME RESULTS
                        {'='*80}
                        Final Position: {final_game_status.get('ship_position', 'Unknown')}
                        Lives Remaining: {final_game_status.get('lives', 'Unknown')}
                        Treasures Collected: {final_game_status.get('treasures_collected', 0)}/{final_game_status.get('total_treasures', 0)}
                        Final Score: {final_game_status.get('score', 0)}
                        Cannonballs Remaining: {final_game_status.get('cannonballs', 'Unknown')}
                        Game Result: {'VICTORY' if final_game_status.get('victory', False) else 'DEFEAT' if final_game_status.get('game_over', False) else 'INCOMPLETE'}
                        Total Enemies Defeated: {final_game_status.get('enemies_defeated', 0)}
                        Total Monsters Defeated: {final_game_status.get('monsters_defeated', 0)}
                        {'='*80}
                        """
                    )

            print(f"📝 Game transcript saved to: {self.log_file_path}")
            return self.log_file_path

        except Exception as e:
            print(f"❌ Error saving transcript: {e}")
            return None

    def track_turn_decision(self, decision: str, pre_turn_status: Dict, post_turn_status: Dict):
        """Track the decision made and its outcome for historical context"""
        try:
            # Calculate outcome metrics
            treasure_gained = post_turn_status.get("treasures_collected", 0) - pre_turn_status.get(
                "treasures_collected", 0
            )
            lives_lost = pre_turn_status.get("lives", 3) - post_turn_status.get("lives", 3)
            cannonballs_used = pre_turn_status.get("cannonballs", 0) - post_turn_status.get(
                "cannonballs", 0
            )

            # Determine outcome quality
            if treasure_gained > 0:
                outcome = "SUCCESSFUL - Collected treasure"
            elif lives_lost > 0:
                outcome = "COSTLY - Lost lives"
            elif cannonballs_used > 0:
                outcome = "COMBAT - Engaged enemies"
            else:
                outcome = "NEUTRAL - No significant change"

            # Store decision record
            decision_record = {
                "turn": self.turn_counter,
                "decision": decision,
                "outcome": outcome,
                "treasure_gained": treasure_gained,
                "lives_lost": lives_lost,
                "cannonballs_used": cannonballs_used,
                "pre_status": {
                    "treasures": pre_turn_status.get("treasures_collected", 0),
                    "lives": pre_turn_status.get("lives", 3),
                    "cannonballs": pre_turn_status.get("cannonballs", 0),
                },
                "post_status": {
                    "treasures": post_turn_status.get("treasures_collected", 0),
                    "lives": post_turn_status.get("lives", 3),
                    "cannonballs": post_turn_status.get("cannonballs", 0),
                },
            }

            self.decision_history.append(decision_record)

            # Keep only last 5 decisions to prevent context overload
            if len(self.decision_history) > 5:
                self.decision_history = self.decision_history[-5:]

            # Create summary for next turn
            self.last_turn_summary = f"PREVIOUS TURN: {decision} → {outcome}"
            if treasure_gained > 0:
                self.last_turn_summary += f" (+{treasure_gained} treasure)"
            if lives_lost > 0:
                self.last_turn_summary += f" (-{lives_lost} lives)"

        except Exception as e:
            print(f"⚠️ Warning: Could not track decision: {e}")

    def get_decision_history_summary(self) -> str:
        """Generate a summary of recent decision history for strategic context"""
        if not self.decision_history:
            return "FIRST TURN: No previous decisions to reference"

        # Get last few decisions
        recent = self.decision_history[-3:]  # Last 3 turns
        summary = "RECENT DECISION HISTORY:\n"

        for record in recent:
            summary += f"Turn {record['turn']}: {record['decision']} → {record['outcome']}\n"

        # Add strategic insights
        if len(self.decision_history) >= 2:
            last_two = self.decision_history[-2:]
            if last_two[0]["decision"] == last_two[1]["decision"]:
                summary += "\n⚠️  WARNING: Repeating same decision - consider alternative strategies"

        return summary.strip()

    def setup_tools(self):
        """Setup tools that agents can use"""

        @tool
        def navigate_scan(radius: int = 5) -> Dict[str, Any]:
            """Scan the environment around the ship for treasures, enemies, and obstacles."""
            return self.game_tools.navigator.scan_surroundings(radius)

        @tool
        def get_cannon_targets() -> List[Dict[str, Any]]:
            """Get all hostile targets within cannon range."""
            return self.game_tools.cannoneer.get_targets_in_range()

        @tool
        def fire_cannon(target_x: int, target_y: int) -> Dict[str, Any]:
            """Fire cannon at specified coordinates. Costs 1 cannonball. Range: 5 tiles."""
            return self.game_tools.cannoneer.fire_cannon(target_x, target_y)

        @tool
        def get_possible_moves() -> List[Dict[str, Any]]:
            """Get all possible moves from current position. Ship can move up to 3 tiles per turn in cardinal directions."""
            return self.game_tools.captain.get_possible_moves()

        @tool
        def move_ship(direction_x: int, direction_y: int) -> Dict[str, Any]:
            """Move the ship up to 3 tiles in cardinal directions.
            Parameters are TOTAL displacement:
            - For 1 tiles north: direction_x=0, direction_y=-1
            - For 2 tiles north: direction_x=0, direction_y=-2
            - For 3 tiles north: direction_x=0, direction_y=-3
            - For 1 tiles south: direction_x=0, direction_y=1
            - For 2 tiles south: direction_x=0, direction_y=2
            - For 3 tiles south: direction_x=0, direction_y=3
            - For 1 tiles west: direction_x=-1, direction_y=0
            - For 2 tiles west: direction_x=-2, direction_y=0
            - For 3 tiles west: direction_x=-3, direction_y=0
            - For 1 tiles east: direction_x=1, direction_y=0
            - For 2 tiles east: direction_x=2, direction_y=0
            - For 3 tiles east: direction_x=3, direction_y=0
            Use get_possible_moves() first to see valid directions with their exact coordinates.
            Illegal moves through land will fail with explanation."""
            return self.game_tools.captain.move_ship(direction_x, direction_y)

        @tool
        def get_game_status() -> Dict[str, Any]:
            """Get comprehensive game status including position, lives, treasures, cannonballs, etc."""
            return self.game_tools.get_game_status()

        self.tools = [
            navigate_scan,
            get_cannon_targets,
            fire_cannon,
            get_possible_moves,
            move_ship,
            get_game_status,
        ]

    def setup_agent_graph(self):
        """Setup the LangGraph agent workflow"""

        # Create tool node
        tool_node = ToolNode(self.tools)

        def navigator_agent(state: GameAgentState) -> GameAgentState:
            """Navigator agent - scans environment and reports findings"""
            system_message = SystemMessage(content=self.system_prompts["navigator"])

            print("\\n🧭 NAVIGATOR: Beginning environmental scan...")

            # Get current game status first
            status = self.game_tools.get_game_status()
            scan_result = self.game_tools.navigator.scan_surroundings(radius=5)

            print(
                f"🧭 NAVIGATOR: Scan complete. Found {len(scan_result['treasures_nearby'])} treasures, {len(scan_result['enemies_nearby'])} enemies, {len(scan_result['monsters_nearby'])} monsters in area."
            )

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
            Lives Remaining: {status['lives']}/3
            Treasures Collected: {status['treasures_collected']}/{status['total_treasures']}
            Cannonballs Remaining: {status['cannonballs']}
            Turn Number: {status['turn_count']}
            
            SCAN RESULTS:
            - Scan Radius: {scan_result['scan_radius']} miles
            - Treasures in area: {len(scan_result['treasures_nearby'])}
            - Enemies in area: {len(scan_result['enemies_nearby'])}  
            - Monsters in area: {len(scan_result['monsters_nearby'])}
            - Immediate threats (within 1 mile): {len(scan_result['immediate_threats'])}
            - Reachable treasures (within 3 miles): {len(scan_result['reachable_treasures'])}
            
            DETAILED FINDINGS:
            Use your navigation tools to scan for specific directional information about treasures and threats.
            Report findings in terms of distances and cardinal directions (N/S/E/W).
            """

            messages = (
                [system_message]
                + state["messages"]
                + [
                    HumanMessage(
                        content=f"Navigator, provide a comprehensive analysis of our current situation and surroundings: {context}"
                    )
                ]
            )

            # Check if stop was requested before making AI call
            if self.web_gui and self.web_gui.game_stop_requested:
                print("🛑 NAVIGATOR: Stop requested, aborting analysis...")
                state["agent_reports"]["navigator"] = "Analysis aborted - game stopped"
                return state

            print("🧭 NAVIGATOR: Analyzing tactical situation...")
            response = self.llm.invoke(messages)
            print(f"🧭 NAVIGATOR REPORT:\\n{response.content}\\n")

            # Log the interaction
            self.log_agent_interaction("navigator", context, response.content, status)

            state["agent_reports"]["navigator"] = response.content
            state["messages"].append(response)

            # Update web GUI with navigator response
            if self.web_gui:
                self.web_gui.agent_reports["navigator"] = response.content

            return state

        def cannoneer_agent(state: GameAgentState) -> GameAgentState:
            """Cannoneer agent - handles combat and targeting"""
            system_message = SystemMessage(content=self.system_prompts["cannoneer"])

            print("\\n⚔️  CANNONEER: Assessing combat situation...")

            # Get available targets
            targets = self.game_tools.cannoneer.get_targets_in_range()
            navigator_report = state["agent_reports"].get(
                "navigator", "No navigator report available"
            )

            print(f"⚔️  CANNONEER: {len(targets)} hostile targets within cannon range")
            for i, target in enumerate(targets):
                hit_chance = target.get("hit_chance", 0.25)
                print(
                    f"⚔️  CANNONEER: Target {i+1}: {target['type']} {target['distance']} miles {target['direction']} - {target['threat_level']} threat level - Hit chance: {hit_chance:.0%}"
                )

            combat_context = f"""
            COMBAT SITUATION ANALYSIS:
            Available Targets: {targets}
            Navigator Intelligence: {navigator_report}
            
            TACTICAL CONSIDERATIONS:
            - Cannon range: 5 tiles (Manhattan distance) with probabilistic hit system
            - Monster threat level: High (more dangerous)
            - Enemy threat level: Medium  
            - Each shot should be carefully considered
            - Coordinate with movement plans
            """

            messages = (
                [system_message]
                + state["messages"]
                + [
                    HumanMessage(
                        content=f"Cannoneer, analyze the combat situation and decide on actions: {combat_context}"
                    )
                ]
            )

            # Check if stop was requested before making AI call
            if self.web_gui and self.web_gui.game_stop_requested:
                print("🛑 CANNONEER: Stop requested, aborting combat analysis...")
                state["agent_reports"]["cannoneer"] = "Combat analysis aborted - game stopped"
                return state

            print("⚔️  CANNONEER: Formulating combat strategy...")
            response = self.llm.invoke(messages)
            print(f"⚔️  CANNONEER TACTICAL ANALYSIS:\\n{response.content}\\n")

            # Log the interaction
            current_status = self.game_tools.get_game_status()
            self.log_agent_interaction(
                "cannoneer", combat_context, response.content, current_status
            )

            # If there are targets and the cannoneer decides to fire, execute it
            if targets and "fire" in response.content.lower():
                print("⚔️  CANNONEER: Attempting to engage targets...")
                for target in targets:
                    # Use internal position coordinates for firing
                    pos = target["_position"]
                    result = self.game_tools.cannoneer.fire_cannon(pos[0], pos[1])
                    print(f"⚔️  CANNONEER: {result['message']}")

                    # Update web GUI with fire cannon result
                    if self.web_gui:
                        self.web_gui.tool_outputs["fire_cannon"] = (
                            f"Target: {target['distance']} miles {target['direction']} - {result['message']}"
                        )

                    if result["success"]:
                        break  # Only fire once per turn

            state["agent_reports"]["cannoneer"] = response.content
            state["messages"].append(response)

            # Update web GUI with cannoneer response
            if self.web_gui:
                self.web_gui.agent_reports["cannoneer"] = response.content

            return state

        def captain_agent(state: GameAgentState) -> GameAgentState:
            """Captain agent - makes movement decisions and overall strategy"""
            system_message = SystemMessage(content=self.system_prompts["captain"])

            print("CAPTAIN: Receiving crew reports and formulating strategy...")

            navigator_report = state["agent_reports"].get(
                "navigator", "Navigator report not available"
            )
            cannoneer_report = state["agent_reports"].get(
                "cannoneer", "Cannoneer report not available"
            )

            # Get movement options
            possible_moves = self.game_tools.captain.get_possible_moves()
            current_status = self.game_tools.get_game_status()

            print("👨‍✈️ CAPTAIN: Analyzing available movement options...")
            for i, move in enumerate(possible_moves):
                risk_color = (
                    "🟢"
                    if "Safe" in move["risk_assessment"]
                    else "🟡" if "Rewarding" in move["risk_assessment"] else "🔴"
                )
                print(
                    f"👨‍✈️ CAPTAIN: Option {i+1}: {move['direction_name']} {risk_color} {move['risk_assessment']}"
                )

            strategic_context = f"""
            COMMAND SITUATION BRIEFING:
            Lives: {current_status['lives']}/3
            Treasures: {current_status['treasures_collected']}/{current_status['total_treasures']}  
            Mission Progress: {(current_status['treasures_collected']/current_status['total_treasures']*100):.1f}% complete
            
            {self.get_decision_history_summary()}
            
            CREW INTELLIGENCE REPORTS:
            Navigator Report: {navigator_report}
            
            Cannoneer Report: {cannoneer_report}
            
            MOVEMENT OPTIONS ANALYSIS:
            AVAILABLE MOVES:
            {chr(10).join([f"- {move['direction_name']}: {move['risk_assessment']}" for move in possible_moves if move['can_move']])}
            
            BLOCKED MOVES:
            {chr(10).join([f"- {move['direction_name']}: {move['risk_assessment']} - {move.get('blocked_reason', 'Path blocked')}" for move in possible_moves if not move['can_move']])}
            
            STRATEGIC OBJECTIVES:
            - Primary: Collect all {current_status['total_treasures']} treasures  
            - Secondary: Preserve crew lives ({current_status['lives']} remaining)
            - Tactical: Maintain operational advantage
            """

            messages = (
                [system_message]
                + state["messages"]
                + [
                    HumanMessage(
                        content=f"Captain, make your strategic decision based on all available intelligence: {strategic_context}"
                    )
                ]
            )

            # Check if stop was requested before making AI call
            if self.web_gui and self.web_gui.game_stop_requested:
                print("🛑 CAPTAIN: Stop requested, aborting strategic decision...")
                state["agent_reports"]["captain"] = "Strategic decision aborted - game stopped"
                state["decision"] = "GAME_STOPPED"
                return state

            print("👨‍✈️ CAPTAIN: Deliberating on best course of action...")
            response = self.llm.invoke(messages)
            print(f"👨‍✈️ CAPTAIN'S STRATEGIC DECISION:\\n{response.content}\\n")

            # Log the interaction
            self.log_agent_interaction(
                "captain", strategic_context, response.content, current_status
            )

            # Parse the captain's decision and execute movement
            print("👨‍✈️ CAPTAIN: Executing movement order...")

            # Try to extract movement command in @[1-3][N/E/S/W] format
            chosen_direction = None
            response_text = response.content

            import re

            # Look for the precise command format @[1-3][N/E/S/W]
            command_pattern = r"@([1-3])([NESW])"
            match = re.search(command_pattern, response_text)

            if match:
                distance = int(match.group(1))
                direction_letter = match.group(2)

                # Map direction letters to unit vectors
                direction_map = {
                    "N": (0, -1),  # North
                    "S": (0, 1),  # South
                    "E": (1, 0),  # East
                    "W": (-1, 0),  # West
                }

                if direction_letter in direction_map:
                    unit_vector = direction_map[direction_letter]
                    chosen_direction = (unit_vector[0] * distance, unit_vector[1] * distance)
                    direction_names = {"N": "North", "S": "South", "E": "East", "W": "West"}
                    print(
                        f"👨‍✈️ CAPTAIN: Parsed command @{distance}{direction_letter} -> {distance} miles {direction_names[direction_letter]} -> {chosen_direction}"
                    )

            # Execute the movement
            if chosen_direction:
                # Get animation data before making the move (for multi-mile movement visualization)
                if self.web_gui:
                    animation_data = self.game_tools.game_state.get_movement_animation_data(
                        chosen_direction
                    )
                    if animation_data["success"] and animation_data["total_steps"] > 1:
                        # Only set animation data for multi-mile moves
                        self.web_gui.movement_animation_data = animation_data

                move_result = self.game_tools.captain.move_ship(
                    chosen_direction[0], chosen_direction[1]
                )
                print(f"👨‍✈️ CAPTAIN: Movement result - {move_result['message']}")

                # Update web GUI with movement result
                if self.web_gui:
                    direction_name = "Unknown"
                    for move in possible_moves:
                        if move["direction"] == chosen_direction:
                            direction_name = move["direction_name"]
                            break
                    self.web_gui.tool_outputs["move"] = (
                        f"Direction: {direction_name} - {move_result['message']}"
                    )
            else:
                print("👨‍✈️ CAPTAIN: No movement commanded - maintaining current position!")
                # Update web GUI with no movement
                if self.web_gui:
                    self.web_gui.tool_outputs["move"] = (
                        "No movement commanded - maintaining position"
                    )

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
        # Check if stop was requested before starting the turn
        if self.web_gui and self.web_gui.game_stop_requested:
            print("🛑 STOP REQUESTED: Aborting agent turn...")
            return GameAgentState(
                messages=[],
                game_status=self.game_tools.get_game_status(),
                last_action="GAME_STOPPED",
                agent_reports={"system": "Game stopped by user request"},
                decision="STOP_GAME",
            )

        self.turn_counter += 1

        initial_state = GameAgentState(
            messages=[],
            game_status=self.game_tools.get_game_status(),
            last_action=None,
            agent_reports={},
            decision=None,
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

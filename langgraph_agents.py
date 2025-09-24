"""
LangGraph-based AI Agents for the pirate game using proper tool calling patterns
This is a complete rewrite of ai_agents.py using proper LangGraph conventions.
"""

import json
import random
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from typing_extensions import TypedDict
import subprocess
import os

from game_tools import GameTools
from game_state import GameState
from system_prompts import SYSTEM_PROMPTS
from card_prompts import GAME_CARDS, get_random_card, get_cards_for_agent


class GameAgentState(TypedDict):
    """State shared between all agents - enhanced for proper LangGraph tool calling"""

    messages: List[Any]  # Full message history including tool calls and results
    game_status: Dict[str, Any]
    last_action: Optional[str]
    agent_reports: Dict[str, str]  # Formatted reports from each agent
    decision: Optional[str]
    current_agent: Optional[str]  # Track which agent is currently active


# Step 1.1: Create langgraph_agents.py with proper imports and LangGraph tools
# ✅ Imports completed above


class LangGraphPirateGameAgents:
    """
    LangGraph-based implementation of pirate game agents using proper tool calling patterns.
    This replaces the manual tool execution in ai_agents.py with structured LangGraph workflows.
    """

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
                verbose=True,
            )

        # Step 1.2: Define LangGraph tools using @tool decorator
        self.setup_langgraph_tools()

        # Step 1.3: Set up proper GameAgentState with message tracking
        # (Already defined above as TypedDict)

        # Step 1.4: Create LLM instances with proper tool binding
        # (Will be done per agent to allow different tool sets)

        # Initialize transcript logging (keeping same as original)
        self.transcript_log = []
        os.makedirs("transcripts", exist_ok=True)
        self.log_file_path = (
            f"transcripts/langgraph_game_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        self.turn_counter = 0

        # Initialize decision history tracking
        self.decision_history = []
        self.last_turn_summary = None

        # Initialize card system
        self.current_cards = []
        self.cards_drawn_this_turn = []

        # Create the LangGraph agent workflow
        self.setup_langgraph_workflow()

    def setup_langgraph_tools(self):
        """
        Step 1.2: Define LangGraph tools using @tool decorator for all game functions
        These replace the manual self.game_tools.method() calls with proper LangGraph tools
        """

        @tool
        def navigate_scan(radius: int = 5) -> str:
            """
            Scan the environment around the ship for treasures, enemies, and obstacles.

            Args:
                radius: Scanning radius in tiles (default: 5, max: 10)

            Returns:
                Formatted string with scan results including treasures, enemies, monsters,
                their positions, distances, and threat assessments.
            """
            scan_data = self.game_tools.navigator.scan_surroundings(radius)

            # Format scan results for LLM consumption
            result = []
            result.append(f"=== NAVIGATION SCAN (Radius: {scan_data['scan_radius']} tiles) ===")
            result.append(f"Summary: {scan_data['summary']}")

            if scan_data.get("treasures_nearby"):
                result.append("\n🏴‍☠️ TREASURES DETECTED:")
                for treasure in scan_data["treasures_nearby"]:
                    result.append(
                        f"  - Treasure at {treasure['direction']} (Distance: {treasure['distance']} tiles)"
                    )

            if scan_data.get("enemies_nearby"):
                result.append("\n⚔️ ENEMIES DETECTED:")
                for enemy in scan_data["enemies_nearby"]:
                    result.append(
                        f"  - Enemy at {enemy['direction']} (Distance: {enemy['distance']} tiles)"
                    )

            if scan_data.get("monsters_nearby"):
                result.append("\n🐙 MONSTERS DETECTED:")
                for monster in scan_data["monsters_nearby"]:
                    result.append(
                        f"  - Monster at {monster['direction']} (Distance: {monster['distance']} tiles)"
                    )

            if scan_data.get("immediate_threats"):
                result.append(
                    f"\n⚠️ IMMEDIATE THREATS: {len(scan_data['immediate_threats'])} within 1 tile"
                )

            if scan_data.get("reachable_treasures"):
                result.append(
                    f"\n✅ REACHABLE TREASURES: {len(scan_data['reachable_treasures'])} within 3 tiles"
                )

            return "\n".join(result)

        @tool
        def fire_cannon(target_position: str, direction: str = None) -> str:
            """
            Fire the ship's cannon at enemy targets within range.

            Args:
                target_position: Target position in format like "3N", "2E", or "1N+2E"
                direction: Alternative direction format (N/S/E/W combination)

            Returns:
                String describing the cannon fire results, hits, misses, and remaining threats.
            """
            try:
                # Parse target position if in combined format
                if "+" in target_position:
                    # Handle combined directions like "1N+2E"
                    parts = target_position.split("+")
                    # Use the game_tools fire_cannon method
                    result = self.game_tools.cannoneer.fire_cannon(target_position, direction)
                else:
                    # Single direction target
                    result = self.game_tools.cannoneer.fire_cannon(target_position, direction)

                # Format result for LLM
                if result.get("success"):
                    return f"🎯 CANNON FIRE SUCCESS: {result.get('message', 'Target destroyed!')} Cannonballs remaining: {result.get('cannonballs_remaining', 'Unknown')}"
                else:
                    return f"💥 CANNON FIRE RESULT: {result.get('message', 'Shot fired but no hit confirmed')} Cannonballs remaining: {result.get('cannonballs_remaining', 'Unknown')}"

            except Exception as e:
                return f"❌ CANNON FIRE FAILED: {str(e)}"

        @tool
        def move_ship(distance: int, direction: str) -> str:
            """
            Move the pirate ship in the specified direction and distance.

            Args:
                distance: Number of tiles to move (1-3)
                direction: Direction to move (N/S/E/W)

            Returns:
                String describing the movement result, new position, and any encounters.
            """
            try:
                result = self.game_tools.captain.move_ship(distance, direction)

                if result.get("success"):
                    new_pos = result.get("new_position", "Unknown")
                    message = result.get("message", "Ship moved successfully")
                    encounters = result.get("encounters", [])

                    response = f"⚓ MOVEMENT SUCCESS: {message} New position: {new_pos}"

                    if encounters:
                        response += f"\n🗺️ ENCOUNTERS: {', '.join(encounters)}"

                    return response
                else:
                    return f"⛔ MOVEMENT FAILED: {result.get('message', 'Cannot move in that direction')}"

            except Exception as e:
                return f"❌ MOVEMENT ERROR: {str(e)}"

        # Store tools for use in workflow
        self.navigate_scan_tool = navigate_scan
        self.fire_cannon_tool = fire_cannon
        self.move_ship_tool = move_ship

        # Create tool sets for each agent (single responsibility principle)
        self.navigator_tools = [navigate_scan]
        self.cannoneer_tools = [fire_cannon]
        self.captain_tools = [move_ship]

        print("🔧 LangGraph tools initialized:")
        print(f"  - Navigator tools: {[t.name for t in self.navigator_tools]}")
        print(f"  - Cannoneer tools: {[t.name for t in self.cannoneer_tools]}")
        print(f"  - Captain tools: {[t.name for t in self.captain_tools]}")

    def setup_langgraph_workflow(self):
        """
        Set up the complete LangGraph workflow with proper tool calling patterns.
        Implementing Phase 2: Individual Agent Implementation
        """
        print("🏗️ Setting up LangGraph workflow with proper agent implementations...")
        
        # Create tool nodes for each agent
        navigator_tool_node = ToolNode(self.navigator_tools)
        cannoneer_tool_node = ToolNode(self.cannoneer_tools)
        captain_tool_node = ToolNode(self.captain_tools)
        
        # Step 2.1: Navigator Agent Implementation
        def navigator_agent(state: GameAgentState) -> GameAgentState:
            """
            Navigator agent using proper LangGraph tool calling.
            Replaces the manual self.game_tools.navigator.scan_surroundings() calls.
            """
            print("\\n🧭 NAVIGATOR: Beginning lookout duties with LangGraph tool calling...")
            
            # Check if stop was requested
            if self.web_gui and self.web_gui.game_stop_requested:
                print("🛑 NAVIGATOR: Stop requested, holding position...")
                state["agent_reports"]["navigator"] = "Lookout duties aborted - game stopped"
                return state
            
            state["current_agent"] = "navigator"
            
            # Create system message for navigator
            system_message = SystemMessage(content=self.get_agent_system_prompt("navigator"))
            
            # Create human message requesting scan
            human_message = HumanMessage(content=f"""
            As the ship's Navigator and Lookout, you must scan the surrounding waters for treasures, enemies, and obstacles.
            
            Use the navigate_scan tool to survey the area. Scan with a radius of 5 tiles to get comprehensive intelligence.
            
            After scanning, provide a clear tactical report about what you've discovered so the crew can act on your intelligence.
            """)
            
            # Build message list for LLM - Each agent gets fresh context to avoid 400 errors
            # Don't pass full state messages to prevent tool message conflicts
            messages = [system_message, human_message]
            
            # Use LangGraph's bind_tools pattern for proper tool calling
            navigator_llm = self.llm.bind_tools(self.navigator_tools)
            response = navigator_llm.invoke(messages)
            
            # Add response to state messages
            state["messages"] = state.get("messages", []) + [response]
            
            print(f"🧭 Navigator agent response generated: {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            return state
        
        # Step 2.2: Navigator Result Handler  
        def navigator_result_handler(state: GameAgentState) -> GameAgentState:
            """
            Handle navigator tool results and extract readable report.
            This processes the tool execution results into a format other agents can use.
            """
            print("📊 NAVIGATOR: Processing scan results...")
            
            # Extract tool results from messages
            tool_results = extract_tool_results(state.get("messages", []))
            
            if tool_results:
                # Get the latest scan result
                latest_scan = tool_results[-1]
                scan_data = latest_scan.get('tool_result', 'No scan data available')
                
                # Format into a readable report for other agents
                navigator_report = f"🧭 NAVIGATOR TACTICAL REPORT:\\n{scan_data}"
                
                # Store in agent reports
                state["agent_reports"]["navigator"] = navigator_report
                
                # Update web GUI if available
                if self.web_gui:
                    self.web_gui.agent_reports["navigator"] = navigator_report
                
                print(f"� Navigator report generated: {len(navigator_report)} characters")
            else:
                # Fallback if no tool results found
                state["agent_reports"]["navigator"] = "🧭 NAVIGATOR REPORT: No scan data - area reconnaissance failed"
                print("⚠️ Navigator: No tool results found in message history")
            
            return state
        
        # Step 2.3: Cannoneer Agent Implementation
        def cannoneer_agent(state: GameAgentState) -> GameAgentState:
            """Cannoneer agent using proper LangGraph tool calling for combat decisions"""
            print("\\n⚔️ CANNONEER: Assessing targets based on navigator report...")
            
            # Check if stop was requested
            if self.web_gui and self.web_gui.game_stop_requested:
                print("🛑 CANNONEER: Stop requested, holding fire...")
                state["agent_reports"]["cannoneer"] = "Combat operations aborted - game stopped"
                return state
                
            state["current_agent"] = "cannoneer"
            
            # Get Navigator's tactical report
            navigator_report = state["agent_reports"].get("navigator", "No navigator report available")
            
            # Create system message for cannoneer
            system_message = SystemMessage(content=self.get_agent_system_prompt("cannoneer"))
            
            # Create human message with tactical assessment request
            human_message = HumanMessage(content=f"""
            As the ship's Cannoneer, analyze the Navigator's tactical report for hostile targets within cannon range.
            
            Navigator's Intelligence Report:
            {navigator_report}
            
            COMBAT ASSESSMENT REQUIRED:
            - Identify enemies and monsters within cannon range (5 tiles maximum)
            - If threats are present and within range, use the fire_cannon tool to engage them
            - Prioritize the most dangerous and closest targets first
            - Report combat results including hits, misses, and remaining threats
            
            AMMUNITION CONSERVATION:
            - Only engage clear threats that pose immediate danger
            - Save ammunition for strategic targets
            - Report cannonball status after engagement
            
            If no targets are within range or worth engaging, report "AREA SECURE - NO ENGAGEMENT REQUIRED"
            """)
            
            # Build message list for LLM - Each agent gets fresh context to avoid 400 errors  
            # The navigator report provides the intelligence, not the raw tool messages
            messages = [system_message, human_message]
            
            # Use LangGraph's bind_tools pattern for combat decisions
            cannoneer_llm = self.llm.bind_tools(self.cannoneer_tools)
            response = cannoneer_llm.invoke(messages)
            
            # Add response to state messages for tool execution tracking
            state["messages"] = state.get("messages", []) + [response]
            
            print(f"⚔️ Cannoneer agent response generated: {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            return state
        
        # Step 2.3: Cannoneer Result Handler
        def cannoneer_result_handler(state: GameAgentState) -> GameAgentState:
            """Handle cannoneer tool results and extract combat report"""
            print("💥 CANNONEER: Processing combat results...")
            
            # Extract tool results from messages
            tool_results = extract_tool_results(state.get("messages", []))
            
            # Look for recent cannon fire results
            cannoneer_results = [r for r in tool_results if r.get('tool_name') == 'fire_cannon']
            
            if cannoneer_results:
                # Process cannon fire results
                combat_report = "⚔️ CANNONEER COMBAT REPORT:\\n"
                for i, result in enumerate(cannoneer_results[-3:], 1):  # Last 3 cannon fires
                    combat_data = result.get('tool_result', 'Combat data unavailable')
                    combat_report += f"Engagement #{i}: {combat_data}\\n"
                
                state["agent_reports"]["cannoneer"] = combat_report.strip()
                print(f"💥 Combat report generated: {len(cannoneer_results)} engagements processed")
            else:
                # No combat action taken
                state["agent_reports"]["cannoneer"] = "⚔️ CANNONEER REPORT: AREA SECURE - No engagement required, ammunition conserved"
                print("🛡️ Cannoneer: No combat action taken - area assessment complete")
            
            # Update web GUI if available
            if self.web_gui:
                self.web_gui.agent_reports["cannoneer"] = state["agent_reports"]["cannoneer"]
                
            return state
        
        def captain_agent(state: GameAgentState) -> GameAgentState:
            """Captain agent - to be implemented in Step 2.4"""
            print("\\n👨‍✈️ CAPTAIN: Placeholder - reviewing crew reports...")
            
            navigator_report = state["agent_reports"].get("navigator", "No navigator report")
            cannoneer_report = state["agent_reports"].get("cannoneer", "No cannoneer report")
            
            state["agent_reports"]["captain"] = f"👨‍✈️ CAPTAIN: Strategic assessment based on crew intel"
            state["decision"] = "HOLD_POSITION"  # Placeholder decision
            
            if self.web_gui:
                self.web_gui.agent_reports["captain"] = state["agent_reports"]["captain"]
                
            return state
        
        # Conditional routing function
        def route_after_agent(state: GameAgentState) -> str:
            """Determine next step based on whether agent made tool calls"""
            if has_tool_calls(state):
                current_agent = state.get("current_agent", "unknown")
                return f"{current_agent}_tools"
            else:
                # No tool calls, go to next agent or end
                current_agent = state.get("current_agent", "unknown")
                if current_agent == "navigator":
                    return "cannoneer"
                elif current_agent == "cannoneer":
                    return "captain"
                else:
                    return "end"
        
        # Build the LangGraph workflow
        workflow = StateGraph(GameAgentState)
        
        # Add agent nodes
        workflow.add_node("navigator", navigator_agent)
        workflow.add_node("cannoneer", cannoneer_agent)
        workflow.add_node("captain", captain_agent)
        
        # Add tool nodes
        workflow.add_node("navigator_tools", navigator_tool_node)
        workflow.add_node("cannoneer_tools", cannoneer_tool_node)
        workflow.add_node("captain_tools", captain_tool_node)
        
        # Add result handler nodes
        workflow.add_node("navigator_result_handler", navigator_result_handler)
        workflow.add_node("cannoneer_result_handler", cannoneer_result_handler)
        # captain result handler will be added in subsequent steps
        
        # Set entry point
        workflow.set_entry_point("navigator")
        
        # Navigator workflow: navigator -> tools (if needed) -> result_handler -> cannoneer
        workflow.add_conditional_edges(
            "navigator",
            route_after_agent,
            {
                "navigator_tools": "navigator_tools",
                "cannoneer": "cannoneer"
            }
        )
        workflow.add_edge("navigator_tools", "navigator_result_handler")
        workflow.add_edge("navigator_result_handler", "cannoneer")
        
        # Cannoneer workflow: cannoneer -> tools (if needed) -> result_handler -> captain
        workflow.add_conditional_edges(
            "cannoneer",
            route_after_agent,
            {
                "cannoneer_tools": "cannoneer_tools",
                "captain": "captain"
            }
        )
        workflow.add_edge("cannoneer_tools", "cannoneer_result_handler")
        workflow.add_edge("cannoneer_result_handler", "captain")
        
        # Temporary edge for captain (will be updated when captain agent is implemented)
        workflow.add_edge("captain", END)
        
        self.graph = workflow.compile()
        print("✅ LangGraph workflow with Navigator agent implementation complete")

    def get_agent_system_prompt(self, agent_name: str) -> str:
        """Get the system prompt for a specific agent"""
        return self.system_prompts.get(agent_name, f"You are the {agent_name} agent.")

    def run_turn(self) -> GameAgentState:
        """
        Run one turn of the game with LangGraph agents.
        Currently using placeholder - will be fully implemented in Phase 2.
        """
        print("🚀 Running LangGraph agent turn...")

        self.turn_counter += 1

        initial_state = GameAgentState(
            messages=[],
            game_status=self.game_tools.get_game_status(),
            last_action=None,
            agent_reports={},
            decision=None,
            current_agent=None,
        )

        # Execute the LangGraph workflow
        final_state = self.graph.invoke(initial_state)

        print(f"✅ LangGraph turn {self.turn_counter} completed")
        return final_state


# Utility functions that will be used in Phase 2
def extract_tool_results(messages: List[Any]) -> List[Dict[str, Any]]:
    """
    Extract tool results from LangGraph message history.
    This will be used by result handlers to process tool outputs.
    """
    tool_results = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            tool_results.append(
                {
                    "tool_name": getattr(msg, "name", "unknown"),
                    "tool_result": msg.content,
                    "tool_call_id": getattr(msg, "tool_call_id", None),
                }
            )
    return tool_results


def has_tool_calls(state: GameAgentState) -> bool:
    """
    Check if the last message in state contains tool calls.
    Used for conditional routing in LangGraph workflow.
    """
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        return hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)
    return False


# Test function for development
def test_langgraph_agents():
    """Test function to verify LangGraph agents setup"""
    print("=== Testing LangGraph Pirate Game Agents ===")
    
    # Use OpenAI for testing since Ollama doesn't support bind_tools yet
    game_state = GameState()
    
    # Try OpenAI first, fallback to different approach for Ollama
    try:
        if os.getenv("OPENAI_API_KEY"):
            print("🤖 Using OpenAI for LangGraph tool calling test...")
            agents = LangGraphPirateGameAgents(game_state, "gpt-4o-mini", use_openai=True)
        else:
            print("⚠️ OpenAI API key not found - LangGraph tool calling requires OpenAI")
            print("🔧 Consider setting OPENAI_API_KEY for full LangGraph functionality")
            print("📝 For now, testing basic setup...")
            agents = LangGraphPirateGameAgents(game_state, "llama3.2", use_openai=False)
            print("✅ Basic setup test completed")
            return
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return
    
    print("\n=== Testing Tool Setup ===")
    print(f"Navigator tools: {len(agents.navigator_tools)}")
    print(f"Cannoneer tools: {len(agents.cannoneer_tools)}") 
    print(f"Captain tools: {len(agents.captain_tools)}")
    
    print("\n=== Running Test Turn ===")
    try:
        result = agents.run_turn()
        print(f"Turn result: {result.get('agent_reports', {})}")
        print("✅ LangGraph agents test completed successfully")
    except Exception as e:
        print(f"❌ Turn execution failed: {e}")
        print("This is expected if using Ollama - bind_tools not yet supported")
if __name__ == "__main__":
    test_langgraph_agents()

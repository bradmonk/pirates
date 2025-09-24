#!/usr/bin/env python3
"""
Display the Pirate Game LangGraph Network Structure
Generates a PNG diagram showing the Navigator -> Cannoneer -> Captain workflow
"""

import os
import sys

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def generate_text_network_diagram(graph) -> str:
    """Generate a text-based visualization of the LangGraph network"""

    diagram = """
🏴‍☠️ PIRATE GAME LANGGRAPH NETWORK STRUCTURE
=============================================

📊 WORKFLOW VISUALIZATION:
┌─────────────────────────────────────────────────────────────┐
│                    PIRATE AGENT WORKFLOW                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  __start__                                                  │
│      │                                                      │
│      ▼                                                      │
│ 🧭 navigator ────────────────┐                              │
│      │                       │                              │
│      ▼                       ▼                              │
│ navigator_tools         [no tools]                          │
│      │                       │                              │
│      ▼                       │                              │
│ navigator_result_handler     │                              │
│      │                       │                              │
│      └───────────────────────┘                              │
│      │                                                      │
│      ▼                                                      │
│ ⚔️ cannoneer ─────────────────┐                              │
│      │                       │                              │
│      ▼                       ▼                              │
│ cannoneer_tools         [no tools]                          │
│      │                       │                              │
│      ▼                       │                              │
│ cannoneer_result_handler     │                              │
│      │                       │                              │
│      └───────────────────────┘                              │
│      │                                                      │
│      ▼                                                      │
│ 🏴‍☠️ captain ─────────────────┐                               │
│      │                       │                              │
│      ▼                       ▼                              │
│ captain_tools           [no tools]                          │
│      │                       │                              │
│      ▼                       │                              │
│ captain_result_handler       │                              │
│      │                       │                              │
│      └───────────────────────┘                              │
│      │                                                      │
│      ▼                                                      │
│   __end__                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

🔧 AGENT TOOLS:
• Navigator: navigate_scan (environment scanning)
• Cannoneer: fire_cannon (combat engagement)  
• Captain: move_ship (strategic movement)

⚡ CONDITIONAL LOGIC:
Each agent can either:
- Make tool calls → Go to tool node → Process results → Next agent
- Skip tools → Go directly to next agent

🎯 WORKFLOW SUMMARY:
1. Navigator scans environment and reports findings
2. Cannoneer assesses targets and engages if needed  
3. Captain analyzes reports and makes movement decisions
4. Each step processes tool results before proceeding

"""

    # Add node details
    nodes = list(graph.nodes.keys())
    edges_info = []

    try:
        # Try to get edge information
        for node in nodes:
            if hasattr(graph, "edges") and node in graph.edges:
                edges_info.append(f"  {node} → {graph.edges[node]}")
    except:
        pass

    diagram += f"\n📍 GRAPH NODES ({len(nodes)} total):\n"
    for node in sorted(nodes):
        if node.startswith("__"):
            diagram += f"  🎯 {node} (system node)\n"
        elif "tools" in node:
            diagram += f"  🔧 {node} (tool execution)\n"
        elif "result_handler" in node:
            diagram += f"  📊 {node} (result processing)\n"
        else:
            diagram += f"  🤖 {node} (agent node)\n"

    if edges_info:
        diagram += f"\n🔗 EDGE CONNECTIONS:\n" + "\n".join(edges_info)

    return diagram


try:
    from langgraph_agents import LangGraphPirateGameAgents
    from game_state import GameState
    import json

    print("🏴‍☠️ Loading Pirate Game LangGraph...")

    # Create a minimal game state for initialization
    game_state = GameState()

    # Initialize the LangGraph agents (using OpenAI for tool calling)
    agents = LangGraphPirateGameAgents(
        game_state=game_state,
        model_name="gpt-4o-mini",  # Required parameter
        use_openai=True,  # Required for bind_tools()
        web_gui=None,  # No web GUI needed for graph display
    )

    print("🎯 Generating LangGraph network diagram...")

    try:
        # Try multiple methods to generate the diagram
        print("🎯 Attempting to generate LangGraph diagram...")

        try:
            # Method 1: Try with higher retry settings
            print("   📡 Trying online Mermaid service with retries...")
            mermaid_png_data = agents.graph.get_graph().draw_mermaid_png(
                max_retries=3, retry_delay=1.0
            )

            diagram_filename = "pirate_game_langgraph.png"
            with open(diagram_filename, "wb") as f:
                f.write(mermaid_png_data)
            print(f"✅ SUCCESS: Diagram saved as {diagram_filename}")

        except Exception as online_error:
            print(f"   ❌ Online method failed: {online_error}")

            try:
                # Method 2: Try local Pyppeteer rendering
                print("   🌐 Trying local browser rendering (Pyppeteer)...")
                from langgraph.graph.graph import MermaidDrawMethod

                mermaid_png_data = agents.graph.get_graph().draw_mermaid_png(
                    draw_method=MermaidDrawMethod.PYPPETEER
                )

                diagram_filename = "pirate_game_langgraph.png"
                with open(diagram_filename, "wb") as f:
                    f.write(mermaid_png_data)
                print(f"✅ SUCCESS: Local diagram saved as {diagram_filename}")

            except Exception as local_error:
                print(f"   ❌ Local method failed: {local_error}")

                # Method 3: Generate a text-based network diagram
                print("   📝 Generating text-based network diagram...")

                text_diagram = generate_text_network_diagram(agents.graph.get_graph())

                with open("pirate_game_network.txt", "w") as f:
                    f.write(text_diagram)

                print("✅ Text-based network diagram saved as: pirate_game_network.txt")
                print("\n" + text_diagram)

        # Also print some basic graph info
        print(f"\n🏗️ Graph Structure Info:")
        nodes = list(agents.graph.get_graph().nodes.keys())
        print(f"   📍 Nodes: {len(nodes)} total")
        for node in sorted(nodes):
            print(f"      - {node}")

    except Exception as e:
        print(f"❌ Failed to generate diagram: {e}")
        print("   💡 This might happen if:")
        print("   - Internet connection is required for Mermaid rendering")
        print("   - OpenAI API key is not set (required for LangGraph initialization)")

        # Try to get basic graph structure anyway
        try:
            print(f"\n🏗️ Basic Graph Structure (without diagram):")
            nodes = list(agents.graph.get_graph().nodes.keys())
            print(f"   📍 Nodes ({len(nodes)} total):")
            for node in sorted(nodes):
                print(f"      - {node}")
        except Exception as inner_e:
            print(f"   ❌ Could not access graph structure: {inner_e}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure you're in the pirates directory and have all dependencies installed")

except Exception as e:
    print(f"❌ Error initializing agents: {e}")
    print("   💡 This might happen if OpenAI API key is not configured")
    print("   The graph structure exists but needs proper initialization")

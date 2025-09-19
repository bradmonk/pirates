#!/usr/bin/env python3
"""
Simple LangGraph Diagram Display for Pirate Game
Displays the graph structure as a PNG image using IPython/Jupyter style display
"""

from typing import Dict, TypedDict, Union, Any
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    message : str



def greeting_node(state: AgentState) -> AgentState:
    """Simple node that adds a greeting to the message state."""

    state['message'] = "Hey " + state["message"] + ", how are you?"

    return state


graph = StateGraph(AgentState)

graph.add_node("greeter", greeting_node)

graph.set_entry_point("greeter")
graph.set_finish_point("greeter")

app = graph.compile()



# Use the code below to generate the diagram for this project
print("🎯 Generating LangGraph diagram...")
mermaid_png_data = app.get_graph().draw_mermaid_png()

diagram_filename = "langgraph_diagram.png"
with open(diagram_filename, "wb") as f:
    f.write(mermaid_png_data)

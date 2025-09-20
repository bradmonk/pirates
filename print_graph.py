#!/usr/bin/env python3
"""
Print LangGraph Mermaid Code for Pirate Game
"""

from game_state import GameState
from ai_agents import PirateGameAgents

def main():
    print("🏴‍☠️ Generating LangGraph Mermaid code...")
    
    try:
        # Create minimal game state and agents to access the graph
        game_state = GameState()
        agents = PirateGameAgents(game_state, 'gpt-4', use_openai=True)
        
        # Get the mermaid syntax directly
        print("🎯 Getting Mermaid code...")
        mermaid_code = agents.graph.get_graph().draw_mermaid()
        
        print('\n' + '='*60)
        print('📋 MERMAID CODE (paste this into mermaid.live)')
        print('='*60)
        print(mermaid_code)
        print('='*60)
        print('✅ Copy the code above and paste it into https://mermaid.live/')
        
        # Also save to file
        with open("current_graph.mmd", "w") as f:
            f.write(mermaid_code)
        print(f"💾 Also saved to: current_graph.mmd")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
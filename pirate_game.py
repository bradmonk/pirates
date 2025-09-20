#!/usr/bin/env python3
"""
Pirate Game - Main game loop
A 2D pirate adventure game played by AI agents using LangGraph and Ollama
"""
import sys
import time
from typing import Optional

from game_state import GameState
from ai_agents import PirateGameAgents, select_model, is_openai_model

# Import GUI with fallback
try:
    from web_gui import PirateGameWebGUI, open_browser
    GUI_AVAILABLE = True
    GUI_TYPE = "web"
except ImportError:
    try:
        from gui_display import PirateGameGUI
        GUI_AVAILABLE = True
        GUI_TYPE = "matplotlib"
    except ImportError:
        GUI_AVAILABLE = False
        GUI_TYPE = "none"
        print("No GUI available. Running in text mode only.")

class PirateGame:
    """Main game controller"""
    
    def __init__(self):
        self.game_state: Optional[GameState] = None
        self.agents: Optional[PirateGameAgents] = None
        self.model_name: Optional[str] = None
        self.gui = None
        self.use_gui = False
        self.gui_type = GUI_TYPE
    
    def setup_game(self) -> bool:
        """Setup the game with model selection and initialization"""
        print("🏴‍☠️" + "="*60 + "🏴‍☠️")
        print("      Welcome to the AI Pirate Treasure Hunt!")
        print("🏴‍☠️" + "="*60 + "🏴‍☠️")
        print()
        print("In this game, three AI agents work together to navigate")
        print("a pirate ship across treacherous waters:")
        print("  🧭 Navigator - Scans for treasures and threats")  
        print("  ⚔️  Cannoneer - Handles combat operations")
        print("  👨‍✈️ Captain - Makes movement and strategic decisions")
        print()
        print("Objective: Collect all treasures while avoiding enemies!")
        print("  💰 Treasures to collect")
        print("  ⚔️  Enemies (damage on contact)")
        print("  👹 Monsters (damage on contact)")
        print("  🌍 Land (impassable)")
        print("  🌊 Water (safe passage)")
        print()
        print("🌐 Opening web interface for model selection and game control...")
        print()
        
        # Always use web GUI - no more prompts
        self.use_gui = GUI_AVAILABLE
        
        # Skip model selection - will be done via web interface
        self.model_name = None
        
        # Initialize game components
        try:
            print("\\nInitializing game...")
            self.game_state = GameState()
            
            # Initialize GUI if requested
            if self.use_gui and GUI_AVAILABLE:
                print(f"Starting {GUI_TYPE} GUI...")
                if GUI_TYPE == "web":
                    self.gui = PirateGameWebGUI(self.game_state)
                    self.gui.start_server()
                    # Give server a moment to start
                    time.sleep(2)
                    # Open browser automatically
                    open_browser("http://localhost:8000")
                else:  # matplotlib fallback
                    from gui_display import PirateGameGUI
                    self.gui = PirateGameGUI(self.game_state)
                
                # Update display
                self.gui.update_display()
                
                # Show GUI (only for matplotlib)
                if GUI_TYPE == "matplotlib" and hasattr(self.gui, 'show'):
                    self.gui.show(block=False)
            
            # Don't initialize agents yet - wait for model selection via web interface
            self.agents = None
            print("✅ Game initialized successfully!")
            print("🎮 Select a model and click 'Start Game' in the web interface")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize game: {e}")
            return False
    
    def play_game(self):
        """Main game loop"""
        if not self.game_state:
            print("❌ Game not properly initialized!")
            return
        
        print("\\n🚢 Waiting for model selection via web interface...")
        
        # Wait for model selection via web interface
        while not self.gui or not hasattr(self.gui, 'selected_model') or not self.gui.selected_model:
            time.sleep(1)
            if not self.gui or not self.gui.running:
                print("❌ Web interface not available!")
                return
        
        # Initialize agents with selected model
        model_name = self.gui.selected_model
        use_openai = is_openai_model(model_name)
        
        print(f"\\n🤖 Initializing AI agents with {'OpenAI' if use_openai else 'Ollama'} model: {model_name}")
        
        # Get system prompts from GUI if available
        system_prompts = None
        if self.gui and hasattr(self.gui, 'system_prompts'):
            system_prompts = self.gui.system_prompts
        
        self.agents = PirateGameAgents(self.game_state, model_name, use_openai, system_prompts, self.gui)
        
        print("\\n🚢 Setting sail...")
        print("\\n" + "="*80)
        
        # Show initial state
        if self.use_gui and self.gui:
            print("📱 GUI Display Active")
        else:
            self.game_state.display_map()
        
        turn_count = 0
        max_turns = 50  # Prevent infinite loops
        
        while not self.game_state.game_over and turn_count < max_turns:
            # Check if stop was requested via web UI
            if self.use_gui and self.gui and self.gui.game_stop_requested:
                print("\\n🛑 GAME STOP REQUESTED VIA WEB INTERFACE")
                print("🚢 Anchoring ship and ending voyage...")
                break
            
            # Check if system prompts were updated via web UI
            if self.use_gui and self.gui and hasattr(self.gui, 'system_prompts') and self.agents:
                self.agents.update_system_prompts(self.gui.system_prompts)
                
            turn_count += 1
            print(f"\\n{'='*30} TURN {turn_count} BEGINS {'='*30}")
            print(f"📍 Current Status: Position {self.game_state.ship_position.x},{self.game_state.ship_position.y} | Lives: {self.game_state.lives} | Treasures: {self.game_state.treasures_collected}/{self.game_state.total_treasures}")
            print("="*80)
            
            try:
                # Let agents make decisions
                print("🤖 AI CREW DELIBERATION COMMENCING...")
                print("="*80)
                result = self.agents.run_turn()
                print("="*80)
                print("🤖 AI CREW DELIBERATION COMPLETE")
                
                # Display comprehensive agent communications
                print("\\n📋 DETAILED CREW REPORTS:")
                print("-" * 60)
                for agent_name, report in result.get("agent_reports", {}).items():
                    print(f"\\n{agent_name.upper()} FULL REPORT:")
                    print("-" * 40)
                    print(report)
                    print("-" * 40)
                
                # Move enemies and monsters toward the ship
                print("\\n👹 ENEMY MOVEMENT PHASE:")
                print("-" * 60)
                enemy_movements = self.game_state.move_enemies_and_monsters()
                if enemy_movements:
                    for movement in enemy_movements:
                        if movement.get('blocked', False):
                            print(f"🚫 {movement['entity_type']} at {movement['from']} blocked by terrain (distance: {movement['distance_to_ship']} tiles)")
                        else:
                            print(f"⚔️ {movement['entity_type']} moved from {movement['from']} → {movement['to']} (distance to ship: {movement['distance_to_ship']} tiles)")
                else:
                    print("🏝️ No enemies within 3 tiles of ship - all quiet")
                print("-" * 60)
                
                # Show updated game state
                if self.use_gui and self.gui:
                    self.gui.update_display()
                else:
                    print("\\n🗺️  Updated Map:")
                    self.game_state.display_map(radius=4)
                
                # Check game status
                status = self.game_state.get_status()
                print(f"\\n📊 TURN {turn_count} RESULTS:")
                print(f"   📍 Position: {status['ship_position']}")
                print(f"   ❤️  Lives: {status['lives']}/3")
                print(f"   💰 Treasures: {status['treasures_collected']}/{status['total_treasures']} ({(status['treasures_collected']/status['total_treasures']*100):.1f}% complete)")
                print(f"   🎯 Mission Status: {'🏆 VICTORY ACHIEVED!' if self.game_state.victory else '💀 MISSION FAILED!' if self.game_state.lives <= 0 else '⚡ ONGOING'}")
                
                if self.game_state.victory:
                    if self.use_gui and self.gui:
                        self.gui.show_game_over_screen(victory=True)
                    else:
                        self._victory_screen()
                    break
                elif self.game_state.lives <= 0:
                    if self.use_gui and self.gui:
                        self.gui.show_game_over_screen(victory=False)
                    else:
                        self._game_over_screen()
                    break
                
                # Brief pause for readability
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\\n\\n⏸️  Game paused by user")
                if self._ask_continue():
                    continue
                else:
                    break
                    
            except Exception as e:
                print(f"\\n❌ Error during turn {turn_count}: {e}")
                if self._ask_continue():
                    continue
                else:
                    break
        
        # Check why the game ended
        if self.use_gui and self.gui and self.gui.game_stop_requested:
            print(f"\\n🛑 Game ended by user request after {turn_count - 1} turns")
        elif turn_count >= max_turns:
            print(f"\\n⏰ Game ended after {max_turns} turns (maximum reached)")
        
        self._end_game_summary()
    
    def _summarize_report(self, report: str) -> str:
        """Extract key information from agent report"""
        # This is a simple summary - in a real implementation you might
        # parse the JSON response more carefully
        if len(report) > 100:
            return report[:97] + "..."
        return report
    
    def _victory_screen(self):
        """Display victory screen"""
        print("\\n" + "🎉" * 20)
        print("🏆 VICTORY! ALL TREASURES COLLECTED! 🏆")
        print("🎉" * 20)
        print("\\nThe AI crew successfully navigated the treacherous waters")
        print("and collected all the treasures! Well done, Captain!")
        print(f"\\n📊 Final Stats:")
        print(f"   Turns taken: {self.game_state.turn_count}")
        print(f"   Lives remaining: {self.game_state.lives}")
        print(f"   Treasures collected: {self.game_state.treasures_collected}")
    
    def _game_over_screen(self):
        """Display game over screen"""
        print("\\n" + "💀" * 20)
        print("💀 GAME OVER - SHIP DESTROYED! 💀")  
        print("💀" * 20)
        print("\\nThe pirate ship has been destroyed by hostile forces.")
        print("Better luck next time, Captain!")
        print(f"\\n📊 Final Stats:")
        print(f"   Turns survived: {self.game_state.turn_count}")
        print(f"   Treasures collected: {self.game_state.treasures_collected}/{self.game_state.total_treasures}")
    
    def _end_game_summary(self):
        """Display end game summary"""
        print("\\n" + "="*60)
        print("🏴‍☠️ GAME SUMMARY 🏴‍☠️")
        print("="*60)
        status = self.game_state.get_status()
        print(f"Model used: {self.model_name}")
        print(f"Total turns: {status['turn_count']}")
        print(f"Treasures collected: {status['treasures_collected']}/{status['total_treasures']}")
        print(f"Final lives: {status['lives']}")
        print(f"Final position: {status['ship_position']}")
        
        if status['victory']:
            print("Result: 🏆 VICTORY!")
        elif status['lives'] <= 0:
            print("Result: 💀 DEFEAT")
        else:
            print("Result: ⏰ TIME LIMIT")
        
        print("\\nThank you for playing the AI Pirate Game!")
        
        # Close GUI if active
        if self.use_gui and self.gui:
            print("\\nPress Enter to close the GUI...")
            try:
                input()
            except:
                pass
            self.gui.close()
    
    def _ask_continue(self) -> bool:
        """Ask user if they want to continue after an error"""
        try:
            response = input("\\nContinue game? (y/n): ").strip().lower()
            return response in ['y', 'yes', '']
        except:
            return False

def main():
    """Main entry point"""
    try:
        game = PirateGame()
        
        if game.setup_game():
            game.play_game()
        else:
            print("❌ Failed to setup game. Exiting...")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n\\n👋 Goodbye, Captain!")
        if 'game' in locals() and hasattr(game, 'gui') and game.gui and hasattr(game.gui, 'stop_server'):
            game.gui.stop_server()
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        if 'game' in locals() and hasattr(game, 'gui') and game.gui and hasattr(game.gui, 'stop_server'):
            game.gui.stop_server()
        sys.exit(1)

if __name__ == "__main__":
    main()
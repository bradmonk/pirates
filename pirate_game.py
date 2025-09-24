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
        print("🏴‍☠️" + "=" * 60 + "🏴‍☠️")
        print("      Welcome to the AI Pirate Treasure Hunt!")
        print("🏴‍☠️" + "=" * 60 + "🏴‍☠️")
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
                if GUI_TYPE == "matplotlib" and hasattr(self.gui, "show"):
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
        while (
            not self.gui or not hasattr(self.gui, "selected_model") or not self.gui.selected_model
        ):
            time.sleep(1)
            if not self.gui or not self.gui.running:
                print("❌ Web interface not available!")
                return

        # Initialize agents with selected model
        model_name = self.gui.selected_model
        use_openai = is_openai_model(model_name)

        print(
            f"\\n🤖 Initializing AI agents with {'OpenAI' if use_openai else 'Ollama'} model: {model_name}"
        )

        # Get system prompts from GUI if available
        system_prompts = None
        if self.gui and hasattr(self.gui, "system_prompts"):
            system_prompts = self.gui.system_prompts

        self.agents = PirateGameAgents(
            self.game_state, model_name, use_openai, system_prompts, self.gui
        )

        print("\\n🚢 Setting sail...")
        print("\\n" + "=" * 80)

        # Show initial state
        if self.use_gui and self.gui:
            print("📱 GUI Display Active")
        else:
            self.game_state.display_map()

        turn_count = 0
        max_turns = 50  # Prevent infinite loops

        # Check if we're in step mode
        if self.use_gui and self.gui and hasattr(self.gui, "step_mode") and self.gui.step_mode:
            print("🔧 Running in STEP MODE - waiting for user input")
            print(
                f"🔍 Initial game state: game_over={self.game_state.game_over}, victory={self.game_state.victory}, lives={self.game_state.lives}"
            )
            self._run_step_mode(turn_count, max_turns)
        else:
            print("🚀 Running in CONTINUOUS MODE")
            self._run_continuous_mode(turn_count, max_turns)

    def _run_continuous_mode(self, turn_count: int, max_turns: int):
        """Run the game in continuous mode"""
        while not self.game_state.game_over and turn_count < max_turns:
            # Check if stop was requested via web UI
            if self.use_gui and self.gui and self.gui.game_stop_requested:
                print("\\n🛑 GAME STOP REQUESTED VIA WEB INTERFACE")
                print("🚢 Anchoring ship and ending voyage...")
                break

            # Check if system prompts were updated via web UI
            if self.use_gui and self.gui and hasattr(self.gui, "system_prompts") and self.agents:
                self.agents.update_system_prompts(self.gui.system_prompts)

            turn_count += 1
            result = self._execute_turn(turn_count)

            if result == "STOP":
                break
            elif result == "VICTORY":
                break
            elif result == "DEFEAT":
                break

            # Brief pause for readability
            time.sleep(1)

        # Final game summary
        self._handle_game_end(turn_count, max_turns)

    def _run_step_mode(self, turn_count: int, max_turns: int):
        """Run the game in step-by-step mode"""
        turn_in_progress = False

        while not self.game_state.game_over and turn_count < max_turns:
            # Check if stop was requested via web UI
            if self.use_gui and self.gui and self.gui.game_stop_requested:
                print("\\n🛑 GAME STOP REQUESTED VIA WEB INTERFACE")
                print("🚢 Anchoring ship and ending voyage...")
                break

            # If no turn in progress, wait for step command or start new turn
            if not turn_in_progress:
                # Wait for step ready signal
                print("🔄 Waiting for step ready signal...")
                wait_start = time.time()
                poll_count = 0

                while not (self.gui.step_ready and self.gui.game_started):
                    time.sleep(0.1)
                    poll_count += 1

                    # Debug: Print status every second
                    if poll_count % 10 == 0:
                        elapsed = time.time() - wait_start
                        print(
                            f"⏳ Still waiting for step signal... ({elapsed:.1f}s elapsed, step_ready={self.gui.step_ready}, game_started={self.gui.game_started})"
                        )

                    if self.gui.game_stop_requested:
                        print("🛑 Stop requested during step wait")
                        self._handle_game_end(turn_count, max_turns)
                        return

                wait_time = time.time() - wait_start
                print(f"✅ Step signal received after {wait_time:.2f} seconds")

                # Start new turn
                turn_count += 1
                print(f"\\n🔧 STEP MODE: Starting turn {turn_count}")
                self._start_turn(turn_count)

                # Initialize step mode in agents
                if self.agents:
                    self.agents.init_step_turn()

                turn_in_progress = True
                self.gui.step_ready = False  # Reset step signal

            else:
                # Wait for next step command
                while not self.gui.step_ready:
                    time.sleep(0.1)
                    if self.gui.game_stop_requested:
                        print("🛑 Stop requested during step execution wait")
                        self._handle_game_end(turn_count, max_turns)
                        return

                # Execute one step
                if self.agents:
                    step_result = self.agents.run_step()
                    print(f"🔍 Step result: {step_result['status']} - {step_result['message']}")

                    # Store step result for immediate UI updates
                    if self.gui:
                        self.gui.last_step_result = step_result.copy()
                        # If we have current step state, extract agent reports
                        if hasattr(self.agents, "step_state") and self.agents.step_state:
                            self.gui.last_step_result["agent_reports"] = self.agents.step_state[
                                "agent_reports"
                            ]
                            self.gui.last_step_result["game_status"] = self.agents.step_state[
                                "game_status"
                            ]

                    if step_result["status"] == "complete":
                        # Turn completed, process results
                        print("🔄 Processing turn results...")
                        result = self._process_turn_results(step_result["final_state"], turn_count)
                        turn_in_progress = False
                        print(f"🎯 Turn result: {result}")

                        # Store a special "turn_complete" result for the web interface
                        if self.gui:
                            self.gui.last_step_result = {
                                "status": "turn_complete",
                                "message": f"Turn {turn_count} completed",
                                "turn_result": result,
                                "final_state": step_result.get("final_state", {}),
                            }

                        if result in ["STOP", "VICTORY", "DEFEAT"]:
                            print(f"🛑 Game ending due to: {result}")
                            break

                    elif step_result["status"] == "error":
                        print(f"❌ Error in step mode: {step_result['message']}")
                        break

                    elif step_result["status"] == "stopped":
                        print("🛑 Step mode stopped by user")
                        break

                    else:
                        # Step completed but turn not finished yet
                        print(f"✅ Agent step completed: {step_result['message']}")

                self.gui.step_ready = False  # Reset step signal        # Final game summary
        self._handle_game_end(turn_count, max_turns)

    def _execute_turn(self, turn_count: int) -> str:
        """Execute a complete turn and return the result status"""
        self.game_state.turn_count = turn_count  # Keep game state turn counter in sync
        print(f"\\n{'='*30} TURN {turn_count} BEGINS {'='*30}")
        print(
            f"📍 Current Status: Position {self.game_state.ship_position.x},{self.game_state.ship_position.y} | Lives: {self.game_state.lives} | Treasures: {self.game_state.treasures_collected}/{self.game_state.total_treasures}"
        )
        print("=" * 80)

        # Draw cards for this turn
        if self.agents:
            cards = self.agents.draw_cards(turn_count)  # Pass current turn number
            print("=" * 80)

        # Check for any pre-existing position overlaps at start of turn
        pre_turn_collision = self.game_state.check_and_handle_position_overlaps()
        if pre_turn_collision:
            print(f"🚨 PRE-TURN COLLISION DETECTED: {pre_turn_collision}")

        try:
            # Capture pre-turn status for decision tracking
            pre_turn_status = self.game_state.get_status()

            # Let agents make decisions
            print("🤖 AI CREW DELIBERATION COMMENCING...")
            print("=" * 80)
            result = self.agents.run_turn()

            # Check if the agents indicated the game was stopped
            if result.get("decision") == "STOP_GAME" or result.get("last_action") == "GAME_STOPPED":
                print("🛑 GAME STOP DETECTED FROM AGENTS")
                print("🚢 Anchoring ship and ending voyage...")
                return "STOP"

            return self._process_turn_results(result, turn_count, pre_turn_status)

        except KeyboardInterrupt:
            print("\\n\\n⏸️  Game paused by user")
            if self._ask_continue():
                return "CONTINUE"
            else:
                return "STOP"

        except Exception as e:
            print(f"\\n❌ Error during turn {turn_count}: {e}")
            if self._ask_continue():
                return "CONTINUE"
            else:
                return "STOP"

    def _start_turn(self, turn_count: int):
        """Initialize a new turn (for step mode)"""
        self.game_state.turn_count = turn_count
        print(f"\\n{'='*30} TURN {turn_count} BEGINS {'='*30}")
        print(
            f"📍 Current Status: Position {self.game_state.ship_position.x},{self.game_state.ship_position.y} | Lives: {self.game_state.lives} | Treasures: {self.game_state.treasures_collected}/{self.game_state.total_treasures}"
        )
        print("=" * 80)

        # Draw cards for this turn
        if self.agents:
            cards = self.agents.draw_cards(turn_count)
            print("=" * 80)

        # Check for any pre-existing position overlaps at start of turn
        pre_turn_collision = self.game_state.check_and_handle_position_overlaps()
        if pre_turn_collision:
            print(f"🚨 PRE-TURN COLLISION DETECTED: {pre_turn_collision}")

    def _process_turn_results(self, result, turn_count: int, pre_turn_status=None) -> str:
        """Process the results of agent decisions and return status"""
        if pre_turn_status is None:
            pre_turn_status = self.game_state.get_status()

        print("=" * 80)
        print("🤖 AI CREW DELIBERATION COMPLETE")

        # Display comprehensive agent communications
        print("\\n📋 DETAILED CREW REPORTS:")
        print("-" * 60)
        for agent_name, report in result.get("agent_reports", {}).items():
            print(f"\\n{agent_name.upper()} FULL REPORT:")
            print("-" * 40)
            print(report)
            print("-" * 40)

        # Track the captain's decision and outcome for next turn's context
        captain_decision = result.get("decision", "No decision recorded")
        post_turn_status = self.game_state.get_status()
        if self.agents:
            self.agents.track_turn_decision(captain_decision, pre_turn_status, post_turn_status)

        # Move enemies and monsters toward the ship
        print("\\n👹 ENEMY MOVEMENT PHASE:")
        print("-" * 60)
        enemy_movements = self.game_state.move_enemies_and_monsters()
        if enemy_movements:
            for movement in enemy_movements:
                if movement.get("blocked", False):
                    print(
                        f"🚫 {movement['entity_type']} at {movement['from']} blocked by terrain (distance: {movement['distance_to_ship']} tiles)"
                    )
                elif movement.get("collision", False):
                    print(
                        f"💥 {movement['entity_type']} moved from {movement['from']} → {movement['to']} - COLLISION WITH SHIP!"
                    )
                    print(f"   {movement.get('message', 'Damage taken!')}")
                else:
                    print(
                        f"⚔️ {movement['entity_type']} moved from {movement['from']} → {movement['to']} (distance to ship: {movement['distance_to_ship']} tiles)"
                    )
        else:
            print("🏝️ No enemies within 5 tiles of ship - all quiet")
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
        print(
            f"   💰 Treasures: {status['treasures_collected']}/{status['total_treasures']} ({(status['treasures_collected']/status['total_treasures']*100):.1f}% complete)"
        )
        print(
            f"   🎯 Mission Status: {'🏆 VICTORY ACHIEVED!' if self.game_state.victory else '💀 MISSION FAILED!' if self.game_state.lives <= 0 else '⚡ ONGOING'}"
        )

        print(
            f"🔍 DEBUG - Game state check: victory={self.game_state.victory}, lives={self.game_state.lives}, game_over={self.game_state.game_over}"
        )

        if self.game_state.victory:
            print("🏆 VICTORY detected - ending game")
            if self.use_gui and self.gui:
                self.gui.show_game_over_screen(victory=True)
            else:
                self._victory_screen()
            return "VICTORY"
        elif self.game_state.lives <= 0:
            print("💀 DEFEAT detected - ending game")
            if self.use_gui and self.gui:
                self.gui.show_game_over_screen(victory=False)
            else:
                self._game_over_screen()
            return "DEFEAT"

        print("⚡ Game continuing...")
        return "CONTINUE"

    def _handle_game_end(self, turn_count: int, max_turns: int):
        """Handle the end of the game and show summary"""
        # Check why the game ended
        if self.use_gui and self.gui and self.gui.game_stop_requested:
            print(f"\\n🛑 Game ended by user request after {turn_count} turns")
        elif turn_count >= max_turns:
            print(f"\\n⏰ Game ended after {max_turns} turns (maximum reached)")

        self._end_game_summary(turn_count, max_turns)

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
        print(
            f"   Treasures collected: {self.game_state.treasures_collected}/{self.game_state.total_treasures}"
        )

    def _end_game_summary(self, actual_turns: int, max_turns: int):
        """Display end game summary"""
        print("\\n" + "=" * 60)
        print("🏴‍☠️ GAME SUMMARY 🏴‍☠️")
        print("=" * 60)
        status = self.game_state.get_status()
        print(f"Model used: {self.model_name}")
        print(f"Total turns: {actual_turns}")
        print(f"Treasures collected: {status['treasures_collected']}/{status['total_treasures']}")
        print(f"Final lives: {status['lives']}")
        print(f"Final position: {status['ship_position']}")

        # Determine end reason based on actual game flow, not just status
        if status["victory"]:
            print("Result: 🏆 VICTORY!")
        elif status["lives"] <= 0:
            print("Result: 💀 DEFEAT")
        elif actual_turns >= max_turns:
            print("Result: ⏰ TIME LIMIT")
        elif self.use_gui and self.gui and self.gui.game_stop_requested:
            print("Result: 🛑 USER STOPPED")
        else:
            print("Result: ❓ UNKNOWN (Game ended unexpectedly)")

        print("\\nThank you for playing the AI Pirate Game!")

        # Save transcript log if agents are available
        if hasattr(self, "agents") and self.agents:
            transcript_file = self.agents.save_transcript(status)
            if transcript_file:
                print(f"📝 Complete agent transcript saved to: {transcript_file}")

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
            return response in ["y", "yes", ""]
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
        if (
            "game" in locals()
            and hasattr(game, "gui")
            and game.gui
            and hasattr(game.gui, "stop_server")
        ):
            game.gui.stop_server()
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        if (
            "game" in locals()
            and hasattr(game, "gui")
            and game.gui
            and hasattr(game.gui, "stop_server")
        ):
            game.gui.stop_server()
        sys.exit(1)


if __name__ == "__main__":
    main()

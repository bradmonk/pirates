"""
Pirate Game - Tools for AI agents
"""

from typing import Dict, List, Tuple, Any
from game_state import GameState, Position, CellType


class NavigatorTool:
    """Tool for the Navigator agent to scan the environment"""

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def scan_surroundings(self, radius: int = 5) -> Dict[str, Any]:
        """Scan the area around the ship and return information about surroundings"""
        ship_pos = self.game_state.ship_position
        surrounding_cells = self.game_state.game_map.get_surrounding_cells(ship_pos, radius)

        # Categorize findings
        treasures = []
        enemies = []
        monsters = []
        land_obstacles = []
        safe_water = []

        def get_direction(from_pos, to_pos):
            """Convert coordinate difference to directional components"""
            dx = to_pos.x - from_pos.x
            dy = to_pos.y - from_pos.y

            # Build direction string showing both components if present
            direction_parts = []

            if dy < 0:  # North
                direction_parts.append(f"{abs(dy)}N")
            elif dy > 0:  # South
                direction_parts.append(f"{dy}S")

            if dx > 0:  # East
                direction_parts.append(f"{dx}E")
            elif dx < 0:  # West
                direction_parts.append(f"{abs(dx)}W")

            if len(direction_parts) == 2:
                return " + ".join(direction_parts)
            elif len(direction_parts) == 1:
                return direction_parts[0]
            else:
                return "same position"

        for pos, cell in surrounding_cells.items():
            # Skip the ship's current position
            if pos == ship_pos:
                continue

            # Check line of sight - skip items blocked by land
            if not self.game_state.game_map.has_line_of_sight(ship_pos, pos):
                continue

            distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
            direction = get_direction(ship_pos, pos)

            if cell == CellType.TREASURE.value:
                treasures.append({"direction": direction, "distance": distance})
            elif cell == CellType.ENEMY.value:
                enemies.append({"direction": direction, "distance": distance})
            elif cell == CellType.MONSTER.value:
                monsters.append({"direction": direction, "distance": distance})
            elif cell == CellType.LAND.value:
                land_obstacles.append({"direction": direction, "distance": distance})
            elif cell == CellType.WATER.value:
                safe_water.append({"direction": direction, "distance": distance})

        # Sort by distance
        treasures.sort(key=lambda x: x["distance"])
        enemies.sort(key=lambda x: x["distance"])
        monsters.sort(key=lambda x: x["distance"])

        scan_report = {
            "scan_radius": radius,
            "treasures_nearby": treasures,
            "enemies_nearby": enemies,
            "monsters_nearby": monsters,
            "land_obstacles": land_obstacles,
            "safe_water_positions": safe_water,
            "immediate_threats": [t for t in enemies + monsters if t["distance"] <= 1],
            "reachable_treasures": [t for t in treasures if t["distance"] <= 3],
            "summary": self._generate_scan_summary(treasures, enemies, monsters, land_obstacles),
        }

        return scan_report

    def _generate_scan_summary(self, treasures, enemies, monsters, obstacles) -> str:
        """Generate a text summary of the scan"""
        summary = []

        if treasures:
            closest_treasure = treasures[0]
            summary.append(
                f"Nearest treasure {closest_treasure['distance']} miles {closest_treasure['direction']}"
            )

        immediate_threats = [t for t in enemies + monsters if t["distance"] <= 1]
        if immediate_threats:
            summary.append(f"DANGER: {len(immediate_threats)} threat(s) within 1 mile!")

        nearby_threats = [t for t in enemies + monsters if 1 < t["distance"] <= 2]
        if nearby_threats:
            summary.append(f"{len(nearby_threats)} threat(s) within 2 miles")

        if not summary:
            summary.append("Area appears safe")

        return " | ".join(summary)


class CannoneerTool:
    """Tool for the Cannoneer agent to target and fire cannons"""

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def get_targets_in_range(self) -> List[Dict[str, Any]]:
        """Get all hostile targets within cannon range (5 tiles)"""
        ship_pos = self.game_state.ship_position
        targets = []

        # Check all positions within 5-tile radius (Manhattan distance)
        for dx in range(-5, 6):  # -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5
            for dy in range(-5, 6):
                # Skip ship's position
                if dx == 0 and dy == 0:
                    continue

                # Check if within 5-tile range (Manhattan distance)
                distance = abs(dx) + abs(dy)
                if distance > 5:
                    continue

                target_pos = Position(ship_pos.x + dx, ship_pos.y + dy)
                if self.game_state.game_map.is_valid_position(target_pos):
                    cell = self.game_state.game_map.get_cell(target_pos)
                    if cell in [CellType.ENEMY.value, CellType.MONSTER.value]:
                        # Calculate hit probability based on distance
                        hit_probabilities = {5: 0.25, 4: 0.50, 3: 0.75, 2: 0.90, 1: 0.95}
                        hit_chance = hit_probabilities.get(distance, 0.25)

                        # Get direction instead of coordinates
                        def get_direction(from_pos, to_pos):
                            dx = to_pos.x - from_pos.x
                            dy = to_pos.y - from_pos.y
                            if abs(dx) > abs(dy):
                                return "East" if dx > 0 else "West"
                            else:
                                return "South" if dy > 0 else "North"

                        direction = get_direction(ship_pos, target_pos)

                        targets.append(
                            {
                                "direction": direction,
                                "type": "Enemy" if cell == CellType.ENEMY.value else "Monster",
                                "threat_level": (
                                    "High" if cell == CellType.MONSTER.value else "Medium"
                                ),
                                "distance": distance,
                                "hit_chance": hit_chance,
                                # Internal coordinates for firing (not shown to agents)
                                "_position": (target_pos.x, target_pos.y),
                            }
                        )

        return targets

    def fire_cannon(self, target_x: int, target_y: int) -> Dict[str, Any]:
        """Fire cannon at specified coordinates"""
        target_pos = Position(target_x, target_y)
        ship_pos = self.game_state.ship_position

        # Check range (5 tiles)
        distance = abs(target_pos.x - ship_pos.x) + abs(target_pos.y - ship_pos.y)
        if distance > 5:
            return {
                "success": False,
                "message": f"Target at ({target_x}, {target_y}) is out of range (distance: {distance})",
                "range_limit": 5,
                "cannonballs_remaining": self.game_state.cannonballs,
            }

        # Check cannonball availability
        if self.game_state.cannonballs <= 0:
            return {
                "success": False,
                "message": "No cannonballs remaining! Collect treasures to get more ammunition.",
                "cannonballs_remaining": 0,
            }

        # Attempt to fire
        success, message = self.game_state.fire_cannon(target_pos)

        return {
            "success": success,
            "message": message,
            "target_destroyed": success,
            "cannonballs_remaining": self.game_state.cannonballs,
            "cannonballs_used": 1 if success else 0,
        }


class CaptainTool:
    """Tool for the Captain agent to move the ship"""

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def get_possible_moves(self) -> List[Dict[str, Any]]:
        """Get all possible moves from current position (up to 3 miles in cardinal directions)"""
        ship_pos = self.game_state.ship_position
        possible_moves = []

        # Check moves in 4 cardinal directions up to 3 miles each
        directions = [(0, -1, "North"), (0, 1, "South"), (-1, 0, "West"), (1, 0, "East")]

        for base_dx, base_dy, direction_name in directions:
            # Check moves of 1, 2, and 3 miles in this direction
            for distance in range(1, 4):  # 1, 2, 3 miles
                dx = base_dx * distance
                dy = base_dy * distance
                target_pos = Position(ship_pos.x + dx, ship_pos.y + dy)

                # Check if this move is possible
                if self.game_state.game_map.is_valid_position(target_pos):
                    path_clear, message, path = self.game_state.game_map.is_path_clear(
                        ship_pos, target_pos
                    )

                    if path_clear:
                        # Analyze what's along the path
                        encounters = []
                        treasures_count = 0
                        enemies_count = 0
                        monsters_count = 0

                        for step_pos in path:
                            cell = self.game_state.game_map.get_cell(step_pos)
                            if cell == CellType.TREASURE.value:
                                treasures_count += 1
                                encounters.append(f"Treasure at ({step_pos.x},{step_pos.y})")
                            elif cell == CellType.ENEMY.value:
                                enemies_count += 1
                                encounters.append(f"Enemy at ({step_pos.x},{step_pos.y})")
                            elif cell == CellType.MONSTER.value:
                                monsters_count += 1
                                encounters.append(f"Monster at ({step_pos.x},{step_pos.y})")

                        # Assess risk level
                        if monsters_count > 0:
                            risk_level = f"Very Dangerous - {monsters_count} Monster(s)"
                        elif enemies_count > 0:
                            risk_level = f"Dangerous - {enemies_count} Enemy(s)"
                        elif treasures_count > 0:
                            risk_level = f"Rewarding - {treasures_count} Treasure(s)"
                        else:
                            risk_level = "Safe"

                        # Map direction to command format
                        direction_letters = {"North": "N", "South": "S", "East": "E", "West": "W"}
                        command_format = f"@{distance}{direction_letters[direction_name]}"

                        possible_moves.append(
                            {
                                "direction": (dx, dy),
                                "direction_name": f"{command_format} ({distance} miles {direction_name})",
                                "command_format": command_format,
                                "target_position": f"{distance} miles {direction_name.lower()}",
                                "distance": distance,
                                "can_move": True,
                                "path": [(pos.x, pos.y) for pos in path],
                                "encounters": encounters,
                                "risk_assessment": risk_level,
                                "treasures_on_path": treasures_count,
                                "enemies_on_path": enemies_count,
                                "monsters_on_path": monsters_count,
                            }
                        )
                    else:
                        # Path is blocked - still show command format
                        direction_letters = {"North": "N", "South": "S", "East": "E", "West": "W"}
                        command_format = f"@{distance}{direction_letters[direction_name]}"

                        possible_moves.append(
                            {
                                "direction": (dx, dy),
                                "direction_name": f"{command_format} ({distance} miles {direction_name})",
                                "command_format": command_format,
                                "target_position": f"{distance} miles {direction_name.lower()}",
                                "distance": distance,
                                "can_move": False,
                                "blocked_reason": message,
                                "risk_assessment": "Blocked",
                            }
                        )
                else:
                    # Target position is off the map - still show command format
                    direction_letters = {"North": "N", "South": "S", "East": "E", "West": "W"}
                    command_format = f"@{distance}{direction_letters[direction_name]}"

                    possible_moves.append(
                        {
                            "direction": (dx, dy),
                            "direction_name": f"{command_format} ({distance} miles {direction_name})",
                            "command_format": command_format,
                            "target_position": f"{distance} miles {direction_name.lower()}",
                            "distance": distance,
                            "can_move": False,
                            "blocked_reason": "Position is outside map boundaries",
                            "risk_assessment": "Off Map",
                        }
                    )

        return possible_moves

    def move_ship(self, direction_x: int, direction_y: int) -> Dict[str, Any]:
        """Move the ship in the specified direction (up to 3 miles)"""
        old_pos = (self.game_state.ship_position.x, self.game_state.ship_position.y)
        old_lives = self.game_state.lives
        old_treasures = self.game_state.treasures_collected
        old_cannonballs = self.game_state.cannonballs

        success, message, move_data = self.game_state.move_ship((direction_x, direction_y))

        if not success:
            return {
                "success": False,
                "reason": "illegal_move",
                "message": message,
                "current_position": old_pos,
                "attempted_move": (direction_x, direction_y),
                "turn_count": self.game_state.turn_count,
            }

        # Successful move - extract detailed information
        result = {
            "success": True,
            "message": message,
            "old_position": old_pos,
            "new_position": (self.game_state.ship_position.x, self.game_state.ship_position.y),
            "path_taken": move_data.get("path", []),
            "encounters": move_data.get("encounters", []),
            "lives_lost": old_lives - self.game_state.lives,
            "treasures_gained": move_data.get("treasures_collected", 0),
            "cannonballs_gained": self.game_state.cannonballs - old_cannonballs,
            "total_cannonballs": self.game_state.cannonballs,
            "turn_count": self.game_state.turn_count,
            "game_over": self.game_state.game_over,
            "victory": self.game_state.victory,
        }

        # Add detailed summary of the move
        if result["encounters"]:
            encounter_summary = []
            for encounter in result["encounters"]:
                encounter_summary.append(
                    f"{encounter['type']} at {encounter['position']}: {encounter['result']}"
                )
            result["encounter_summary"] = encounter_summary

        return result


class GameTools:
    """Container for all game tools"""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.navigator = NavigatorTool(game_state)
        self.cannoneer = CannoneerTool(game_state)
        self.captain = CaptainTool(game_state)

    def get_game_status(self) -> Dict[str, Any]:
        """Get comprehensive game status"""
        return {
            **self.game_state.get_status(),
            "scan_report": self.navigator.scan_surroundings(),
            "available_targets": self.cannoneer.get_targets_in_range(),
            "possible_moves": self.captain.get_possible_moves(),
        }


if __name__ == "__main__":
    # Quick test of the tools
    from game_state import GameState

    game = GameState()
    tools = GameTools(game)

    print("=== NAVIGATOR SCAN ===")
    scan = tools.navigator.scan_surroundings()
    print(f"Summary: {scan['summary']}")
    print(f"Treasures: {len(scan['treasures_nearby'])}")
    print(f"Enemies: {len(scan['enemies_nearby'])}")
    print(f"Immediate threats: {len(scan['immediate_threats'])}")

    print("\n=== CANNONEER TARGETS ===")
    targets = tools.cannoneer.get_targets_in_range()
    print(f"Targets in range: {len(targets)}")
    for target in targets:
        print(f"  - {target['type']} at {target['position']} ({target['threat_level']} threat)")

    print("\n=== CAPTAIN MOVES ===")
    moves = tools.captain.get_possible_moves()
    safe_moves = [m for m in moves if m["can_move"] and "Safe" in m["risk_assessment"]]
    print(f"Safe moves available: {len(safe_moves)}")
    for move in safe_moves[:3]:  # Show first 3 safe moves
        print(f"  - {move['direction_name']}: {move['risk_assessment']}")

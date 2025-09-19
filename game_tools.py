"""
Pirate Game - Tools for AI agents
"""
from typing import Dict, List, Tuple, Any
from game_state import GameState, Position, CellType

class NavigatorTool:
    """Tool for the Navigator agent to scan the environment"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def scan_surroundings(self, radius: int = 3) -> Dict[str, Any]:
        """Scan the area around the ship and return information about surroundings"""
        ship_pos = self.game_state.ship_position
        surrounding_cells = self.game_state.game_map.get_surrounding_cells(ship_pos, radius)
        
        # Categorize findings
        treasures = []
        enemies = []
        monsters = []
        land_obstacles = []
        safe_water = []
        
        for pos, cell in surrounding_cells.items():
            # Skip the ship's current position
            if pos == ship_pos:
                continue
                
            if cell == CellType.TREASURE.value:
                distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
                treasures.append({"position": (pos.x, pos.y), "distance": distance})
            elif cell == CellType.ENEMY.value:
                distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
                enemies.append({"position": (pos.x, pos.y), "distance": distance})
            elif cell == CellType.MONSTER.value:
                distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
                monsters.append({"position": (pos.x, pos.y), "distance": distance})
            elif cell == CellType.LAND.value:
                distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
                land_obstacles.append({"position": (pos.x, pos.y), "distance": distance})
            elif cell == CellType.WATER.value:
                distance = abs(pos.x - ship_pos.x) + abs(pos.y - ship_pos.y)
                safe_water.append({"position": (pos.x, pos.y), "distance": distance})
        
        # Sort by distance
        treasures.sort(key=lambda x: x["distance"])
        enemies.sort(key=lambda x: x["distance"])
        monsters.sort(key=lambda x: x["distance"])
        
        scan_report = {
            "ship_position": (ship_pos.x, ship_pos.y),
            "scan_radius": radius,
            "treasures_nearby": treasures,
            "enemies_nearby": enemies,
            "monsters_nearby": monsters,
            "land_obstacles": land_obstacles,
            "safe_water_positions": safe_water,
            "immediate_threats": [t for t in enemies + monsters if t["distance"] <= 1],
            "reachable_treasures": [t for t in treasures if t["distance"] <= 2],
            "summary": self._generate_scan_summary(treasures, enemies, monsters, land_obstacles)
        }
        
        return scan_report
    
    def _generate_scan_summary(self, treasures, enemies, monsters, obstacles) -> str:
        """Generate a text summary of the scan"""
        summary = []
        
        if treasures:
            closest_treasure = treasures[0]
            summary.append(f"Nearest treasure at distance {closest_treasure['distance']} at {closest_treasure['position']}")
        
        immediate_threats = [t for t in enemies + monsters if t["distance"] <= 1]
        if immediate_threats:
            summary.append(f"DANGER: {len(immediate_threats)} threat(s) within attack range!")
        
        nearby_threats = [t for t in enemies + monsters if 1 < t["distance"] <= 2]
        if nearby_threats:
            summary.append(f"{len(nearby_threats)} threat(s) nearby")
        
        if not summary:
            summary.append("Area appears safe")
        
        return " | ".join(summary)

class CannoneerTool:
    """Tool for the Cannoneer agent to target and fire cannons"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def get_targets_in_range(self) -> List[Dict[str, Any]]:
        """Get all hostile targets within cannon range (2 tiles)"""
        ship_pos = self.game_state.ship_position
        targets = []
        
        # Check all positions within 2-tile radius (Manhattan distance)
        for dx in range(-2, 3):  # -2, -1, 0, 1, 2
            for dy in range(-2, 3):
                # Skip ship's position
                if dx == 0 and dy == 0:
                    continue
                
                # Check if within 2-tile range (Manhattan distance)
                distance = abs(dx) + abs(dy)
                if distance > 2:
                    continue
                
                target_pos = Position(ship_pos.x + dx, ship_pos.y + dy)
                if self.game_state.game_map.is_valid_position(target_pos):
                    cell = self.game_state.game_map.get_cell(target_pos)
                    if cell in [CellType.ENEMY.value, CellType.MONSTER.value]:
                        targets.append({
                            "position": (target_pos.x, target_pos.y),
                            "type": "Enemy" if cell == CellType.ENEMY.value else "Monster",
                            "threat_level": "High" if cell == CellType.MONSTER.value else "Medium"
                        })
        
        return targets
    
    def fire_cannon(self, target_x: int, target_y: int) -> Dict[str, Any]:
        """Fire cannon at specified coordinates"""
        target_pos = Position(target_x, target_y)
        ship_pos = self.game_state.ship_position
        
        # Check range (2 tiles)
        distance = abs(target_pos.x - ship_pos.x) + abs(target_pos.y - ship_pos.y)
        if distance > 2:
            return {
                "success": False,
                "message": f"Target at ({target_x}, {target_y}) is out of range (distance: {distance})",
                "range_limit": 2,
                "cannonballs_remaining": self.game_state.cannonballs
            }
        
        # Check cannonball availability
        if self.game_state.cannonballs <= 0:
            return {
                "success": False,
                "message": "No cannonballs remaining! Collect treasures to get more ammunition.",
                "cannonballs_remaining": 0
            }
        
        # Attempt to fire
        success, message = self.game_state.fire_cannon(target_pos)
        
        return {
            "success": success,
            "message": message,
            "target_destroyed": success,
            "cannonballs_remaining": self.game_state.cannonballs,
            "cannonballs_used": 1 if success else 0
        }

class CaptainTool:
    """Tool for the Captain agent to move the ship"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def get_possible_moves(self) -> List[Dict[str, Any]]:
        """Get all possible moves from current position (up to 3 tiles in cardinal directions)"""
        ship_pos = self.game_state.ship_position
        possible_moves = []
        
        # Check moves in 4 cardinal directions up to 3 tiles each
        directions = [
            (0, -1, "North"), (0, 1, "South"), (-1, 0, "West"), (1, 0, "East")
        ]
        
        for base_dx, base_dy, direction_name in directions:
            # Check moves of 1, 2, and 3 tiles in this direction
            for distance in range(1, 4):  # 1, 2, 3 tiles
                dx = base_dx * distance
                dy = base_dy * distance
                target_pos = Position(ship_pos.x + dx, ship_pos.y + dy)
                
                # Check if this move is possible
                if self.game_state.game_map.is_valid_position(target_pos):
                    path_clear, message, path = self.game_state.game_map.is_path_clear(ship_pos, target_pos)
                    
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
                        
                        possible_moves.append({
                            "direction": (dx, dy),
                            "direction_name": f"{direction_name} {distance} tile(s)",
                            "target_position": (target_pos.x, target_pos.y),
                            "distance": distance,
                            "can_move": True,
                            "path": [(pos.x, pos.y) for pos in path],
                            "encounters": encounters,
                            "risk_assessment": risk_level,
                            "treasures_on_path": treasures_count,
                            "enemies_on_path": enemies_count,
                            "monsters_on_path": monsters_count
                        })
                    else:
                        # Path is blocked
                        possible_moves.append({
                            "direction": (dx, dy),
                            "direction_name": f"{direction_name} {distance} tile(s)",
                            "target_position": (target_pos.x, target_pos.y),
                            "distance": distance,
                            "can_move": False,
                            "blocked_reason": message,
                            "risk_assessment": "Blocked"
                        })
                else:
                    # Target position is off the map
                    possible_moves.append({
                        "direction": (dx, dy),
                        "direction_name": f"{direction_name} {distance} tile(s)",
                        "target_position": (target_pos.x, target_pos.y),
                        "distance": distance,
                        "can_move": False,
                        "blocked_reason": "Position is outside map boundaries",
                        "risk_assessment": "Off Map"
                    })
        
        return possible_moves
    
    def move_ship(self, direction_x: int, direction_y: int) -> Dict[str, Any]:
        """Move the ship in the specified direction (up to 3 tiles)"""
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
                "turn_count": self.game_state.turn_count
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
            "victory": self.game_state.victory
        }
        
        # Add detailed summary of the move
        if result["encounters"]:
            encounter_summary = []
            for encounter in result["encounters"]:
                encounter_summary.append(f"{encounter['type']} at {encounter['position']}: {encounter['result']}")
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
            "possible_moves": self.captain.get_possible_moves()
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
    safe_moves = [m for m in moves if m['can_move'] and 'Safe' in m['risk_assessment']]
    print(f"Safe moves available: {len(safe_moves)}")
    for move in safe_moves[:3]:  # Show first 3 safe moves
        print(f"  - {move['direction_name']}: {move['risk_assessment']}")
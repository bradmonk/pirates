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
        """Get all hostile targets within cannon range (1 tile)"""
        ship_pos = self.game_state.ship_position
        targets = []
        
        # Check all adjacent positions (cannon range = 1)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:  # Skip ship's position
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
        
        # Check range
        distance = abs(target_pos.x - ship_pos.x) + abs(target_pos.y - ship_pos.y)
        if distance > 1:
            return {
                "success": False,
                "message": f"Target at ({target_x}, {target_y}) is out of range (distance: {distance})",
                "range_limit": 1
            }
        
        # Attempt to fire
        success = self.game_state.fire_cannon(target_pos)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully destroyed target at ({target_x}, {target_y})",
                "target_destroyed": True
            }
        else:
            cell = self.game_state.game_map.get_cell(target_pos)
            return {
                "success": False,
                "message": f"No valid target at ({target_x}, {target_y}). Found: {cell}",
                "target_destroyed": False
            }

class CaptainTool:
    """Tool for the Captain agent to move the ship"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def get_possible_moves(self) -> List[Dict[str, Any]]:
        """Get all possible moves from current position"""
        ship_pos = self.game_state.ship_position
        possible_moves = []
        
        # Check all 8 directions (including diagonals)
        directions = [
            (-1, -1, "Northwest"), (-1, 0, "North"), (-1, 1, "Northeast"),
            (0, -1, "West"), (0, 1, "East"),
            (1, -1, "Southwest"), (1, 0, "South"), (1, 1, "Southeast")
        ]
        
        for dx, dy, name in directions:
            new_pos = Position(ship_pos.x + dx, ship_pos.y + dy)
            
            if self.game_state.game_map.is_valid_position(new_pos):
                cell = self.game_state.game_map.get_cell(new_pos)
                can_move = self.game_state.game_map.can_move_to(new_pos)
                
                risk_level = "Safe"
                if cell == CellType.ENEMY.value:
                    risk_level = "Dangerous - Enemy"
                elif cell == CellType.MONSTER.value:
                    risk_level = "Very Dangerous - Monster"
                elif cell == CellType.TREASURE.value:
                    risk_level = "Rewarding - Treasure"
                
                possible_moves.append({
                    "direction": (dx, dy),
                    "direction_name": name,
                    "position": (new_pos.x, new_pos.y),
                    "can_move": can_move,
                    "cell_type": cell,
                    "risk_assessment": risk_level
                })
        
        return possible_moves
    
    def move_ship(self, direction_x: int, direction_y: int) -> Dict[str, Any]:
        """Move the ship in the specified direction"""
        old_pos = (self.game_state.ship_position.x, self.game_state.ship_position.y)
        old_lives = self.game_state.lives
        old_treasures = self.game_state.treasures_collected
        
        success = self.game_state.move_ship((direction_x, direction_y))
        
        if success:
            new_pos = (self.game_state.ship_position.x, self.game_state.ship_position.y)
            lives_lost = old_lives - self.game_state.lives
            treasures_gained = self.game_state.treasures_collected - old_treasures
            
            result = {
                "success": True,
                "old_position": old_pos,
                "new_position": new_pos,
                "lives_lost": lives_lost,
                "treasures_gained": treasures_gained,
                "turn_count": self.game_state.turn_count,
                "game_over": self.game_state.game_over,
                "victory": self.game_state.victory
            }
            
            if treasures_gained > 0:
                result["message"] = f"Moved to {new_pos} and collected treasure!"
            elif lives_lost > 0:
                result["message"] = f"Moved to {new_pos} but took damage from hostile!"
            else:
                result["message"] = f"Successfully moved to {new_pos}"
                
            return result
        else:
            return {
                "success": False,
                "message": "Cannot move in that direction - blocked by land or invalid position",
                "current_position": old_pos
            }

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
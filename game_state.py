"""
Pirate Game - Core game logic and state management
"""
import csv
import random
from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

class CellType(Enum):
    """Enum for different cell types on the map"""
    WATER = 'W'
    LAND = 'L'
    TREASURE = 'T'
    ENEMY = 'E'
    MONSTER = 'M'
    OWNSHIP = 'O'

@dataclass(frozen=True)
class Position:
    """Represents a position on the game map"""
    x: int
    y: int
    
    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

class GameMap:
    """Handles loading and managing the game map"""
    
    def __init__(self, csv_path: str = "map.csv"):
        self.csv_path = csv_path
        self.grid = None
        self.width = 0
        self.height = 0
        self.load_map()
    
    def load_map(self):
        """Load the map from CSV file"""
        try:
            with open(self.csv_path, 'r') as file:
                csv_reader = csv.reader(file)
                self.grid = [row for row in csv_reader]
            self.height = len(self.grid)
            self.width = len(self.grid[0]) if self.grid else 0
            print(f"Loaded map: {self.width}x{self.height}")
        except Exception as e:
            print(f"Error loading map: {e}")
            raise
    
    def get_cell(self, pos: Position) -> str:
        """Get the content of a cell at the given position"""
        if self.is_valid_position(pos):
            return self.grid[pos.y][pos.x]
        return None
    
    def set_cell(self, pos: Position, value: str):
        """Set the content of a cell at the given position"""
        if self.is_valid_position(pos):
            self.grid[pos.y][pos.x] = value
    
    def is_valid_position(self, pos: Position) -> bool:
        """Check if a position is within the map boundaries"""
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height
    
    def can_move_to(self, pos: Position) -> bool:
        """Check if the ship can move to this position (not land)"""
        if not self.is_valid_position(pos):
            return False
        cell = self.get_cell(pos)
        return cell != CellType.LAND.value
    
    def is_path_clear(self, start: Position, end: Position) -> Tuple[bool, str, List[Position]]:
        """Check if there's a clear path from start to end position, allowing only orthogonal moves"""
        # Calculate the path - only allow moves in cardinal directions (no diagonal)
        dx = end.x - start.x
        dy = end.y - start.y
        
        # Check if move distance is valid (max 3 tiles)
        distance = abs(dx) + abs(dy)
        if distance > 3:
            return False, f"Move distance ({distance}) exceeds maximum of 3 tiles", []
        
        # For now, we'll implement a simple path: move all X first, then all Y
        # In a more sophisticated version, we could implement A* pathfinding
        path = [start]
        current = start
        
        # Move horizontally first
        x_step = 1 if dx > 0 else -1 if dx < 0 else 0
        for _ in range(abs(dx)):
            current = Position(current.x + x_step, current.y)
            if not self.can_move_to(current):
                blocked_cell = self.get_cell(current)
                return False, f"Path blocked by {blocked_cell} at ({current.x}, {current.y})", []
            path.append(current)
        
        # Move vertically
        y_step = 1 if dy > 0 else -1 if dy < 0 else 0
        for _ in range(abs(dy)):
            current = Position(current.x, current.y + y_step)
            if not self.can_move_to(current):
                blocked_cell = self.get_cell(current)
                return False, f"Path blocked by {blocked_cell} at ({current.x}, {current.y})", []
            path.append(current)
        
        return True, "Path is clear", path[1:]  # Exclude starting position
    
    def get_surrounding_cells(self, pos: Position, radius: int = 3) -> Dict[Position, str]:
        """Get all cells within radius of the given position"""
        surrounding = {}
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                check_pos = Position(pos.x + dx, pos.y + dy)
                if self.is_valid_position(check_pos):
                    surrounding[check_pos] = self.get_cell(check_pos)
        return surrounding
    
    def find_cell_type(self, cell_type: CellType) -> List[Position]:
        """Find all positions containing a specific cell type"""
        positions = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == cell_type.value:
                    positions.append(Position(x, y))
        return positions
    
    def get_map_display(self) -> List[List[str]]:
        """Get the current map grid for display purposes"""
        return self.grid

class GameState:
    """Manages the overall game state"""
    
    def __init__(self, map_path: str = "map.csv"):
        self.game_map = GameMap(map_path)
        self.ship_position = self._find_initial_ship_position()
        self.treasures_collected = 0
        self.lives = 3
        self.cannonballs = 25  # Start with 25 cannonballs
        self.score = 0  # Score tracking system
        self.enemies_defeated = 0  # Track enemies defeated
        self.monsters_defeated = 0  # Track monsters defeated
        self.turn_count = 0
        self.game_over = False
        self.victory = False
        
        # Remove the ship marker from the map and replace with water
        self.game_map.set_cell(self.ship_position, CellType.WATER.value)
        
        # Count initial treasures
        self.total_treasures = len(self.game_map.find_cell_type(CellType.TREASURE))
    
    def _find_initial_ship_position(self) -> Position:
        """Find the initial ship position from the map"""
        ship_positions = self.game_map.find_cell_type(CellType.OWNSHIP)
        if not ship_positions:
            raise ValueError("No ship position (O) found on the map!")
        return ship_positions[0]  # Take the first ship position
    
    def move_ship(self, direction: Tuple[int, int]) -> Tuple[bool, str, Dict[str, Any]]:
        """Move the ship in the given direction (dx, dy) up to 3 tiles"""
        target_position = Position(
            self.ship_position.x + direction[0],
            self.ship_position.y + direction[1]
        )
        
        # Check if the path is clear
        path_clear, message, path = self.game_map.is_path_clear(self.ship_position, target_position)
        
        if not path_clear:
            return False, message, {"reason": "illegal_move", "message": message}
        
        # If path is clear, move through each step and collect items/handle encounters
        move_results = {
            "success": True,
            "old_position": (self.ship_position.x, self.ship_position.y),
            "path": [(pos.x, pos.y) for pos in path],
            "encounters": [],
            "treasures_collected": 0,
            "damage_taken": 0,
            "final_position": (target_position.x, target_position.y)
        }
        
        for step_pos in path:
            cell_content = self.game_map.get_cell(step_pos)
            
            # Handle encounters at each step
            if cell_content == CellType.TREASURE.value:
                old_treasures = self.treasures_collected
                old_cannonballs = self.cannonballs
                self.collect_treasure(step_pos)
                move_results["encounters"].append({
                    "position": (step_pos.x, step_pos.y),
                    "type": "treasure",
                    "result": f"Collected treasure! Gained 2 cannonballs."
                })
                move_results["treasures_collected"] += 1
                
            elif cell_content == CellType.ENEMY.value:
                old_lives = self.lives
                self.take_damage()
                damage = old_lives - self.lives
                self.game_map.set_cell(step_pos, CellType.WATER.value)
                move_results["encounters"].append({
                    "position": (step_pos.x, step_pos.y),
                    "type": "enemy",
                    "result": f"Engaged enemy! Lost {damage} life."
                })
                move_results["damage_taken"] += damage
                
            elif cell_content == CellType.MONSTER.value:
                old_lives = self.lives
                self.take_damage()
                damage = old_lives - self.lives
                self.game_map.set_cell(step_pos, CellType.WATER.value)
                move_results["encounters"].append({
                    "position": (step_pos.x, step_pos.y),
                    "type": "monster", 
                    "result": f"Fought monster! Lost {damage} life."
                })
                move_results["damage_taken"] += damage
        
        # Move the ship to final position
        self.ship_position = target_position
        self.turn_count += 1
        
        # Check for any enemies occupying the same tile as the ship after movement
        collision_detected = self.check_and_handle_position_overlaps()
        if collision_detected:
            success_message += f" | COLLISION DETECTED: {collision_detected}"
        
        # Check victory condition
        if self.treasures_collected >= self.total_treasures:
            self.victory = True
            self.game_over = True
            
        # Check game over condition
        if self.lives <= 0:
            self.game_over = True
        
        success_message = f"Successfully moved to {target_position.x},{target_position.y}"
        if move_results["encounters"]:
            success_message += f" with {len(move_results['encounters'])} encounters"
            
        return True, success_message, move_results
    
    def get_movement_animation_data(self, direction: Tuple[int, int]) -> Dict[str, Any]:
        """Get detailed animation data for multi-tile movement including each step"""
        target_position = Position(
            self.ship_position.x + direction[0],
            self.ship_position.y + direction[1]
        )
        
        # Check if the path is clear
        path_clear, message, path = self.game_map.is_path_clear(self.ship_position, target_position)
        
        if not path_clear:
            return {"success": False, "error": message, "steps": []}
        
        # Build animation steps data
        animation_data = {
            "success": True,
            "total_steps": len(path) - 1,  # Don't count starting position
            "steps": []
        }
        
        for i, step_pos in enumerate(path):
            if i == 0:  # Skip starting position
                continue
                
            cell_content = self.game_map.get_cell(step_pos)
            step_data = {
                "step_number": i,
                "position": (step_pos.x, step_pos.y),
                "cell_type": cell_content,
                "encounter": None,
                "delay_ms": 400  # Pause duration between steps
            }
            
            # Determine what happens at this step
            if cell_content == CellType.TREASURE.value:
                step_data["encounter"] = {
                    "type": "treasure",
                    "message": "Collected treasure! +2 cannonballs"
                }
            elif cell_content == CellType.ENEMY.value:
                step_data["encounter"] = {
                    "type": "enemy", 
                    "message": "Engaged enemy! -1 life"
                }
            elif cell_content == CellType.MONSTER.value:
                step_data["encounter"] = {
                    "type": "monster",
                    "message": "Fought monster! -1 life"
                }
                
            animation_data["steps"].append(step_data)
        
        return animation_data
    
    def collect_treasure(self, pos: Position):
        """Collect treasure at the given position"""
        self.treasures_collected += 1
        self.cannonballs += 2  # Reward 2 cannonballs per treasure
        self.score += 10  # Add 10 points for treasure
        self.game_map.set_cell(pos, CellType.WATER.value)
        print(f"🏆 Treasure collected! Total: {self.treasures_collected}/{self.total_treasures}")
        print(f"💰 Rewarded with 2 cannonballs! Total: {self.cannonballs} cannonballs")
        print(f"⭐ +10 points! Score: {self.score}")
    
    def take_damage(self):
        """Ship takes damage from enemy or monster"""
        self.lives -= 1
        print(f"💥 Ship damaged! Lives remaining: {self.lives}")
        if self.lives <= 0:
            self.game_over = True
            print("💀 Game Over - Ship destroyed!")
    
    def fire_cannon(self, target_pos: Position) -> Tuple[bool, str]:
        """Fire cannon at target position with probabilistic hit system"""
        # Check if we have cannonballs
        if self.cannonballs <= 0:
            return False, "No cannonballs remaining! Collect treasures to get more ammunition."
        
        # Check if target is within range (5 tile radius)
        distance = abs(target_pos.x - self.ship_position.x) + abs(target_pos.y - self.ship_position.y)
        if distance > 5:
            return False, f"Target too far - cannons have range of 5 tiles (target distance: {distance})"
        
        cell_content = self.game_map.get_cell(target_pos)
        if cell_content in [CellType.ENEMY.value, CellType.MONSTER.value]:
            # Consume a cannonball
            self.cannonballs -= 1
            
            # Calculate hit probability based on distance
            hit_probabilities = {5: 0.25, 4: 0.50, 3: 0.75, 2: 0.90, 1: 0.95}
            hit_chance = hit_probabilities.get(distance, 0.25)
            
            # Roll for hit
            if random.random() <= hit_chance:
                # Hit! Destroy target and award points
                self.game_map.set_cell(target_pos, CellType.WATER.value)
                target_type = "Enemy" if cell_content == CellType.ENEMY.value else "Monster"
                
                if cell_content == CellType.ENEMY.value:
                    self.enemies_defeated += 1
                    self.score += 10  # +10 points for enemy
                    points_msg = "+10 points"
                else:  # Monster
                    self.monsters_defeated += 1
                    self.score += 50  # +50 points for monster
                    points_msg = "+50 points"
                
                success_message = f"💥 Direct hit! {target_type} destroyed at {target_pos.x},{target_pos.y}! {points_msg}! Score: {self.score}. Cannonballs remaining: {self.cannonballs}"
                print(success_message)
                return True, success_message
            else:
                # Miss!
                miss_message = f"💦 Cannon fire missed target at {target_pos.x},{target_pos.y} (hit chance: {hit_chance:.0%}). Cannonballs remaining: {self.cannonballs}"
                print(miss_message)
                return False, miss_message
        else:
            # Consume cannonball even for invalid targets (shot was fired)
            self.cannonballs -= 1
            return False, f"💦 Cannon fired at empty water at ({target_pos.x},{target_pos.y}). Cannonballs remaining: {self.cannonballs}"
    
    def move_enemies_and_monsters(self) -> List[Dict]:
        """Move enemies and monsters toward the ship if within 3 tiles"""
        movements = []
        
        # Find all enemies and monsters on the map
        entities_to_move = []
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                cell = self.game_map.get_cell(Position(x, y))
                if cell in [CellType.ENEMY.value, CellType.MONSTER.value]:
                    entities_to_move.append({
                        'position': Position(x, y),
                        'type': cell
                    })
        
        for entity in entities_to_move:
            current_pos = entity['position']
            entity_type = entity['type']
            
            # Calculate distance to ship
            dx = self.ship_position.x - current_pos.x
            dy = self.ship_position.y - current_pos.y
            distance = max(abs(dx), abs(dy))  # Chebyshev distance (max of x,y differences)
            
            # Only move if within 3 tiles of the ship
            if distance <= 3:
                # Determine the best direction to move (one tile toward ship)
                move_x = 0
                move_y = 0
                
                if dx != 0:
                    move_x = 1 if dx > 0 else -1
                if dy != 0:
                    move_y = 1 if dy > 0 else -1
                
                # Try multiple movement options in order of preference
                movement_options = []
                
                # Primary: diagonal move toward ship
                if move_x != 0 and move_y != 0:
                    movement_options.append(Position(current_pos.x + move_x, current_pos.y + move_y))
                
                # Secondary: horizontal move toward ship
                if move_x != 0:
                    movement_options.append(Position(current_pos.x + move_x, current_pos.y))
                
                # Tertiary: vertical move toward ship
                if move_y != 0:
                    movement_options.append(Position(current_pos.x, current_pos.y + move_y))
                
                # Try each movement option
                moved = False
                for new_pos in movement_options:
                    if (self.game_map.is_valid_position(new_pos) and 
                        self.game_map.get_cell(new_pos) == CellType.WATER.value):
                        
                        # Check if this move would put enemy on same tile as ship
                        if new_pos.x == self.ship_position.x and new_pos.y == self.ship_position.y:
                            # Enemy is trying to move into ship's tile - trigger collision
                            entity_type_name = 'Enemy' if entity_type == CellType.ENEMY.value else 'Monster'
                            collision_msg = self.resolve_collision(current_pos, entity_type_name)
                            movements.append({
                                'entity_type': entity_type_name,
                                'from': (current_pos.x, current_pos.y),
                                'to': (new_pos.x, new_pos.y),
                                'collision': True,
                                'message': collision_msg,
                                'distance_to_ship': 0
                            })
                            moved = True
                            break
                        else:
                            # Normal movement - no collision
                            self.game_map.set_cell(current_pos, CellType.WATER.value)
                            self.game_map.set_cell(new_pos, entity_type)
                            
                            movements.append({
                                'entity_type': 'Enemy' if entity_type == CellType.ENEMY.value else 'Monster',
                                'from': (current_pos.x, current_pos.y),
                                'to': (new_pos.x, new_pos.y),
                                'distance_to_ship': max(abs(self.ship_position.x - new_pos.x), 
                                                      abs(self.ship_position.y - new_pos.y))
                            })
                            moved = True
                            break
                
                if not moved:
                    # Entity couldn't move (blocked by land or other entities)
                    movements.append({
                        'entity_type': 'Enemy' if entity_type == CellType.ENEMY.value else 'Monster',
                        'from': (current_pos.x, current_pos.y),
                        'to': (current_pos.x, current_pos.y),
                        'blocked': True,
                        'distance_to_ship': distance
                    })
        
        # After all enemy movements, check for any remaining position overlaps
        collision_check = self.check_and_handle_position_overlaps()
        if collision_check:
            print(f"🚨 POST-MOVEMENT COLLISION CHECK: {collision_check}")
        
        return movements
    
    def get_pursuing_entities(self) -> List[Dict]:
        """Get list of enemies and monsters that are actively pursuing (within 3 tiles of ship)"""
        pursuing_entities = []
        
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                cell = self.game_map.get_cell(Position(x, y))
                if cell in [CellType.ENEMY.value, CellType.MONSTER.value]:
                    # Calculate distance to ship
                    dx = self.ship_position.x - x
                    dy = self.ship_position.y - y
                    distance = max(abs(dx), abs(dy))  # Chebyshev distance
                    
                    # Entity is pursuing if within 3 tiles
                    if distance <= 3:
                        pursuing_entities.append({
                            'position': (x, y),
                            'type': cell,
                            'distance': distance
                        })
        
        return pursuing_entities
    
    def check_collision_with_ship(self, position: Position) -> bool:
        """Check if a given position would result in collision with the ship"""
        return (position.x == self.ship_position.x and 
                position.y == self.ship_position.y)
    
    def resolve_collision(self, collision_position: Position, entity_type: str) -> str:
        """Handle collision between ship and enemy/monster at given position"""
        old_lives = self.lives
        self.take_damage()
        damage_taken = old_lives - self.lives
        
        # Remove the enemy/monster from the map after collision
        self.game_map.set_cell(collision_position, CellType.WATER.value)
        
        collision_message = f"💥 COLLISION! {entity_type} at ({collision_position.x},{collision_position.y}) collided with ship! Lost {damage_taken} life."
        print(collision_message)
        return collision_message
    
    def check_and_handle_position_overlaps(self) -> str:
        """Check if any enemies/monsters occupy the same tile as the ship and handle collisions"""
        collision_messages = []
        
        # Check all positions on the map for enemies/monsters that overlap with ship position
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                pos = Position(x, y)
                cell_content = self.game_map.get_cell(pos)
                
                # If there's an enemy or monster at the ship's position, handle collision
                if (pos.x == self.ship_position.x and pos.y == self.ship_position.y and
                    cell_content in [CellType.ENEMY.value, CellType.MONSTER.value]):
                    
                    entity_type = "Enemy" if cell_content == CellType.ENEMY.value else "Monster"
                    collision_msg = self.resolve_collision(pos, entity_type)
                    collision_messages.append(collision_msg)
        
        return " | ".join(collision_messages) if collision_messages else ""

    def get_status(self) -> Dict:
        """Get current game status"""
        return {
            "ship_position": (self.ship_position.x, self.ship_position.y),
            "lives": self.lives,
            "treasures_collected": self.treasures_collected,
            "total_treasures": self.total_treasures,
            "cannonballs": self.cannonballs,
            "score": self.score,
            "enemies_defeated": self.enemies_defeated,
            "monsters_defeated": self.monsters_defeated,
            "turn_count": self.turn_count,
            "game_over": self.game_over,
            "victory": self.victory,
            "pursuing_entities": self.get_pursuing_entities()
        }
    
    def display_map(self, radius: int = 5):
        """Display the map around the ship"""
        print(f"\n{'='*50}")
        print(f"Turn {self.turn_count} | Lives: {self.lives} | Treasures: {self.treasures_collected}/{self.total_treasures}")
        print(f"Ship Position: ({self.ship_position.x}, {self.ship_position.y})")
        print(f"{'='*50}")
        
        # Display a section of the map around the ship
        start_x = max(0, self.ship_position.x - radius)
        end_x = min(self.game_map.width, self.ship_position.x + radius + 1)
        start_y = max(0, self.ship_position.y - radius)
        end_y = min(self.game_map.height, self.ship_position.y + radius + 1)
        
        for y in range(start_y, end_y):
            row = ""
            for x in range(start_x, end_x):
                if x == self.ship_position.x and y == self.ship_position.y:
                    row += "🚢 "
                else:
                    cell = self.game_map.grid[y][x]
                    if cell == 'W':
                        row += "🌊 "
                    elif cell == 'L':
                        row += "🌍 "
                    elif cell == 'T':
                        row += "💰 "
                    elif cell == 'E':
                        row += "⚔️ "
                    elif cell == 'M':
                        row += "👹 "
                    else:
                        row += f"{cell} "
            print(f"{y:2d}: {row}")
        
        # Print x-axis labels
        x_labels = "    "
        for x in range(start_x, end_x):
            x_labels += f"{x%10} "
        print(x_labels)
        print()

if __name__ == "__main__":
    # Quick test of the game state
    game = GameState()
    game.display_map()
    print(f"Game status: {game.get_status()}")
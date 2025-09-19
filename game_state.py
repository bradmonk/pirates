"""
Pirate Game - Core game logic and state management
"""
import csv
from typing import Tuple, List, Dict, Optional
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
    
    def move_ship(self, direction: Tuple[int, int]) -> bool:
        """Move the ship in the given direction (dx, dy)"""
        new_position = Position(
            self.ship_position.x + direction[0],
            self.ship_position.y + direction[1]
        )
        
        if not self.game_map.can_move_to(new_position):
            return False
        
        # Check what's at the new position
        cell_content = self.game_map.get_cell(new_position)
        
        # Handle different cell types
        if cell_content == CellType.TREASURE.value:
            self.collect_treasure(new_position)
        elif cell_content == CellType.ENEMY.value or cell_content == CellType.MONSTER.value:
            self.take_damage()
            # Remove the defeated enemy/monster
            self.game_map.set_cell(new_position, CellType.WATER.value)
        
        # Move the ship
        self.ship_position = new_position
        self.turn_count += 1
        
        # Check victory condition
        if self.treasures_collected >= self.total_treasures:
            self.victory = True
            self.game_over = True
        
        return True
    
    def collect_treasure(self, pos: Position):
        """Collect treasure at the given position"""
        self.treasures_collected += 1
        self.game_map.set_cell(pos, CellType.WATER.value)
        print(f"🏆 Treasure collected! Total: {self.treasures_collected}/{self.total_treasures}")
    
    def take_damage(self):
        """Ship takes damage from enemy or monster"""
        self.lives -= 1
        print(f"💥 Ship damaged! Lives remaining: {self.lives}")
        if self.lives <= 0:
            self.game_over = True
            print("💀 Game Over - Ship destroyed!")
    
    def fire_cannon(self, target_pos: Position) -> bool:
        """Fire cannon at target position"""
        # Check if target is within range (adjacent cells)
        distance = abs(target_pos.x - self.ship_position.x) + abs(target_pos.y - self.ship_position.y)
        if distance > 1:
            print("🎯 Target too far - cannons have range of 1 tile")
            return False
        
        cell_content = self.game_map.get_cell(target_pos)
        if cell_content in [CellType.ENEMY.value, CellType.MONSTER.value]:
            self.game_map.set_cell(target_pos, CellType.WATER.value)
            print(f"💥 {cell_content} destroyed at {target_pos.x}, {target_pos.y}!")
            return True
        else:
            print("🎯 No target at that position")
            return False
    
    def get_status(self) -> Dict:
        """Get current game status"""
        return {
            "ship_position": (self.ship_position.x, self.ship_position.y),
            "lives": self.lives,
            "treasures_collected": self.treasures_collected,
            "total_treasures": self.total_treasures,
            "turn_count": self.turn_count,
            "game_over": self.game_over,
            "victory": self.victory
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
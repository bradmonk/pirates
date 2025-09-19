# Pirate Game - Complete Game Rules & Mechanics

## Game Overview
A turn-based strategy game where AI agents control a pirate ship navigating a dangerous ocean to collect treasures while avoiding or destroying enemies and monsters.

## Map & World

### Cell Types
- **Water (W)**: Safe to navigate
- **Land (L)**: Impassable terrain 
- **Treasure (T)**: Collectible items that provide resources and points
- **Enemy (E)**: Hostile ships that deal damage on contact
- **Monster (M)**: More dangerous creatures that deal damage on contact
- **Ship (O)**: Player's starting position (replaced with water after initialization)

### Map Size
- Standard 30x30 grid loaded from `map.csv`
- Coordinates use (x, y) system with (0,0) at top-left

## Ship Mechanics

### Starting Resources
- **Lives**: 3 (game over when reduced to 0)
- **Cannonballs**: 25 (ammunition for combat)
- **Score**: 0 (tracks performance)

### Movement System
- **Range**: Up to 3 tiles per turn in any combination of directions
- **Pathfinding**: Simple system - moves horizontally first, then vertically
- **Restrictions**: Cannot move through land or off the map edges
- **Encounters**: Automatic interactions when moving into occupied cells

## Combat System

### Cannon Mechanics
- **Range**: 5 tiles maximum (Manhattan distance)
- **Ammunition**: Consumes 1 cannonball per shot
- **Probabilistic Hit System**: Distance-based accuracy
  - 1 tile: 95% hit chance
  - 2 tiles: 90% hit chance  
  - 3 tiles: 75% hit chance
  - 4 tiles: 50% hit chance
  - 5 tiles: 25% hit chance
- **Targets**: Only enemies and monsters can be destroyed
- **Misses**: Still consume cannonballs

### Combat Encounters
- **Contact Damage**: Ship loses 1 life when moving into enemy/monster cells
- **Entity Removal**: Enemies and monsters are destroyed after dealing damage
- **No Retaliation**: Entities don't attack from a distance

## Scoring System

### Point Values
- **Treasure Collection**: +10 points each
- **Enemy Destruction**: +10 points each
- **Monster Destruction**: +50 points each

### Victory Conditions
- **Primary Goal**: Collect all treasures on the map
- **Bonus**: Maximize score by destroying enemies and monsters
- **Failure**: Lose all 3 lives

## Resource Management

### Cannonball Economy
- **Starting Amount**: 25 cannonballs
- **Treasure Reward**: +2 cannonballs per treasure collected
- **Consumption**: 1 cannonball per cannon shot (hit or miss)
- **Strategy**: Balance treasure collection with combat engagement

### Life System
- **Starting Lives**: 3
- **Damage Sources**: Contact with enemies or monsters
- **No Healing**: Lives cannot be restored during gameplay

## Enemy AI Behavior

### Movement Rules
- **Activation Range**: Enemies and monsters move only when within 3 tiles of the ship
- **Movement Speed**: 1 tile per turn
- **Pathfinding Priority**:
  1. Diagonal movement toward ship (most efficient)
  2. Horizontal movement toward ship
  3. Vertical movement toward ship
- **Obstacles**: Cannot move through land or occupied cells
- **Stuck Behavior**: Remain stationary if all paths blocked

### AI Strategy
- **Pursuit**: Actively chase the player's ship
- **Predictable**: Always move toward ship using shortest path
- **Non-Coordinated**: Each entity moves independently

## Turn Structure

### Phase Order
1. **AI Crew Deliberation**: Three AI agents (Navigator, Cannoneer, Captain) analyze situation and make decisions
2. **Player Actions**: Ship movement, treasure collection, combat encounters processed
3. **Enemy Movement**: All enemies and monsters within range move toward ship
4. **Status Update**: Map display and statistics updated
5. **Victory Check**: Game ends if all treasures collected or ship destroyed

### AI Agents
- **Navigator**: Analyzes surroundings, identifies threats and treasures
- **Cannoneer**: Evaluates combat opportunities and cannon effectiveness  
- **Captain**: Makes final movement decisions based on crew recommendations

## Advanced Mechanics

### Multi-Tile Movement
- Ship can move up to 3 tiles in a single turn
- Path must be clear of obstacles
- All encounters along the path are triggered
- Strategic positioning for optimal treasure collection and combat angles

### Probabilistic Combat
- Distance affects hit probability significantly
- Risk/reward balance between close-range accuracy and safety
- Resource management critical for extended gameplay

### Dynamic Enemy Positioning
- Enemies actively pursue the player
- Creates evolving tactical situations
- Forces strategic decision-making about engagement vs. evasion

## Game End Conditions

### Victory
- Collect all treasures on the map
- Ship survives the journey
- Score based on treasures collected and enemies defeated

### Defeat  
- Ship loses all 3 lives through enemy encounters
- Game ends immediately upon death

### Turn Limit
- Maximum 50 turns to prevent infinite gameplay
- Encourages efficient exploration and resource management

## Strategic Considerations

### Resource Optimization
- Balance cannonball usage with treasure collection rewards
- Prioritize high-value targets (monsters worth 50 vs enemies worth 10)
- Plan routes to maximize treasure collection while minimizing enemy encounters

### Risk Management  
- Evaluate when to engage enemies vs. avoid them
- Consider enemy movement patterns when planning ship routes
- Use terrain features to limit enemy approach angles

### Endgame Planning
- Ensure sufficient resources for final treasure collection phases
- Account for increasing enemy density as treasures are collected
- Maintain escape routes for emergency situations

---

*This game combines strategic planning, resource management, and tactical combat in a dynamic environment where both player actions and enemy AI create an evolving challenge.*
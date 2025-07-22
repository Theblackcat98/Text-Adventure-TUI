# Developer Guide - Text Adventure TUI

This guide covers the technical aspects of developing and extending the Text Adventure TUI engine.

## Architecture Overview

The Text Adventure TUI engine follows a modular, event-driven architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Game Engine   │    │  Event Manager  │    │  Story Manager  │
│   (game.py)     │◄──►│(event_manager.py)│    │(story_manager.py)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Game State Mgr  │    │   YAML Loader   │    │ Data Structures │
│(game_state_...py)│    │(yaml_loader.py) │    │(data_structures.py)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Game Engine (`game.py`)
The main game loop that orchestrates all other components:
- Handles player input and choice presentation
- Manages LLM integration for dynamic storytelling
- Coordinates event triggering and state updates
- Manages save/load functionality

### 2. Event Manager (`event_manager.py`)
Handles the event-driven gameplay mechanics:
- Evaluates trigger conditions
- Executes event actions
- Manages event state (once-only events, etc.)
- Provides narrative injection and modification

### 3. Story Manager (`story_manager.py`)
Manages story discovery, validation, and creation:
- Discovers available stories automatically
- Validates story structure and content
- Creates story templates
- Provides story metadata

### 4. Game State Manager (`game_state_manager.py`)
Manages the current game state:
- Player statistics and inventory
- Game flags and location tracking
- Turn counting and progression
- State persistence for save/load

### 5. YAML Loader (`yaml_loader.py`)
Handles loading and parsing of story files:
- Loads story arc definitions
- Parses event configurations
- Creates data structure objects
- Supports backward compatibility

### 6. Data Structures (`data_structures.py`)
Defines the core data models:
- `Story`: Complete story definition
- `Event`: Individual event configuration
- `Player`: Player state and attributes
- `GameState`: Current game session state

## Event System Deep Dive

### Event Structure
```yaml
- id: unique_event_id
  name: "Human Readable Name"
  options:
    once: true  # Optional: event only triggers once
    priority: 1 # Optional: execution priority
  trigger:
    mode: AND   # AND, OR, or MANUAL
    conditions:
      - type: condition_type
        value: condition_value
        # Additional condition parameters
  actions:
    - type: action_type
      value: action_value
      # Additional action parameters
```

### Trigger Types

#### Location-Based
- `location`: Player is in specific location
- `turn_count_in_location`: Time spent in current location
- `turn_count_global`: Total game turns

#### State-Based
- `flag_set`/`flag_not_set`: Check game flags
- `inventory_has`/`inventory_not_has`: Check inventory
- `stat_check`: Check player statistics
- `game_start`: Game initialization trigger

#### Input-Based
- `player_action_keyword`: Match keywords in input
- `player_intent`: Match classified intent
- `player_action`: Exact action match

### Action Types

#### State Modification
- `set_flag`/`clear_flag`: Manage game flags
- `add_item`/`remove_item`: Inventory management
- `change_location`: Move player
- `update_stat`: Modify player statistics

#### Narrative Control
- `override_narrative`: Replace story text completely
- `inject_narrative`: Add text before/after main narrative
- `modify_prompt`: Influence LLM generation

#### Player Interaction
- `add_choice`: Add single player option
- `present_choices`: Add multiple player options
- `end_game`: End story with success/failure

## Story Creation Workflow

### 1. Planning Phase
- Define story concept and theme
- Outline major story beats and choices
- Identify key locations and characters
- Plan progression mechanics

### 2. Structure Design
- Create story arc with metadata
- Design event flow and dependencies
- Plan flag usage and state management
- Define player progression

### 3. Implementation
```bash
# Create story template
python story_tool.py create my_story "My Amazing Story" --author "Your Name"

# Edit generated files
# - story_arc.yaml: Story metadata and structure
# - story_events.yaml: Interactive events
# - intro.txt: Opening narrative

# Validate story
python story_tool.py validate my_story
```

### 4. Testing and Refinement
- Test all story paths
- Validate event triggers
- Check narrative flow
- Refine based on feedback

## Step-by-Step Story Creation Tutorial

Let's create a simple story called "The Mysterious Key" from scratch:

### Step 1: Create the Story Template

```bash
python story_tool.py create mysterious_key "The Mysterious Key" --author "Your Name"
```

This creates three files:
- `mysterious_key_story_arc.yaml` - Story metadata
- `mysterious_key_story_events.yaml` - Interactive events
- `mysterious_key_intro.txt` - Opening narrative

### Step 2: Edit the Story Arc

Edit `mysterious_key_story_arc.yaml`:

```yaml
title: "The Mysterious Key"
starting_location: "old_attic"
initial_story_part: "mysterious_key_intro.txt"
total_turns_estimate: 10

initial_inventory: []
initial_player_stats:
  health: 100
  curiosity: 50

description: |
  You've inherited your grandmother's house and discovered a mysterious key
  in the attic. What secrets does it unlock?

checkpoints:
  - turn: 8
    prompt_injection: "Time is running short. You feel compelled to solve this mystery."

tags: ["mystery", "family", "short"]
difficulty: "beginner"
content_warnings: []
author: "Your Name"
version: "1.0"
```

### Step 3: Create the Opening Narrative

Edit `mysterious_key_intro.txt`:

```
The dusty attic creaks under your footsteps as you explore your late grandmother's house. 
Sunlight filters through a small window, illuminating floating dust motes and forgotten 
treasures. In an old wooden chest, your fingers close around something cold and metallic - 
an ornate brass key with strange symbols etched into its surface.

What door could this mysterious key possibly open?
```

### Step 4: Design Interactive Events

Edit `mysterious_key_story_events.yaml`:

```yaml
# Story initialization
- id: story_start
  name: "Discovery in the Attic"
  trigger:
    mode: MANUAL
    conditions:
      - type: game_start
  actions:
    - type: set_flag
      value: "has_mysterious_key"
    - type: add_item
      value: "brass_key"
    - type: change_location
      value: "old_attic"

# First investigation
- id: examine_key
  name: "Examining the Key"
  options:
    once: true
  trigger:
    mode: AND
    conditions:
      - type: player_action_keyword
        keywords: ["examine key", "look at key", "inspect key"]
      - type: inventory_has
        value: "brass_key"
  actions:
    - type: set_flag
      value: "knows_key_symbols"
    - type: override_narrative
      text: |
        The brass key is heavier than it looks. Strange symbols are etched along its length - 
        they look like they might be some kind of family crest. You remember seeing similar 
        symbols somewhere else in the house...

# Finding the locked door
- id: find_locked_door
  name: "The Hidden Door"
  options:
    once: true
  trigger:
    mode: AND
    conditions:
      - type: player_action_keyword
        keywords: ["go downstairs", "leave attic", "explore house"]
      - type: flag_set
        value: "knows_key_symbols"
  actions:
    - type: change_location
      value: "basement"
    - type: override_narrative
      text: |
        As you explore the house, you notice a small door hidden behind a bookshelf 
        in the basement. The same symbols from the key are carved into the door frame!

# Using the key
- id: unlock_door
  name: "Unlocking the Mystery"
  trigger:
    mode: AND
    conditions:
      - type: player_action_keyword
        keywords: ["use key", "unlock door", "open door"]
      - type: location
        value: "basement"
      - type: inventory_has
        value: "brass_key"
  actions:
    - type: end_game
      success: true
      message: |
        The key turns smoothly in the lock. Behind the door, you discover your 
        grandmother's secret study, filled with journals documenting your family's 
        fascinating history. You've uncovered a treasure more valuable than gold - 
        the story of your heritage.
```

### Step 5: Validate and Test

```bash
# Validate the story structure
python story_tool.py validate mysterious_key

# Test the story in the game
python -m text_adventure_tui_lib.game
# Select "The Mysterious Key" from the menu
```

### Step 6: Iterate and Improve

Based on testing:
- Add more interactive elements
- Create branching paths
- Add inventory puzzles
- Enhance narrative descriptions
- Test edge cases

This tutorial demonstrates the complete process from concept to playable story!

## Advanced Event Patterns

### Progressive Revelation
```yaml
- id: reveal_clue_1
  trigger:
    conditions:
      - type: location
        value: "library"
      - type: flag_not_set
        value: "clue_1_found"
  actions:
    - type: set_flag
      value: "clue_1_found"
    - type: inject_narrative
      text: "You notice something glinting behind the books..."

- id: reveal_clue_2
  trigger:
    conditions:
      - type: flag_set
        value: "clue_1_found"
      - type: player_action_keyword
        keywords: ["examine", "look behind"]
  actions:
    - type: set_flag
      value: "clue_2_found"
    - type: override_narrative
      text: "Behind the books, you find an ancient key!"
```

### Conditional Choices
```yaml
- id: locked_door_encounter
  trigger:
    conditions:
      - type: location
        value: "mysterious_door"
  actions:
    - type: present_choices
      choices:
        - label: "Use the ancient key"
          action: "unlock_door"
          condition:
            type: inventory_has
            value: "ancient_key"
        - label: "Try to pick the lock"
          action: "pick_lock"
        - label: "Look for another way"
          action: "find_alternative"
```

### Time-Based Events
```yaml
- id: time_pressure
  trigger:
    conditions:
      - type: turn_count_global
        operator: ">="
        value: 15
  actions:
    - type: inject_narrative
      text: "Time is running out! You feel the urgency mounting."
      position: "pre"
    - type: modify_prompt
      instruction: "The player is under time pressure. Emphasize urgency."
```

## LLM Integration

### Prompt Engineering
The engine uses several techniques to guide LLM generation:

1. **Context Building**: Current game state, location, and history
2. **Instruction Injection**: Event-driven prompt modifications
3. **Choice Generation**: Structured choice presentation
4. **Narrative Consistency**: Maintaining story coherence

### Customizing LLM Behavior
```python
# In event actions
- type: modify_prompt
  instruction: "The atmosphere should be tense and foreboding."

# Multiple instructions can be combined
- type: modify_prompt
  instruction: "Present exactly 3 choices to the player."
```

## Testing and Debugging

### Running Tests

The project includes comprehensive tests to ensure the game engine works correctly:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python tests/test_game_engine.py

# Run tests with coverage
python -m pytest tests/ --cov=text_adventure_tui_lib --cov-report=html
```

### Test Structure

The test suite includes:
- **test_game_basics.py** - Basic functionality tests
- **test_game_engine.py** - Core engine component tests
- **test_new_engine.py** - Advanced engine feature tests

### Adding New Tests

When adding new features, create corresponding tests:

```python
# Example test structure
import pytest
from text_adventure_tui_lib.your_module import YourClass

def test_your_feature():
    # Arrange
    instance = YourClass()
    
    # Act
    result = instance.your_method()
    
    # Assert
    assert result == expected_value
```

### Debug Mode
Enable debug mode to see:
- Event trigger evaluations
- Game state changes
- LLM prompt construction
- Flag and inventory updates

### Validation Tools
```bash
# Validate specific story
python story_tool.py validate my_story

# Validate all stories
python story_tool.py validate

# Get detailed story information
python story_tool.py info my_story
```

### Testing Stories

When creating new stories, test them thoroughly:

```bash
# 1. Validate story structure
python story_tool.py validate your_story

# 2. Test in debug mode
python -m text_adventure_tui_lib.game
# Select your story and enable debug mode

# 3. Test all story paths
# Play through different choices to ensure all events trigger correctly

# 4. Verify save/load functionality
# Use /save and /load commands during gameplay
```

### Common Issues

#### Events Not Triggering
1. Check trigger conditions carefully
2. Verify flag names and values
3. Ensure location names match exactly
4. Test with debug mode enabled

#### Narrative Flow Problems
1. Use `inject_narrative` for additions
2. Use `override_narrative` for replacements
3. Consider narrative position (pre/post)
4. Test with different player choices

#### State Management Issues
1. Verify flag setting/clearing logic
2. Check inventory item names
3. Ensure stat updates are correct
4. Test save/load functionality

## Performance Considerations

### Event Optimization
- Use specific trigger conditions to avoid unnecessary evaluations
- Implement `once: true` for one-time events
- Consider event priority for execution order

### Memory Management
- Large stories may require memory optimization
- Consider lazy loading for complex narratives
- Monitor save file sizes

## Extension Points

### Adding New Trigger Types
1. Add condition evaluation in `EventManager._evaluate_trigger()`
2. Update documentation and examples
3. Add validation in `StoryManager`

### Adding New Action Types
1. Add action handling in `EventManager._perform_actions()`
2. Update return value structure if needed
3. Add validation and documentation

### Custom Game Mechanics
1. Extend `GameState` for new state types
2. Add corresponding manager methods
3. Update save/load serialization

## Best Practices

### Story Design
- Start with simple, linear stories
- Gradually add complexity and branching
- Test frequently during development
- Use meaningful flag and location names

### Event Design
- Keep events focused on single purposes
- Use descriptive event names and IDs
- Document complex trigger logic
- Test edge cases thoroughly

### Code Organization
- Follow existing naming conventions
- Add type hints for new functions
- Include docstrings for public methods
- Write tests for new functionality

## Contributing

### Development Setup
1. Fork the repository
2. Create a virtual environment
3. Install development dependencies
4. Run existing tests
5. Make your changes
6. Add tests for new features
7. Update documentation
8. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints consistently
- Write clear, descriptive variable names
- Add comments for complex logic

### Testing
- Test new features thoroughly
- Include edge case testing
- Validate with multiple stories
- Check backward compatibility

This guide should help you understand and extend the Text Adventure TUI engine effectively. For specific questions or issues, please refer to the main README or open an issue on the project repository.

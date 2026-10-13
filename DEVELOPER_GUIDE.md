# Developer Guide - Text Adventure TUI

This guide covers the technical aspects of developing and extending the Text Adventure TUI engine.

## Architecture Overview

The Text Adventure TUI engine is a **hybrid LLM + YAML design**:

*   **The LLM (Ollama) generates the story** — scene summaries, the choices offered each turn,
    intent classification, and narration of action outcomes.
*   **YAML manages all state** — every flag, inventory item, stat, location, and turn counter is
    defined and mutated through YAML-driven events. The LLM never changes game state directly.

The YAML layer is the source of truth; the LLM is a rendering/authoring layer. See
[docs/architecture.md](docs/architecture.md) for the flow overview and
[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) for the line-level deep dive.

The engine follows a modular, event-driven architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Game Engine   │    │  Event Manager  │    │  Story Manager  │
│   (game.py)     │◄──►│(event_manager.py)│    │(story_manager.py)│
│  hosts the      │    │  interprets all │    │                 │
│  Ollama LLM     │    │  YAML event     │    │                 │
│  (story only)   │    │  triggers and   │    │                 │
│                 │    │  actions        │    │                 │
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
The main game loop (module: `text_adventure_tui_lib/game.py`) that orchestrates all other components:
- Handles player input and choice presentation
- Manages LLM integration for dynamic storytelling (three call sites: scene+choices JSON, intent classification, action continuation)
- Coordinates event triggering and state updates
- Manages save/resume functionality

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
    once: true  # Optional: event only triggers once per playthrough
    once_per_location: true  # Optional: re-arms when the player travels
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
- `inventory_count`: How many items the player carries (`==`, `>=`, `<=`, `>`, `<`)
- `stat_check`: Check player statistics
- `game_start`: Game initialization trigger

#### Input-Based
- `player_action_keyword`: Match keywords in input (substring by default; `match: word` for whole-word)
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

# Edit generated files:
# - <my_story>_story_arc.yaml: Story metadata and initial state
# - <my_story>_story_events.yaml: Interactive events
# - <my_story>_intro.txt: Opening narrative

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

The LLM is a pure authoring/rendering layer: it produces prose and choices, while YAML events
decide what those words mean. There are three call sites, all in `game.py`:

1.  **`get_llm_options(narrative, game_state_manager)`** — each turn, sends the current narrative
    plus live state (location, health, inventory) and requires a JSON reply
    (`{"narrative_summary": ..., "choices": [...]}`, exactly 4 choices). On any error (bad JSON,
    wrong choice count, Ollama down) it falls back to the current narrative and
    `["Look around.", "Check inventory.", "Wait.", "Leave."]`.
2.  **`get_player_intent(player_choice, game_state_manager)`** — classifies the chosen action into
    a snake_case keyword (e.g. `search_desk`, `read_journal`) at low temperature. This is what
    `player_intent` event triggers match against. Errors return `"unknown_intent"`.
3.  **`get_llm_story_continuation(narrative, player_choice, instructions)`** — narrates the
    outcome of the chosen action. Only called when no event produced an `override_narrative`
    that turn; on error it returns `"The path forward is hazy..."`.

### Configuration

`OLLAMA_HOST` (default `http://localhost:11434`) and `OLLAMA_MODEL` (default `phi4:latest`)
are read from the environment at import time (`game.py:36-37`), so they must be set before
launch.

### Prompt Engineering

The engine uses several techniques to guide LLM generation:

1.  **Context Building**: current game state, location, and history are injected into the prompt
2.  **Instruction Injection**: event-driven prompt modifications (`modify_prompt` actions and
    checkpoint `prompt_injection`), collected per turn and appended to the continuation prompt
3.  **Choice Generation**: structured JSON choice presentation
4.  **Narrative Consistency**: key story beats can bypass the LLM entirely via
    `override_narrative`, guaranteeing authored text is shown verbatim

### Customizing LLM Behavior
```python
# In event actions (story or general events YAML)
- type: modify_prompt
  instruction: "The atmosphere should be tense and foreboding."

# Multiple instructions can be combined
- type: modify_prompt
  instruction: "Present exactly 3 choices to the player."
```

```python
# In the story arc checkpoints (fires when turn_count matches)
checkpoints:
  - turn: 10
    prompt_injection: "Security is tightening. You need to move quickly now."
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
python -m pytest tests/test_game_engine.py

# Run directly with pytest
pytest tests/test_game_engine.py

# Run tests with coverage
python -m pytest tests/ --cov=text_adventure_tui_lib --cov-report=html
```

### Test Structure

The test suite includes:
- **test_game_basics.py** - Basic functionality tests
- **test_game_engine.py** - Core engine component tests
- **test_new_engine.py** - Advanced engine feature tests
- **test_yaml_state_logic.py** - Every condition type, action type, `once`/`MANUAL`/force semantics, ordering quirks, and scripted playthroughs of the shipped stories — no LLM required
- **test_yaml_exhaustive_playthrough.py** - Exhaustive BFS exploration of the reachable state space of both shipped stories (every corpus action from every reachable state), reachability/dead-event coverage, keyword-granularity firing tests, save/resume edge cases, and checkpoint logic

### Testing Without an LLM

The engine's test harness (`tests/yaml_sim.py`) drives the real `EventManager`/`GameStateManager` exactly as `game.py` does, minus the LLM calls. This works because the LLM only ever produces prose and choice labels — it never mutates state. Simulated turns supply action text directly, and state coverage is explored breadth-first with deduplication. No Ollama instance or network access is needed for any test.

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

# 4. Verify save/resume functionality
# Use /save during gameplay, then resume from the main menu's "Resume Game" option
# (saves live in ~/.text_adventure_tui_saves/)
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

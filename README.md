# Text Adventure TUI

A terminal-based text adventure game engine powered by LLM (Large Language Model) integration. Create immersive, dynamic stories with event-driven gameplay and natural language interaction.

## Features

- **LLM-Powered Storytelling**: Dynamic narrative generation using Ollama
- **Event-Driven System**: Complex story branching and state management
- **Rich Terminal UI**: Beautiful text formatting with Rich library
- **Save/Load System**: Persistent game state
- **Modular Story Structure**: Easy story creation and modification
- **Natural Language Input**: Players interact using natural language
- **Story Discovery**: Automatic detection and validation of stories
- **Multiple Story Support**: Play different adventures with unique mechanics
- **Comprehensive Event System**: Full range of triggers and actions

## Installation

1. **Install Ollama**: Follow instructions at [ollama.ai](https://ollama.ai)
2. **Pull a model**: `ollama pull llama3.1:8b` (or your preferred model)
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Run the game**: `python -m text_adventure_tui_lib.game`

## Story Structure

Stories are defined using YAML files with the following structure:

### Story Arc File (`story_name_story_arc.yaml`)
```yaml
title: "Your Story Title"
starting_location: "initial_location"
initial_story_part: "intro.txt"
total_turns_estimate: 20
initial_inventory: ["item1", "item2"]
initial_player_stats:
  health: 100
  mana: 50
description: "Story description"
checkpoints:
  - turn: 15
    prompt_injection: "Time is running short..."
  - turn: 25
    force_end_game: true
    flag_messages:
      - flag: "success"
        message_if_set: "Victory!"
        message_if_not_set: "Defeat..."
tags: ["adventure", "mystery"]
difficulty: "medium"
content_warnings: ["mild violence"]
author: "Your Name"
version: "1.0"
```

### Events File (`story_name_story_events.yaml`)
Events define the interactive elements of your story:

```yaml
- id: event_id
  name: "Event Name"
  options:
    once: true  # Optional: event triggers only once
  trigger:
    mode: AND  # AND, OR, or MANUAL
    conditions:
      - type: location
        value: "specific_location"
      - type: flag_set
        value: "flag_name"
  actions:
    - type: set_flag
      value: "new_flag"
    - type: override_narrative
      text: "Custom narrative text"
    - type: present_choices
      choices:
        - label: "Option 1"
          action: "choice_action_1"
        - label: "Option 2"
          action: "choice_action_2"
```

## Event System

### Trigger Types
- `location`: Player is in a specific location
- `flag_set`/`flag_not_set`: Check game flags
- `player_action_keyword`: Match keywords in player input
- `player_intent`: Match player's intended action
- `player_action`: Exact action match
- `inventory_has`/`inventory_not_has`: Check inventory
- `turn_count_in_location`: Time spent in location
- `turn_count_global`: Total game turns
- `stat_check`: Check player statistics
- `game_start`: Game initialization

### Action Types
- `set_flag`/`clear_flag`: Manage game flags
- `add_item`/`remove_item`: Inventory management
- `change_location`: Move player
- `update_stat`: Modify player statistics
- `override_narrative`: Replace story text
- `inject_narrative`: Add text before/after
- `modify_prompt`: Influence LLM generation
- `add_choice`: Add single player option
- `present_choices`: Add multiple player options
- `end_game`: End the story with success/failure

### Operators for Numeric Conditions
- `==`: Equal to
- `>=`: Greater than or equal to
- `<=`: Less than or equal to
- `>`: Greater than
- `<`: Less than

## Configuration

Edit `text_adventure_tui_lib/game.py` to configure:
- Ollama host and model
- Debug settings
- UI themes

## Creating New Stories

### Method 1: Using Story Manager (Recommended)
```python
from text_adventure_tui_lib.story_manager import StoryManager
from pathlib import Path

stories_path = Path("text_adventure_tui_lib/story_parts")
events_path = Path("text_adventure_tui_lib/events")
manager = StoryManager(stories_path, events_path)

# Create a new story template
manager.create_story_template("my_story", "My Amazing Adventure", "Your Name")

# Validate an existing story
result = manager.validate_story("my_story")
if not result.is_valid:
    print("Errors:", result.errors)
```

### Method 2: Manual Creation
1. Create a story arc file: `story_name_story_arc.yaml`
2. Create an events file: `story_name_story_events.yaml`
3. Create an intro text file: `story_name_intro.txt`
4. Place files in appropriate directories
5. The story will automatically appear in the main menu

## Example Stories

### Whispers of the Salted Crypt
A mystery adventure about finding a missing mentor. Features:
- Investigation mechanics
- Location-based puzzles
- Multiple story paths
- Rescue mission narrative

### The Clockwork Heist
A stealth-based heist in a mechanical museum. Features:
- Stealth mechanics
- Multiple approach strategies
- Inventory-based puzzles
- Risk/reward choices

## Development

### Project Structure
```
text_adventure_tui_lib/
├── game.py              # Main game engine
├── event_manager.py     # Event system
├── yaml_loader.py       # Story loading
├── data_structures.py   # Game data models
├── game_state_manager.py # State management
├── story_manager.py     # Story discovery and validation
├── story_parts/         # Story files
│   ├── *_story_arc.yaml
│   └── *.txt
└── events/              # Event files
    ├── general_events.yaml
    └── *_story_events.yaml
```

### Story Validation
The story manager includes comprehensive validation:
- Required field checking
- File existence verification
- YAML syntax validation
- Event structure validation
- Cross-reference checking

### Adding Features
1. Extend data structures in `data_structures.py`
2. Add new action types in `event_manager.py`
3. Update trigger conditions as needed
4. Add validation rules in `story_manager.py`
5. Test with existing stories

### General Events
The `general_events.yaml` file contains reusable events:
- Health warnings
- Location descriptions
- Help system
- Debug information
- Time-based events

## Game Commands

### In-Game Commands
- `/save`: Save current game state
- `/debug`: Show debug information
- `/quit`: Exit the game
- `/force_event <event_id>`: Trigger specific event (debug)

### Natural Language
Players can interact naturally:
- "look around"
- "take the key"
- "go north"
- "examine the door"
- "use the lockpicks on the chest"

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Validate stories using the story manager
5. Update documentation
6. Submit a pull request

## Troubleshooting

### Common Issues
1. **Ollama not responding**: Check if Ollama is running and accessible
2. **Story not appearing**: Verify story arc file exists and is valid
3. **Events not triggering**: Check trigger conditions and flags
4. **Save/load errors**: Ensure save directory permissions

### Debug Mode
Enable debug mode in the main menu to see:
- Game state information
- Event trigger details
- Flag and inventory status
- Turn counters

## License

MIT License - see LICENSE file for details.
## Build, Lint, and Test

- **Install dependencies**: `pip install -r requirements-dev.txt`
- **Lint**: `flake8 .`
- **Test**: `pytest`
- **Run a single test file**: `pytest tests/test_new_engine.py`
- **Build**: `python -m build`

## Code Style

- **Formatting**: Use Black for code formatting (max line length 88).
- **Imports**: Use `isort` to sort imports.
- **Types**: Use type hints for all function signatures.
- **Naming**: Use `snake_case` for variables and functions, `PascalCase` for classes.
- **Error Handling**: Use try/except blocks for error handling.
- **Docstrings**: Use Google-style docstrings.

## Game Engine Architecture

The engine is a **hybrid LLM + YAML design**: the LLM (Ollama) generates the story (scene
summaries, choices, intent classification, action outcomes), while YAML drives **all game
state** (flags, inventory, stats, locations, turn counters, branching). The LLM never mutates
state directly; events are the only mechanism that changes it.

The engine is event-driven and location-based. The core components are:

- **`game.py`**: The main game loop (menu, turn loop, all LLM calls, save/resume). Driven by the `current_location` value, turn counters, and the event system.
- **`event_manager.py`**: The YAML interpreter. Evaluates trigger conditions against `GameState` and the player's action/intent, then executes event actions.
- **`yaml_loader.py`**: Loads a story arc file, then merges `events/general_events.yaml` + `events/<story>_story_events.yaml` (in that order) into a flat event list, and builds the initial `Player` from the arc's `initial_*` fields.
- **`data_structures.py`**: Defines the core data structures for the game, including `GameState`, `Player`, `Story`, and `Event`.
- **`game_state_manager.py`**: Manages the game state, including player stats, inventory, flags, and location. It is the **only** writer of mutable state.

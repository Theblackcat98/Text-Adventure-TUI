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

The game engine is event-driven and location-based. The core components are:

- **`game.py`**: The main game loop, which is driven by the `current_location` flag and the event system.
- **`event_manager.py`**: Manages game events, including loading event definitions from YAML files, checking trigger conditions, and executing event actions.
- **`yaml_loader.py`**: Loads all YAML files in a story's directory into a single, flat list of events.
- **`data_structures.py`**: Defines the core data structures for the game, including `GameState`, `Player`, `Story`, and `Event`.
- **`game_state_manager.py`**: Manages the game state, including player stats, inventory, flags, and location.

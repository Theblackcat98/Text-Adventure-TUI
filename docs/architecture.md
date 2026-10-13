# Architecture Overview

The Terminal Text Adventure is a **hybrid engine**:

- **LLM (Ollama) generates the story** — scene summaries, choices, and action outcomes.
- **YAML manages all game state** — branching, puzzles, inventory, flags, locations, and pacing.

The YAML layer is the source of truth for what has happened and what is possible; the LLM
only ever produces prose and choices. It can never change game state directly.

> For the exhaustive deep dive (line-level call traces, load order, known quirks, and
> verified reachability analysis), see [`docs/architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md).

## Core Components

1.  **Game Engine (`text_adventure_tui_lib/game.py`)**:
    *   The single entry point: main menu, turn loop, all LLM calls, slash commands, save writing.
    *   **Responsibilities**:
        *   Initializing the Ollama client and the Rich console/theme.
        *   Loading a story via `yaml_loader.load_story_and_player()`.
        *   Running the per-turn loop: LLM scene description → choice presentation → event evaluation → LLM continuation.
        *   Handling player input (numbered choices and `/commands`).
        *   Save/resume, story checkpoints, and game-end handling.

2.  **LLM Integration (Ollama)**:
    *   Three LLM call sites per turn, all via the `ollama` Python client:
        *   **Scene + choices** (`get_llm_options`): returns a JSON object with `narrative_summary` and up to 4 `choices`. Falls back to a generic list (`Look around.`, `Check inventory.`, `Wait.`, `Leave.`) if the call or parsing fails.
        *   **Intent classification** (`get_player_intent`): classifies the chosen action into a keyword (e.g. `search_desk`) used by `player_intent` event triggers.
        *   **Story continuation** (`get_llm_story_continuation`): narrates the outcome of the chosen action.
    *   **Connection**: `http://localhost:11434` by default; override with the `OLLAMA_HOST` environment variable.
    *   **Model**: `phi4:latest` by default; override with the `OLLAMA_MODEL` environment variable.
    *   Both variables are read at import time (`game.py:36-37`), so they must be set before launching the game.

3.  **Event System (`text_adventure_tui_lib/event_manager.py`)** — the YAML interpreter:
    *   Each turn, every event's `trigger` is evaluated against the current `GameState` (location, flags, inventory, stats, turn counters) plus the player's action/intent.
    *   Conditions combine with `mode: AND`, `OR` (or `MANUAL`, never auto-fired).
    *   Executing actions mutates state (flags, inventory, stats, location) and produces narrative effects (`override_narrative`, `inject_narrative`, `modify_prompt`, `add_choice`, `end_game`).
    *   `options.once: true` events fire at most once per playthrough; the fired set is the only save-relevant event state (`get_state()`/`load_state()`).

4.  **Game State (`text_adventure_tui_lib/data_structures.py` + `game_state_manager.py`)**:
    *   `GameState` holds the mutable runtime state: `flags`, `turn_count`, `current_location`, `turns_in_location`, plus references to the `Story` and `Player`.
    *   `Player` holds `stats` and `inventory`.
    *   `GameStateManager` is the **only** writer of this state. YAML actions name an action (`set_flag`, `add_item`, `change_location`, ...) and the manager executes exactly one mutation — YAML authors can shape state but never touch objects directly.

5.  **Story Content (YAML + text)**:
    *   `story_parts/<name>_story_arc.yaml` — the *initial* state: `initial_player_stats`, `initial_inventory`, `starting_location`, plus metadata (checkpoints, tags, difficulty, warnings, author, version). Contains no logic.
    *   `events/<name>_story_events.yaml` — the story's trigger→action rules. This is where the game logic lives.
    *   `events/general_events.yaml` — shared events (help command, debug info, low-health warning, location ambiance) loaded for every story.
    *   `story_parts/<name>_intro.txt` — opening narrative text, referenced by the arc's `initial_story_part`.

## Game Flow

1.  **Main menu**: discovers stories, offers "Resume Game" (from `~/.text_adventure_tui_saves/`) and a debug toggle.
2.  **Story load**: `yaml_loader` reads the arc file, then merges `general_events.yaml` + the story's events file (in that order) into one event list, and builds the initial `Player` from the arc's `initial_*` fields.
3.  **Story start**: the intro text file is loaded, then the `story_start` event (mode `MANUAL`) is executed explicitly — typically setting the opening flag/location and an `override_narrative`.
4.  **Turn loop** (repeats until an `end_game` action, a `force_end_game` checkpoint, or `/quit`):
    *   **LLM scene + choices**: the current narrative, location, health, and inventory go to the LLM, which returns a scene summary and up to 4 choices.
    *   **Pre-choice event pass**: events are evaluated with empty input, so location/turn-count/flavor events (e.g. `first_time_in_location`) can inject narrative or add choices before the player decides.
    *   **Player choice**: the player picks a number or runs a `/command`. Free text is not parsed as an input — the LLM's generated choice labels are what events match against.
    *   **Event pass with intent**: the chosen action is classified into an intent, then events are evaluated against it (`player_action_keyword` matches substrings of the choice text, `player_intent` matches the classification). A matching event's `override_narrative` replaces the story beat; otherwise the LLM narrates the outcome.
    *   **End checks**: the `game_ended*` flags or a `force_end_game` checkpoint at the current turn number end the story (success/failure/message chosen by flag).
    *   **Advance state**: `turn_count` and `turns_in_location` increment; checkpoint `prompt_injection` for this turn is queued for the next LLM call.

## Configuration

| Setting         | How to change                                        | Default                     |
| --------------- | ---------------------------------------------------- | --------------------------- |
| Ollama host     | `OLLAMA_HOST` environment variable (set at launch)   | `http://localhost:11434`    |
| Ollama model    | `OLLAMA_MODEL` environment variable (set at launch)  | `phi4:latest`               |
| Debug output    | Main menu → "Toggle Debug Output"                    | OFF                         |
| Save location   | `~/.text_adventure_tui_saves/<story_id>_<ts>.json`   | `/save` command in-game     |

## Diagram (Simplified Flow)

```
[Start] --> Main Menu --select story--> [Load arc + general + story YAML]
                                          |
                          [Player(stats, inventory) from arc initial_*]
                                          |
                          [intro .txt] + [execute story_start event]
                                          | (override_narrative)
                                          v
+-------------------------------------------------------------------------+
| Turn loop:                                                              |
|   [LLM #1: scene summary + 4 choices]  (JSON out; fallback list on err)  |
|        |                                                               |
|   [pre-choice event pass] -- inject_narrative / add_choice -->          |
|        |                                                               |
|   [player picks number / /command] -- choice label + intent              |
|        |                                                               |
|   [event pass vs GameState] -- match? -- override_narrative -----+      |
|        | no match                                              v      |
|        +--> [LLM #2: story continuation]                      [skip]   |
|        |                                                               |
|   [end? game_ended flags / force_end_game checkpoint] -- yes --> [End]  |
|        | no                                                             |
|   [turn_count++, turns_in_location++, checkpoint prompt_injection]      |
+-------------------------------------------------------------------------+
```

## Document Map

* [`README.md`](../README.md) — user-facing overview, event reference, and in-game commands.
* [`docs/customization.md`](customization.md) — how to customize the model, story content, and events.
* [`DEVELOPER_GUIDE.md`](../DEVELOPER_GUIDE.md) — authoring stories and extending the engine.
* [`docs/architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) — exhaustive deep dive with
  line-referenced call traces, load order, and verified quirks.

Earlier revisions of `docs/architecture.md` and `docs/customization.md` described a single-script,
LLM-only prototype (a top-level `game.py` with no YAML and no persistence). That design no longer
exists; those documents have been rewritten to match the current engine.

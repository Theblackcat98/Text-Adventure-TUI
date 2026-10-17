# Text-Adventure-TUI: DATA — Data models and mutable game-state façade

Prefix: DATA · Commit: 7f349d1 (2025-07-22) · Depth: deep
Scope (read fully): `text_adventure_tui_lib/data_structures.py` (45),
`text_adventure_tui_lib/game_state_manager.py` (56),
`text_adventure_tui_lib/__init__.py` (0),
`text_adventure_tui_lib/events/__init__.py` (0),
`text_adventure_tui_lib/story_parts/__init__.py` (0).
Read partially, as neighbours: `text_adventure_tui_lib/game.py`,
`text_adventure_tui_lib/event_manager.py`, `text_adventure_tui_lib/yaml_loader.py`,
`text_adventure_tui_lib/story_manager.py`, `story_tool.py`, `tests/test_game_engine.py`,
`tests/test_new_engine.py`.
Method: read + grep + AST field audit + 14 runnable probes in
`probe/data-*.py`. Limits: no Ollama server in this environment, so the live
game loop was simulated, never executed end-to-end.

## Purpose
Define the four dataclasses that carry all narrative and session data, and
expose the single mutable façade (`GameStateManager`) through which the rest of
the engine is supposed to change that data.

## Public surface
| Symbol | Kind | Location | Notes |
|---|---|---|---|
| `Player` | dataclass | `text_adventure_tui_lib/data_structures.py:5-8` | 2 fields |
| `Event` | dataclass | `text_adventure_tui_lib/data_structures.py:11-17` | 5 fields, 3 required |
| `Story` | dataclass | `text_adventure_tui_lib/data_structures.py:20-35` | 13 fields, 2 required |
| `GameState` | dataclass | `text_adventure_tui_lib/data_structures.py:38-45` | 6 fields, 2 required |
| `GameStateManager` | class | `text_adventure_tui_lib/game_state_manager.py:4-56` | 14 methods, 0 properties |
| `get_player/get_story/get_flags/get_inventory/get_stats/get_current_location/get_turn_count` | getter | `game_state_manager.py:8,11,14,24,35,41,52` | all return the **live** object |
| `set_flag/clear_flag/add_item/remove_item/update_stat` | mutator | `game_state_manager.py:17,20,27,31,38` | the only sanctioned writes |
| `set_current_location/increment_turns_in_location/increment_turn` | mutator | `game_state_manager.py:44,49,55` | |
| `to_dict/from_dict/__eq__/schema version` | absent | `data_structures.py` | verified by probe DATA-7 |

## Key data structures
### `Player`
Shape: `stats: Dict[str, Any]` (`data_structures.py:7`), `inventory: List[str]`
(`:8`). Created by `yaml_loader.py:67-70` (new format) and `yaml_loader.py:117-120`
(old format), plus `Player()` in tests. Owned by `GameState.player`
(`data_structures.py:41`). Mutated by `game_state_manager.py:29,33,39`.
Read by `event_manager.py:119,203,205,240`, `game.py:123,124`.
Lifetime: one per session; discarded and re-created from YAML on resume.

### `Event`
Shape: `id: str`, `name: str`, `trigger: Dict[str, Any]`, `actions: List[Dict[str, Any]]`,
`options: Dict[str, Any]` (`data_structures.py:12-17`). Created only by
`yaml_loader.py:20-28`. Owned by `Story.events` (`data_structures.py:24`).
Read by `event_manager.py:8,58,77,102,278`. Never mutated after construction.
Lifetime: one per loaded YAML entry.

### `Story`
Shape: 13 fields (`data_structures.py:22-35`). Created by `yaml_loader.py:75-78`
plus post-construction assignment of 10 fields at `yaml_loader.py:82-91`
(new format) and `yaml_loader.py:131-140` (old format). Owned by
`GameState.current_story` (`data_structures.py:40`).
**Lifetime: reloaded from disk on every resume — the in-save copy is discarded.**

### `GameState`
Shape: `current_story: Story`, `player: Player`, `flags: Dict[str, bool]`,
`turn_count: int`, `current_location: str`, `turns_in_location: int`
(`data_structures.py:39-45`). Created at `game.py:240-247` (resume) and
`game.py:255-259` (new game). Owned by `GameStateManager`
(`game_state_manager.py:5-6`). Lifetime: one per `game_loop` call.

## Invariants
| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| `flags` values are `bool` | nowhere | `game_state_manager.py:18` writes `True`; `tests/test_game_engine.py:76` and `tests/test_new_engine.py:85` write the **string** `"start"` (verified run: probe DATA-4 case F shows the stored value's type) |
| `inventory` has no duplicates | `game_state_manager.py:28` guard | bypassable via `get_inventory()` (`game_state_manager.py:24-25`) — verified run, probe DATA-5 case 2 |
| `turns_in_location == 0` on entering a location | `game_state_manager.py:44-47` | only fires when the string actually changes |
| `current_location` is a real location name | nowhere | no validator; `change_location` action takes any value (`event_manager.py:114-115`) |
| save file is loadable by the same build | nowhere | no schema version key (verified run: probe DATA-7 case 3) |
| every event dict has `id` | nowhere at load | hard `KeyError` at `yaml_loader.py:22` instead |

## Dependencies out
| Target | Called at | Why |
|---|---|---|
| `typing.Dict/List/Any` | `data_structures.py:2`, `game_state_manager.py:2` | annotations only |
| `dataclasses.dataclass/field` | `data_structures.py:1` | |
| `data_structures` | `game_state_manager.py:1` | `GameState, Player, Story` imported; `Event` and `GameStateManager` are not used at all in this file |

## Dependencies in
| Caller | Location | What it expects |
|---|---|---|
| `game.py` | `game.py:240-259`, `:218-230`, `:347-348`, `:362` | a `GameState` it can mutate |
| `event_manager.py` | `event_manager.py:102-125,185-241` | a `GameStateManager` facade |
| `yaml_loader.py` | `yaml_loader.py:5`, `:20-28`, `:67`, `:75` | the dataclasses constructible with keywords |
| `story_manager.py` | `story_manager.py:9` | imports `Story` — **never uses it**; only `StoryInfo` (`story_manager.py:13-24`) |

## Side effects
| Effect | Location | Trigger condition | Reversible? |
|---|---|---|---|
| writes `save_game/*.json` | `game.py:224-229` | `/save` command | no; files accumulate, never pruned |
| mutates in-memory `GameState` | `game_state_manager.py:18,22,29,33,39,46,47,50,56` | event actions and end-of-turn | yes only by resume |

## Error and edge behaviour
| Situation | What happens | Location |
|---|---|---|
| YAML event missing `id` | `KeyError: 'id'`, whole story load aborts | `yaml_loader.py:22` |
| YAML event with scalar `trigger` | loads fine, crashes on first trigger sweep: `AttributeError: 'str' object has no attribute 'get'` | `event_manager.py:180` |
| `trigger.conditions` a mapping, not a list | loads fine, same `AttributeError` later | `event_manager.py:180` |
| `set` or `datetime` inside `player.stats` | `AttributeError: '<type>' object has no attribute '__dict__'` at save time | `game.py:229` |
| `tuple` inside `player.stats` | silently becomes a `list` on reload | `game.py:229`, `game.py:242` |
| save file missing `turns_in_location` | `KeyError` on resume, unhandled | `game.py:246` |
| cyclic `GameState` | `ValueError: Circular reference detected` | `game.py:229` |

## Lifecycle and concurrency
Single-threaded, single-process, synchronous. `GameStateManager.__init__`
(`game_state_manager.py:5-6`) stores the **reference** it is given, not a copy.
**No concurrency primitive exists anywhere in the repo**: grep for
`threading|multiprocessing|asyncio|Lock(|RLock(|Semaphore|Thread(|Process(|await |async def|concurrent.futures|signal.|import signal`
across all `*.py` returns zero matches (verified run). No lock is needed because
there is exactly one writer (the `while True` loop at `game.py:276`) and the Ollama
client call at `game.py:110` blocks.

## Configuration
| Knob | Default | Source | Runtime or restart |
|---|---|---|---|
| `current_location` default | `"start"` | `data_structures.py:44` | construction |
| `total_turns_estimate` default | `20` | `data_structures.py:28` | construction |
| `version` default | `"1.0"` | `data_structures.py:35` | construction |
| `difficulty` default | `"medium"` | `data_structures.py:32` | construction |
| `author` default | `"Unknown"` | `data_structures.py:34` | construction |

## Extension points
To add a state field: add it to the dataclass (`data_structures.py`), add a
manager mutator (`game_state_manager.py`), and add a read at `game.py:240-247`
**and** a save at `game.py:225-228`. Missing the last step means the field is
silently dropped on save and `KeyError` on resume — this is exactly what
`turns_in_location` does if you edit the dataclass and forget `game.py:246`.
`DEVELOPER_GUIDE.md:538-541` promises all three steps but names no file.

## Tests
| Test file | What it actually asserts | Coverage notes |
|---|---|---|
| `tests/test_game_engine.py:15-35` | a `player_action` trigger fires | real |
| `tests/test_game_engine.py:38-59` | `turn_count_in_location >= 3` fires with `turns_in_location=3` injected at `:51` | real |
| `tests/test_game_engine.py:76` | sets a **flag** named `current_location` | bogus; see Surprises |
| `tests/test_new_engine.py:85` | same bogus flag | bogus; see Surprises |
| `tests/test_new_engine.py:47-68` | manager add/remove/set/clear | real |
| `tests/test_new_engine.py:38-46` | YAML load populates stats + inventory | real |
| none | round-trip of save/load | **no test at all** |

## Docs vs code
| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| "Extend `GameState` for new state types / Add corresponding manager methods / Update save/load serialization" | `DEVELOPER_GUIDE.md:538-540` | true but incomplete; the save/load step is `game.py:240-247`, outside the two files named | accurate |
| "State persistence for save/load" | `DEVELOPER_GUIDE.md:49` | partial: `Player` state is **not** persisted | misleading |
| "the game is stateless between sessions" | `docs/architecture.md:71` | false; `/save` writes and Resume rebuilds | stale doc |
| `data_structures.py # Game data models` | `README.md:200` | accurate | accurate |

## Unknowns
- Whether the 7 passing tests are the intended contract — `tests/` never touches
  `save_game_state` or the resume path.
- Whether any older save file exists in the wild — needs the author's machine.
- Whether the missing `Player` persistence is deliberate — needs the author.

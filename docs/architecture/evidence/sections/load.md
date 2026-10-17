# Text-Adventure-TUI: LOAD — YAML → dataclass loading (both formats)

Prefix: LOAD · Commit: `7f349d1` · Depth: deep
Scope: `text_adventure_tui_lib/yaml_loader.py` (142, read fully).
Read for context, not analysed: `text_adventure_tui_lib/game.py` (235-269, 380-466), `text_adventure_tui_lib/story_manager.py` (42-153), `text_adventure_tui_lib/event_manager.py` (1-30, 38-90, 165-180), `text_adventure_tui_lib/data_structures.py` (1-45).
Content consumed (read to judge the loader only): `events/general_events.yaml`, `events/whispers_of_the_salted_crypt_story_events.yaml`, `events/the_clockwork_heist_story_events.yaml`, `story_parts/*_story_arc.yaml`, `story_parts/Whispers_of_the_Salted_Crypt/*.yaml`, `story_parts/*.txt`.
Method: full read; 9 probes under `/tmp/opencode/cdd-text-adventure-tui/probe/load-0*.py`, all run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` (a stale 0.1.1 copy of the package in `~/.local/lib/python3.13/site-packages/` shadows the repo and has no `yaml_loader.py`). Baseline: `python -m pytest -q` → **7 passed in 0.01s**.
Limits: the game cannot be launched end-to-end here (no Ollama server), so every claim about runtime behaviour is either read off the source or demonstrated by calling the loader/`EventManager` directly, not by playing.

---

## Purpose

Turn the on-disk story YAML into the two frozen dataclasses the engine runs on (`Story` + `Player`), choosing between a modern "story arc + shared events directory" layout and a legacy "directory of chapter files" layout — `verified (read: text_adventure_tui_lib/yaml_loader.py:32-45)`.

---

## Public surface

| Symbol | Kind | Location | Notes |
|---|---|---|---|
| `load_story_and_player(story_name: str, stories_path: Path) -> Tuple[Story, Player]` | public function, the module's only exported name | `yaml_loader.py:32-93` | Sole entry point of the format bridge; called from `game.py:239`, `game.py:254`, `story_manager.py:144` — `verified (read: text_adventure_tui_lib/game.py:17)` |
| `_load_yaml(file_path: Path) -> Any` | private helper | `yaml_loader.py:8-11` | Bare `yaml.safe_load`, `open()` with **no `encoding=`** — `verified (read: yaml_loader.py:10)` |
| `_create_events_from_data(event_data) -> List[Event]` | private helper | `yaml_loader.py:14-29` | The single place raw dicts become `Event`; the only hard `KeyError` in the file is `data["id"]` at line 22 |
| `_load_story_old_format(story_name, stories_path)` | private helper, the "backward compatibility" branch | `yaml_loader.py:96-142` | Reached only from line 45 |

There is no `__all__`, no CLI, no registration, no logging — `verified (read: yaml_loader.py:1-142)`.

---

## Key data structures

### `Story` (output)
Shape: `id, title, events, starting_location, initial_story_part, total_turns_estimate, description, checkpoints, tags, difficulty, content_warnings, author, version` — `verified (read: data_structures.py:20-35)`.
Created by `yaml_loader.py:75-79` (new branch) and `yaml_loader.py:128` (old branch).
Owned by: `GameState.current_story` — `verified (read: data_structures.py:40)`.
Mutated by: the loader only, immediately after construction, by attribute assignment (`yaml_loader.py:82-91` / `131-140`) — the fields exist purely because the dataclass declares them; the loader writes them post-hoc rather than through the constructor.
Read by: `game.py:258` (`story.starting_location`), `game.py:264` (`story.initial_story_part`), `game.py:221` (`story.id`), and `story.checkpoints` further down `game_loop` — `verified (read: game.py:221, 254-269)`.
Lifetime: one per `game_loop` invocation; thrown away when the player quits or returns to the menu — `inferred (because game_loop rebuilds it on every entry and holds no module-level reference)`.

### `Player` (output)
Shape: `stats: Dict[str, Any]`, `inventory: List[str]` — `verified (read: data_structures.py:5-8)`.
Created by `yaml_loader.py:66-69` (new) and `yaml_loader.py:118-121` (old).
Lifetime: one per `game_loop`, wrapped in `GameState` — `verified (read: game.py:240-260)`.

### `Event` (output, many per story)
Shape: `id: str` (required), `name: str`, `trigger: Dict`, `actions: List[Dict]`, `options: Dict` — `verified (read: data_structures.py:11-17)`.
Created by `yaml_loader.py:20-28`, one per raw YAML mapping, in list order.
Read by: `EventManager.__init__` collapses the list into a dict at `event_manager.py:8` — so **list order is load-bearing** (see *Invariants*).

### Raw intermediate `all_events: List[Dict]` (throwaway)
`yaml_loader.py:49` — the concatenation of `general_events.yaml` (`:52-56`) and `<story>_story_events.yaml` (`:59-63`); the whole story's YAML is held in memory simultaneously before any `Event` exists — `verified (read: yaml_loader.py:49-63)`.

---

## Invariants

| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| `Story.id` equals the arc-file basename | `yaml_loader.py:76` (`id=story_name`) | Nothing checks it; it holds only because `story_manager` derives ids the same way at `story_manager.py:53` — `verified (read: story_manager.py:53, yaml_loader.py:76)` |
| An event mapping always has an `id` key | Nowhere | `yaml_loader.py:22` hard-indexes and raises a bare `KeyError: 'id'` with **no file name and no line number** — `verified (run: probe load-03-errors.py, case c)` |
| Each events file's top level is a list of mappings | Nowhere in the loader | `story_manager.validate_story` (`story_manager.py:112-113`), and only for the *story* file — `verified (read: story_manager.py:103-113)` |
| Event ids are unique across general + story files | Nowhere | Shipped files happen to be disjoint (`general ∩ story = ∅`) — `verified (run: probe load-07-saveroundtrip.py)` |
| `data.get(key, default)` protects against a missing key | Everywhere **except** `id` | `yaml_loader.py:23-26` vs `:22` |
| `data.get(key, default)` does **not** protect against a *null* value | Nowhere | YAML `trigger:` with no value yields `None`, not `{}`; see *Surprises* — `verified (run: probe load-09-nullkeys.py)` |
| Event **list order** == file order, and general events come first | `yaml_loader.py:52-63`, `:73` | Load-bearing because `event_manager.py:50` iterates `self.events.items()` and `:80-81` **breaks on the first `override_narrative`** — so a general event can shadow a story event — `verified (read: event_manager.py:50, 80-81)` |
| `<story_name>_story_events.yaml` exists | Nothing | Its absence is only a `print`-to-stdout warning in `story_manager.py:104-105`; the loader silently loads fewer events — `verified (read: yaml_loader.py:60-63)` |
| `story_start` event exists | `story_manager.py:116-122` (error) and `yaml_loader.py:112-116` (old branch only) | The **new** branch never checks; a story with no `story_start` still loads, then `game.py:272` prints `DEBUG: Event 'story_start' not found` and the intro `.txt` is used verbatim — `verified (read: game.py:272, event_manager.py:24-30)` |

---

## Dependencies out

| Target | Called at | Why |
|---|---|---|
| `yaml.safe_load` (PyYAML, `SafeLoader`) | `yaml_loader.py:11` | The only parser used; `yaml.safe_load` never executes arbitrary tags |
| `pathlib.Path.exists` / `.parent` | `yaml_loader.py:41, 48, 53, 60` | Path arithmetic + existence probing |
| `pathlib.Path.glob("*.yaml")` | `yaml_loader.py:103` | Old-branch chapter discovery (**unsorted** — see *Surprises*) |
| `open()` (builtin) | `yaml_loader.py:10` | Reads each YAML file; **no `encoding=`**, **no `newline=`** |
| `dataclasses` `Player` / `Event` / `Story` | `yaml_loader.py:5, 20-28, 66, 75, 118, 128` | Output types |
| `event_manager` / `game` / `game_state_manager` / `rich` / `ollama` | — | **Not imported.** The loader is dependency-free apart from PyYAML and stdlib — `verified (read: yaml_loader.py:1-5)` |

---

## Dependencies in

| Caller | Location | What it expects |
|---|---|---|
| `game_loop` (new game) | `game.py:254` then `game.py:258` | `story.starting_location` to be a non-`None` string |
| `game_loop` (resume) | `game.py:239` then `game.py:240-247` | Same, plus `story.events` — but it takes flags/turn/location from the save file, not from the freshly loaded story — `verified (read: game.py:237-250)` |
| `game_loop` | `game.py:264` | `story.initial_story_part` to be a bare filename resolvable under `story_parts/` |
| `game_loop` | `game.py:272` | An event with id `story_start` to exist in `story.events` |
| `save_game_state` | `game.py:221` | `story.id` to be a filesystem-safe stem for a `.json` filename |
| `main_menu` | `game.py:397` → `story_manager.discover_stories` (`story_manager.py:47`) | Does **not** call the loader; it re-parses arc YAML itself at `story_manager.py:49` |
| `main_menu` (resume) | `game.py:451` | The `id` persisted in the save file (`story_manager`/`game.py:229`) must round-trip back into `load_story_and_player` |
| `StoryManager.validate_story` | `story_manager.py:144` | Wraps the call in `try/except Exception` (`story_manager.py:145-146`), so it is the only caller that tolerates loader failures |
| `story_tool.py` | via `StoryManager(stories_path, events_path)` | Indirect: `create_story_template` writes arc + events files that this loader must later read — `verified (read: story_manager.py:155-256, story_tool.py:12-15)` |

---

## Side effects

| Effect | Location | Trigger condition | Reversible? |
|---|---|---|---|
| Reads up to 3 YAML files per call | `yaml_loader.py:42, 54, 61` | every `load_story_and_player` | N/A (read-only) |
| Reads N YAML files in the old branch | `yaml_loader.py:103-104` | every `_load_story_old_format` | N/A |
| Creates `Event` objects | `yaml_loader.py:20-28` | per event mapping | N/A |
| **Mutates a freshly built `Story`** after construction | `yaml_loader.py:82-91`, `:131-140` | always | N/A |
| **Writes nothing** | — | — | `verified (read: yaml_loader.py:1-142)` — the module contains no `open(...,"w")`, no `mkdir`, no global |

The loader is a pure function of the filesystem. Its only non-obvious side effect is I/O volume (see *Lifecycle*).

---

## Error and edge behaviour

| Situation | What happens | Location |
|---|---|---|
| `<name>_story_arc.yaml` missing | Falls through to `_load_story_old_format` | `yaml_loader.py:41-45` |
| Old branch, no directory / no `*.yaml` / all empty | `ValueError: No events found for story '<name>'.` | `yaml_loader.py:108-109` — `verified (run: probe load-03-errors.py, case f)` |
| Old branch, no `story_start` event | `StopIteration` caught → `ValueError: Could not find 'story_start' event in any YAML file for '<name>'.` | `yaml_loader.py:111-116` — `verified (run: probe load-03-errors.py, case g)` |
| Old branch, `story_start` present but `setup_info` is not a mapping | `setup_info["id"]` raises `TypeError` | `yaml_loader.py:112, 123` |
| Story arc file exists but is **empty** | `yaml.safe_load` → `None`; `None.get(...)` → `AttributeError: 'NoneType' object has no attribute 'get'` at line 67 | `yaml_loader.py:42, 67` — `verified (run: probe load-03-errors.py, case e)` |
| Story arc file is a YAML **list** | Same `AttributeError`, at line 72 or 67 depending on order | `yaml_loader.py:67` |
| Events file top level is a **mapping** | `all_events.extend(mapping)` extends with the mapping's **keys** (strings); `data["id"]` → `TypeError: string indices must be integers, not 'str'` | `yaml_loader.py:56/63 → 22` — `verified (run: probe load-03-errors.py, case a)` |
| Events file top level is a **list of strings** | Same `TypeError` | `yaml_loader.py:22` — `verified (run: probe load-03-errors.py, case b)` |
| An event mapping **missing `id`** | `KeyError: 'id'` — no filename, no line, no index | `yaml_loader.py:22` — `verified (run: probe load-03-errors.py, case c)` |
| `general_events.yaml` malformed | Same crash as above, at line 54 — and `validate_story` never looks at this file | `yaml_loader.py:52-56` — `verified (run: probe load-03-errors.py, case d)` |
| Invalid YAML syntax | `yaml.YAMLError` propagates uncaught from `_load_yaml` | `yaml_loader.py:11` |
| Non-UTF-8 bytes in any file | `UnicodeDecodeError` from `open()` | `yaml_loader.py:10` — see *Configuration* |
| `<story>_story_events.yaml` missing | Silently loads only `general_events.yaml`; no warning, no log | `yaml_loader.py:60-63` |
| `initial_story_part` file missing | Loader does not notice; `game.py:268-269` swallows `FileNotFoundError` and substitutes the literal `"The story begins..."` | `game.py:265-269` |

### The three requested failure modes, side by side

| Case | YAML | Exception | `validate_story` verdict | Caught first by |
|---|---|---|---|---|
| (a) mapping, not list | `story_start:\n  id: story_start` | `TypeError: string indices must be integers, not 'str'` (`yaml_loader.py:22`, raised from `:73`) | **is_valid=False**, errors: `Events file must contain a list of events` (`story_manager.py:112-113`) **and** `Failed to load story: string indices must be integers...` (`story_manager.py:144-146`) | `validate_story`, by its own `isinstance` check — `verified (run: probe load-03-errors.py)` |
| (b) list of strings | `- "story_start"\n- "some_event"` | same `TypeError` | **is_valid=False**, errors: `Events file must contain a 'story_start' event` (`story_manager.py:121-122`), `Event 0 is not a dictionary`, `Event 1 is not a dictionary` (`story_manager.py:126-128`), plus `Failed to load story: ...` | `validate_story` — but note it needs *three* independent checks to name it, and the crash message is identical to case (a) — `verified (run: probe load-03-errors.py)` |
| (c) event missing `id` | `- id: story_start …` + `- name: no id here` | `KeyError: 'id'` | **is_valid=False**, error: `Event 1 missing required 'id' field` (`story_manager.py:130-131`) | `validate_story` — `verified (run: probe load-03-errors.py)` |

The distinction that matters: `validate_story` catches (a) and (b) only because it re-parses the same file with its own `isinstance` checks; it catches (c) only because it happens to test the same key. **The loader itself catches nothing** — every one of the three escapes as a raw Python exception.

---

## Lifecycle and concurrency

- **No caching of any kind.** `grep -rn "lru_cache|@cache|functools|_CACHE|memo" text_adventure_tui_lib/ story_tool.py tests/` finds no code hits at all (only the English word "memory" inside `story_parts/idea.txt`) — `verified (run: grep)`.
- Every call re-reads and re-parses everything from disk. Measured with a `builtins.open` counter, 3 `main_menu` iterations + 1 game start of `whispers_of_the_salted_crypt` — `verified (run: probe load-05-readcount.py)`:

  | File | Reads | Why |
  |---|---|---|
  | `whispers_of_the_salted_crypt_story_arc.yaml` | **4** | 3× `discover_stories` (`story_manager.py:49`) + 1× `load_story_and_player` (`yaml_loader.py:42`) |
  | `the_clockwork_heist_story_arc.yaml` | 3 | 3× `discover_stories` |
  | `general_events.yaml` | 1 | `yaml_loader.py:54` |
  | `whispers_of_the_salted_crypt_story_events.yaml` | 1 | `yaml_loader.py:61` |
  | `01_intro.txt` | 1 | `game.py:266` |
  | **total** | **10** | |

  Each menu iteration re-reads every arc file for the menu list; the selected story's arc is then parsed a fourth time. At this content size (~10 KB total) the cost is negligible — `inferred (because the largest single file is 10.8 KB and parse time is sub-millisecond)`.
- `EventManager(...)` construction reads nothing — `verified (run: probe load-05-readcount.py)`.
- Re-entrancy: safe. `load_story_and_player` is a pure function with no module-level state; two calls cannot interfere — `verified (read: yaml_loader.py:1-142)`.
- Concurrency: not designed for it. Two threads loading the same story would each re-read from disk (no shared cache, so no corruption, just duplicated I/O); `_load_yaml` uses a scoped `with open(...)` so the file handle is always closed — `verified (read: yaml_loader.py:10-11)`.
- Teardown: none needed; the module holds no handles, no globals, no registrations.
- `Story`/`Player` outlive the loader: the loader's locals become the live game state, so mutating a `Story` after return (which the loader itself does at `:82-91`) is permanent — `verified (read: yaml_loader.py:82-91, data_structures.py:20-35)`.

---

## Configuration

| Knob | Default | Source | Runtime or restart |
|---|---|---|---|
| `stories_path` | `Path(__file__).parent / "story_parts"` | `game.py:235`, `game.py:389` | per call |
| events directory | **hardcoded** `stories_path.parent / "events"` | `yaml_loader.py:48` | per call — **not a parameter** |
| `--stories-path` / `--events-path` CLI flags | `text_adventure_tui_lib/story_parts`, `text_adventure_tui_lib/events` | `story_tool.py:13-16` | process |
| YAML parser | `yaml.safe_load` | `yaml_loader.py:11` | not configurable |
| Text encoding | **locale default** (`open()` with no `encoding=`) | `yaml_loader.py:10`; also `game.py:266` | not configurable |
| Story-arc field defaults | see table below | `yaml_loader.py:82-91` | per load |
| Old-branch field defaults | hardcoded | `yaml_loader.py:131-140` | per load |

### Encoding

`_load_yaml` opens with `open(file_path, "r")` — no `encoding=` — `verified (read: yaml_loader.py:10)`. The same omission exists at `game.py:266` for the intro `.txt`.

Non-ASCII content actually shipped (UTF-8 on disk, verified byte-wise):

| File:line | Characters | Notes |
|---|---|---|
| `events/general_events.yaml:73` | `•` U+2022 BULLET | inside the `help_command` event's `override_narrative` |
| `events/general_events.yaml:74` | `•` U+2022 | ditto |
| `events/general_events.yaml:75` | `•` U+2022 | ditto |
| `events/general_events.yaml:76` | `•` U+2022 | ditto |
| `story_parts/idea.txt:7, 15, 19, 23` | `–` U+2013 EN DASH | `idea.txt` is referenced by nothing, so it never loads |
| everything else (`*_story_arc.yaml`, both story-events files, all 4 old-format chapter files, `01_intro.txt`, `clockwork_intro.txt`, `whispers_intro.txt`) | pure ASCII | `verified (run: python utf-8 decode sweep)` |

Consequence, demonstrated — `verified (run: probe load-06-encoding.py)`:

| Environment | `locale.getpreferredencoding(False)` | Result |
|---|---|---|
| default | `UTF-8` | both stories load, 16 events each |
| `LC_ALL=C LANG=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0` | `ANSI_X3.4-1968` | **`UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 1934`** for **both** stories |

The crash lands at `yaml_loader.py:54` — i.e. on `general_events.yaml`, the *first* events file read, so **every** story dies, not just the two that reference the bullets. And because `main_menu` has no `try/except` around `game_loop(...)` (`game.py:435`) and the only `try` in `main_menu` guards `ollama.Client` construction (`game.py:382-386`), the menu will happily list the stories (the arc files are ASCII, so `discover_stories` at `story_manager.py:49` survives) and then the game exits with a raw traceback the moment a story is chosen — `verified (read: game.py:382-386, 435, 451)`. No emoji exist in any shipped content file; the `📖` in `story_tool.py:55` is source code, not loaded data.

### Loader defaults vs `@dataclass` defaults

Every field the loader reads has an explicit `.get(...)` default (`yaml_loader.py:82-91`) that **agrees** with the dataclass default (`data_structures.py:26-35`). There are **zero** disagreements — `verified (run: probe load-04-defaults.py)`:

| Field | Loader `.get` default | `Story` dataclass default | Agree? |
|---|---|---|---|
| `starting_location` | `"start"` | `"start"` (`:26`) | yes |
| `initial_story_part` | `"01_intro.txt"` | `"01_intro.txt"` (`:27`) | yes |
| `total_turns_estimate` | `20` | `20` (`:28`) | yes |
| `description` | `""` | `""` (`:29`) | yes |
| `checkpoints` | `[]` | `field(default_factory=list)` (`:30`) | yes (dataclass is safer) |
| `tags` | `[]` | `field(default_factory=list)` (`:31`) | yes |
| `difficulty` | `"medium"` | `"medium"` (`:32`) | yes |
| `content_warnings` | `[]` | `field(default_factory=list)` (`:33`) | yes |
| `author` | `"Unknown"` | `"Unknown"` (`:34`) | yes |
| `version` | `"1.0"` | `"1.0"` (`:35`) | yes |

Conversely, **every** `Story` field is populated by the loader — there are no orphan dataclass fields — `verified (run: probe load-04-defaults.py)`. The two default sets being redundant is itself the smell: `yaml_loader.py:82-91` re-states every default that `data_structures.py:26-35` already guarantees, and could be replaced by a single `Story(**filtered_kwargs)` or by deleting the overrides and letting the dataclass defaults apply.

---

## Extension points

The first file a contributor edits when adding a story field is **`text_adventure_tui_lib/yaml_loader.py`** — specifically `yaml_loader.py:82-91` for the new branch and `yaml_loader.py:131-140` for the old branch. Adding e.g. `Story.mood` requires four coordinated edits:

| Step | File:line |
|---|---|
| 1. declare the field + default | `data_structures.py:20-35` |
| 2. read it from the arc | `yaml_loader.py:82-91` (and the old-branch default list at `:131-140`) |
| 3. surface it in the menu | `story_manager.py:55-65` |
| 4. document it | `README.md:53-78`, `README_OLD.md:164-214`, `DEVELOPER_GUIDE.md:176-199` |

Other extension seams:
- **A new events source**: add an `extend()` block between `yaml_loader.py:56` and `yaml_loader.py:63`. Order matters — sources added earlier get earlier dict slots and therefore precedence under the `break` at `event_manager.py:80-81`.
- **A new story layout**: extend the branch at `yaml_loader.py:41-45`. The branch key is *only* "does `<name>_story_arc.yaml` exist" (`yaml_loader.py:38, 41`) — there is no explicit format marker, no version field, no content sniffing.
- **Authoring a new story**: `story_tool.py create` → `story_manager.create_story_template` (`story_manager.py:155-256`) writes `<id>_story_arc.yaml`, `<id>_intro.txt` and `events/<id>_story_events.yaml`. Note `create_story_template` writes `initial_story_part: f"{story_id}_intro.txt"` (`story_manager.py:161`) and `intro_file = self.stories_path / f"{story_id}_intro.txt"` (`story_manager.py:201`) — consistent — but it writes the arc to `self.stories_path` and the events to `self.events_path`, whereas the loader *ignores* `events_path` and derives `stories_path.parent/"events"` — see *Surprises*.

---

## Tests

| Test file | What it actually asserts | Coverage notes |
|---|---|---|
| `tests/test_new_engine.py:36-42` | `story.id == "story_start"`, `story.title == "Test Story"`, `len(story.events) > 0`, `player.stats["health"] == 100`, `"a rusty key" in player.inventory` | **The only test of `load_story_and_player` in the repo** — and it exercises the **OLD** branch (`yaml_loader.py:45`), because the fixture at `:16-33` creates a *directory* `tmp_path/"test_story"` with `game_setup.yaml` inside and no `<name>_story_arc.yaml` — `verified (read: tests/test_new_engine.py:15-42)` |
| `tests/test_game_engine.py:9` | nothing — `load_story_and_player` is imported and **never called** (0 call sites in the file) | `verified (run: grep -c "load_story_and_engine(" → 0)` |
| `tests/test_game_basics.py` | 3 lines; no loader involvement | `verified (read: tests/test_game_basics.py:1-3)` |
| Baseline | `python -m pytest -q` → **7 passed in 0.01s** | `verified (run: pytest -q)` |

**Coverage gap:** the new-format branch (`yaml_loader.py:41-93`) — the branch both shipped stories actually use, and the branch that assembles `general_events.yaml` + story events — has **zero** test coverage. Nothing pins the event ordering, the defaults table, or the `KeyError` behaviour. `verified (run: grep -n "load_story_and_player" tests/*.py → 2 hits: one import in test_game_engine.py, one import + one call in test_new_engine.py)`.

The test at `test_new_engine.py:38` **asserts the bug**: `story.id == "story_start"` — the story's id is the setup event's id (`yaml_loader.py:123`). Any fix to that line breaks this test.

---

## Surprises

- **The old-format branch reads a story *event* as if it were story metadata.** `setup_info = next(e for e in all_events if e["id"] == "story_start")` (`yaml_loader.py:112`) selects one event mapping, then that same mapping is mined for `initial_player_stats` (`:119`), `initial_inventory` (`:120`), `story.id` (`:123`) and `title` (`:124`). The only shape that works is `test_new_engine.py:20-33`'s: `initial_player_stats`/`initial_inventory` **nested inside the `story_start` event**. No other shape is read — they would have to be top-level keys of the YAML file, which is impossible because the top level must be a list (`yaml_loader.py:106`). **No shipped old-format file follows it** — all four files under `story_parts/Whispers_of_the_Salted_Crypt/` lack both keys (`verified (run: probe load-01-routing.py, last section)`), so an old-format player always starts with `stats={}` and `inventory=[]`.
- **The old-format branch produces `story.id == "story_start"`, always.** `story_id = setup_info["id"]` (`yaml_loader.py:123`) is the literal `"story_start"` string in `Whispers_of_the_Salted_Crypt/game_setup.yaml:1` — not a story identifier at all. `verified (run: probe load-01-routing.py)` → `story.id='story_start'`, `story.title='The Missing Mentor'` (from `setup_info["name"]`, `game_setup.yaml:2`, via the `title`→`name` fallback at `yaml_loader.py:124`), `starting_location='start'` (hardcoded, `:131`), `initial_story_part='01_intro.txt'` (hardcoded, `:132` — **which is the other, new-format story's intro file**).
- **Those three values are load-bearing across save/resume, and they break it.** `game.py:221` names the save `f"{story_state_manager.get_story().id}_{timestamp}.json"`, so an old-format save is called **`story_start_20261012_101112.json`** (`verified (run: probe load-01-routing.py)`). Resume then feeds that id back in at `game.py:451` → `load_story_and_player("story_start", ...)` → no `story_start_story_arc.yaml` → old branch → no `story_parts/story_start/` directory → `ValueError: No events found for story 'story_start'.` **Old-format saves can never be resumed.** `verified (run: probe load-07-saveroundtrip.py)`. The new branch round-trips cleanly: `whispers_of_the_salted_crypt_20261012_101112.json` → reload OK.
- **The whole `story_parts/Whispers_of_the_Salted_Crypt/` directory is dead content in the shipped game.** It is only reachable via the story id `Whispers_of_the_Salted_Crypt`, which **nothing ever produces**: `story_manager.discover_stories` globs `*_story_arc.yaml` (`story_manager.py:47`), there is no `Whispers_of_the_Salted_Crypt_story_arc.yaml`, and `validate_story` hard-requires one (`story_manager.py:80-83`). `grep -rn "Whispers_of_the_Salted_Crypt"` matches **only** `text_adventure_tui.egg-info/SOURCES.txt:25-28` — `verified (run: grep)`. All four files (`game_setup.yaml`, `chapter1_study.yaml`, `chapter2_coast.yaml`, `chapter3_crypt.yaml`) would be picked up by the old branch's `story_path.glob("*.yaml")` (`yaml_loader.py:103`) **if** that id were ever passed — proven by forcing `_load_story_old_format("Whispers_of_the_Salted_Crypt", ...)`, which yields 8 events. They also ship in the wheel (`MANIFEST.in:4` + `setup.py:45 include_package_data`), confirmed by the 0.1.1 wheel listing. Meanwhile the *same story* is playable in its new format via `whispers_of_the_salted_crypt_story_arc.yaml` — so there are two divergent, independently-maintained copies of one story in the tree.
- **Old-branch chapter order is filesystem order, not sorted.** `story_path.glob("*.yaml")` (`yaml_loader.py:103`) is **not** wrapped in `sorted()`. On this machine it happens to yield `chapter1, chapter2, chapter3, game_setup` (verified), so `story_start` lands **last** in the event list, not first. `inferred (because `Path.glob` returns `os.scandir` order, which is filesystem-dependent and not guaranteed alphabetical — it matched `sorted()` here only by luck of creation order)`. Since `EventManager` iterates in that order (`event_manager.py:50`), re-creating these files on a different filesystem can reorder event precedence.
- **General events are loaded first and therefore win.** `general_events.yaml` is `extend`ed at `yaml_loader.py:56`, before story events at `:63`. The resulting `EventManager` dict order is verified for both stories — `verified (run: probe load-02-order.py)`:

  | # | Key (identical for both stories) | Source |
  |---|---|---|
  | 0-5 | `low_health_warning`, `inventory_full_warning`, `first_time_in_location`, `long_time_in_location`, `help_command`, `debug_info` | `events/general_events.yaml` |
  | 6 | `story_start` | story events file |
  | 7-15 | the 9 story-specific ids (e.g. `find_elians_journal` … `end_story_success_cautious` for whispers; `scout_museum` … `desperate_escape` for clockwork) | story events file |

  Both stories load 16 events, dict order == list order, no duplicates. Because `check_and_trigger_events` `break`s on the first `override_narrative` (`event_manager.py:80-81`), typing `help` fires `help_command` (index 4, general) and **aborts the whole scan**, so no story event gets to override the narrative on that turn.
- **Duplicate event ids are resolved silently, last-wins.** `EventManager.__init__` uses `{event.id: event for event in events}` (`event_manager.py:8`). Since story events are appended *after* general events (`yaml_loader.py:63`), a story event reusing a general id silently **overwrites** the general one while keeping the *original* insertion position. `verified (run: probe load-02-order.py)`: input `['low_health_warning', 'low_health_warning', 'inventory_full_warning', …]` → dict `['low_health_warning', 'inventory_full_warning', …]`, `len(list)=7`, `len(dict)=6`, and the surviving `low_health_warning` is the **second** (story) copy. No warning, no log, no validation check for duplicates exists anywhere (`story_manager.py:125-137` loops but never compares ids).
- **Unknown event keys are silently discarded.** `_create_events_from_data` reads only `id`, `name`, `trigger`, `actions`, `options` (`yaml_loader.py:21-27`). Every other key an author writes into an event — including a typo like `option:` instead of `options:` — vanishes with no diagnostic. Shipped keys are exactly those five (`verified (run: probe load-07-saveroundtrip.py)`).
- **YAML `null` defeats every `.get(key, default)` in the loader.** `trigger:` with no value parses as `None`, and `data.get("trigger", {})` returns `None` because the key *exists*. The loader hands `None` straight to `EventManager`, which crashes: `AttributeError: 'NoneType' object has no attribute 'get'` at `event_manager.py:170` (`trigger`) and at `event_manager.py:52` (`options`). `verified (run: probe load-09-nullkeys.py)`. `actions:` null passes the loader too (no crash until the event actually fires, at `for action in event.actions` — `event_manager.py:102`). `story_manager` only checks *key presence*, never key *type* (`story_manager.py:133-137`), so validation passes these files.
- **The events directory is derived, not passed.** `events_path = stories_path.parent / "events"` (`yaml_loader.py:48`). `StoryManager` accepts an explicit `events_path` (`story_manager.py:38-40`) and uses it for its own checks (`story_manager.py:103`), then calls `load_story_and_player(story_id, self.stories_path)` (`story_manager.py:144`) — which ignores it. With `--stories-path content --events-path elsewhere`, **validation reads one file and the loader reads a different one**: `verified (run: probe load-08-eventspath.py)` → the loader loaded only `general_events.yaml` and never saw `elsewhere/demo_story_events.yaml`, yet `validate_story` reported **zero errors** because it validated the file nobody loads. A story can therefore validate clean and then play with its `story_start` event missing.
- **Every `Story` field's default is written twice.** `yaml_loader.py:82-91` restates all ten defaults already declared at `data_structures.py:26-35`, and `yaml_loader.py:131-140` restates them a *third* time as literals. They currently agree (verified), but there is no test pinning them, so a one-sided edit silently diverges.
- **The `_load_yaml` encoding omission breaks both stories on any non-UTF-8 default locale** — see *Configuration*. `game.py:266` has the same omission for the intro `.txt`.

---

## Docs vs code

| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| "Supports backward compatibility" (`DEVELOPER_GUIDE.md:57`) | `DEVELOPER_GUIDE.md:52-57` | `_load_story_old_format` exists and works (`yaml_loader.py:96-142`), but **zero shipped stories reach it**; its only exercise in the whole repo is one unit test (`test_new_engine.py:36`) | **True but vestigial** — the branch is tested for the dead format and untested for the live one |
| Story arc schema (`README.md:53-78`) | `README.md:53-78` | Matches `yaml_loader.py:66-91` key-for-key; `initial_player_stats`/`initial_inventory` are read at `:67-68` | **Accurate** |
| `initial_story_part` "Defaults to `01_intro.txt` if not specified" | `README_OLD.md:167` | `yaml_loader.py:83` (new) and `:132` (old) both default to `"01_intro.txt"` | **Accurate** |
| Events file schema (`README.md:80-106`) — list of event mappings with `id`/`name`/`options`/`trigger`/`actions` | `README.md:80-106` | Loader requires `id` (`yaml_loader.py:22`), defaults the other four (`:23-26`). README's example never mentions that `initial_player_stats` belongs *inside* `story_start` for the old format | **Accurate for the new format; silent about the old one** |
| Old-format docs put `initial_player_stats` / `initial_inventory` at the **top level of the arc file** | `README_OLD.md:171-179`, `DEVELOPER_GUIDE.md:182-185` | Correct for the new branch (`yaml_loader.py:67-68`); **wrong for the old branch**, which requires them inside the `story_start` event (`yaml_loader.py:119-120`) | **Misleading — no doc anywhere shows the old format's required shape except `test_new_engine.py:20-33`** |
| `initial_story_part` "If omitted, the game might default to a common intro or require an initial event to provide the narrative" | `README_OLD.md:202` | Silent `FileNotFoundError` → `"The story begins..."` (`game.py:268-269`), unless `story_start` supplies `override_narrative` (`game.py:272-274`) | **Accurate, understated** |
| Story discovery "Discovers available stories automatically" | `DEVELOPER_GUIDE.md:40` | True — but only arc files (`story_manager.py:47`); the old-format directory is invisible | **Accurate but hides the dead branch** |
| Advanced event patterns (`DEVELOPER_GUIDE.md:320-386`) — `inject_narrative` with `position`, `modify_prompt`, `present_choices` with `condition` | `DEVELOPER_GUIDE.md:322-386` | The loader passes `actions` through **verbatim and unvalidated** (`yaml_loader.py:25`), so these shapes load iff `event_manager._perform_actions` handles them | **Loader is agnostic and correct here; schema ownership is entirely `event_manager`'s** (EVT section) |

---

## DATA-layer block (deserialisation / schema checklist)

| Question | Answer |
|---|---|
| Where is the schema declared? | Nowhere as a machine-readable artefact. It is implied by the `.get(...)` calls at `yaml_loader.py:23-26, 67-68, 72, 82-91` and by the dataclass at `data_structures.py:11-35`. There is no JSON Schema, no Pydantic model, no TypedDict, no `**kwargs` whitelist — `verified (read: yaml_loader.py:1-142)`. |
| Is `id` the key? | Yes, but only informally: the *event* key is `id` (`yaml_loader.py:22`), and the *story* key is the filename stem, which is never written into the YAML at all (`yaml_loader.py:76`) — `verified (read: yaml_loader.py:76)` |
| Constraints enforced at load | Exactly one: the top-level `id` key of each event, enforced by an unguarded subscript (`yaml_loader.py:22`) |
| Constraints *not* enforced | container types, `id` uniqueness, `id` string-ness, `trigger`/`actions`/`options` shapes, action `type` vocabulary, condition `type` vocabulary, `initial_player_stats` value types, `total_turns_estimate` being an int, `initial_story_part` existing, `checkpoints` entries having `turn` |
| Schema versioning / migration | None. The only version-ish field is `Story.version`, a free-form string defaulting to `"1.0"` (`yaml_loader.py:91`, `data_structures.py:35`) that **nothing ever reads** — `verified (run: grep -rn "\.version\b" → the only other hit, story_tool.py:142, prints `story_info.version` from the separate `StoryInfo` dataclass filled by `story_manager.py:64`, never from the loader's `Story.version`)`. The branch at `yaml_loader.py:41-45` is a *filename* sniff, not a version check. |
| Backward compatibility | Implemented as a second code path (`yaml_loader.py:96-142`) selected by filename existence. It is not additive: the two paths share **no** metadata parsing — the old branch hardcodes ten values instead of reading them (`yaml_loader.py:131-140`) and reads a different source for player stats (`:119-120` vs `:67-68`). |
| Transaction / atomicity | N/A for reads. But the loader has **no partial-result contract**: it builds `all_events` first (`:49-63`) and only then constructs `Story` (`:75-79`), so a bad event aborts before any object escapes — good. However `_load_story_old_format` raises `ValueError` for the empty case (`:109`) but lets raw `TypeError`/`KeyError` escape for malformed ones — inconsistent error contract. |
| Serialisation (the write side) | Out of scope for this file, but coupled: `json.dump(..., default=lambda o: o.__dict__)` (`game.py:229`) serialises whatever the loader produced, including the bogus `id="story_start"` — that is how the unresumable-save bug in *Surprises* is persisted. |
| Delete / orphan semantics | N/A. `idea.txt`, `whispers_intro.txt` and the whole `Whispers_of_the_Salted_Crypt/` tree are orphans: nothing loads them, nothing garbage-collects them, and `MANIFEST.in:3-4` + `setup.py:45` ship all of them into the wheel — `verified (run: grep whispers_intro → 0 hits; MANIFEST.in:3-4; wheel listing)`. |
| Connection lifecycle | N/A. File handles are opened and closed per file via a scoped `with` (`yaml_loader.py:10`) — no pool, no leak, no fd exhaustion risk for 1-3 files. |
| Hot-path cost | `load_story_and_player` is called **once** per `game_loop` entry (`game.py:239`/`254`), never per turn — not on the hot path. The repeated arc parsing happens in `discover_stories` (`story_manager.py:47, 49`), i.e. per menu iteration, which is cold-path. |
| Determinism | New branch: fully deterministic (file order is explicit at `yaml_loader.py:56, 63`). Old branch: `Path.glob` is unsorted (`yaml_loader.py:103`) — order depends on the filesystem, so event precedence is not reproducible across machines — `inferred (because Path.glob does not sort; it preserves os.scandir order)`. |

### Which YAML defects reach `EventManager` unchallenged

Cross-checked against `story_manager.validate_story` (`story_manager.py:74-153`), which is a *different* file and re-parses the arc + **only the story events file** (`story_manager.py:87-88, 109-110`) — it never opens `general_events.yaml` (`story_manager.py:103` hard-codes `<story_id>_story_events.yaml`).

| Defect | `validate_story` | Loader | Ends up in `EventManager` as |
|---|---|---|---|
| any defect in `events/general_events.yaml` | **never checked** | loaded at `yaml_loader.py:54` | whatever it contains, or a crash at `:22` — `verified (run: probe load-03-errors.py, case d)` |
| duplicate event id across general + story files | never checked | both loaded (`:56, :63`) | **last wins, silently** (`event_manager.py:8`) |
| duplicate event id inside one file | never checked | both kept in the list (`:73`) | dict collapses them, `len(dict) < len(list)` |
| unknown / misspelled event key | never checked | dropped at `yaml_loader.py:21-27` | absent, no diagnostic |
| `trigger:` present but null | *key present* → no warning (`story_manager.py:133`) | passes `None` through (`:24`) | `AttributeError` at `event_manager.py:170` |
| `actions:` present but null | no warning (`story_manager.py:136`) | passes `None` through (`:25`) | `TypeError` at `event_manager.py:102` when the event fires |
| `options:` present but null | never checked at all | passes `None` through (`:26`) | `AttributeError` at `event_manager.py:52` |
| action `type:` unknown verb | never checked | verbatim (`:25`) | silently ignored branch in `_perform_actions` |
| condition `type:` unknown | never checked | verbatim (`:24`) | `met` stays `False` (`event_manager.py:184`+) |
| event missing `id` | **caught**: `Event N missing required 'id' field` (`story_manager.py:130-131`) | `KeyError: 'id'` | never reached |
| events file top level not a list | **caught**: `story_manager.py:112-113` | `TypeError` at `:22` | never reached |
| non-UTF-8 bytes | **caught only incidentally**, when `validate_story`'s own `open()` at `story_manager.py:109` raises — but it wraps only `yaml.YAMLError` (`story_manager.py:139`), so `UnicodeDecodeError` escapes to the outer `except Exception` at `story_manager.py:150-151` | `UnicodeDecodeError` at `yaml_loader.py:10` | never reached |
| old-format story directory | **not reachable**: `validate_story` hard-requires `<id>_story_arc.yaml` and returns early (`story_manager.py:80-83`) | loaded at `yaml_loader.py:96-142` | fully unvalidated |
| `initial_story_part` missing on disk | **warning only** (`story_manager.py:99-100`) | not checked | `game.py:268-269` substitutes `"The story begins..."` |
| `title` / `starting_location` missing from the arc | **errors** (`story_manager.py:91-94`) | defaults to `"Untitled Story"` / `"start"` (`yaml_loader.py:72, 82`) | loads anyway if you skip validation |
| `initial_player_stats` wrong type | never checked | verbatim into `Player.stats` (`yaml_loader.py:67`) | dict operations in `GameStateManager` may fail later |

`verified (run: probe load-03-errors.py, load-08-eventspath.py, load-09-nullkeys.py)` for all of the above unless a `read:` tag is given.

---

## Unknowns

- Whether the old-format branch was ever reachable in a *released* build. The published `dist/text_adventure_tui-0.1.1-py3-none-any.whl` ships a **different** content set (`story_arc.yaml`, `long/medium/short_story_arc.yaml`, `long/medium/short_story_events.yaml`) and **no `yaml_loader.py` at all** — the 0.1.1 artifact predates this loader. `verified (run: unzip -l dist/…whl)`. Whether some intermediate build wired `story_arc.yaml` (singular) to the old branch — needs git history across the 37 commits for `story_parts/` renames, which is outside this section's scope.
- Whether any author has ever hand-placed `initial_player_stats` inside a `story_start` event outside the unit test — needs the upstream repository's issue/PR history; this tree has exactly one instance (`test_new_engine.py:26-29`), which is also the only executed example of the old format.
- Whether the unsorted `Path.glob` at `yaml_loader.py:103` has ever produced a different order on another machine or filesystem (ext4 hash order vs. tmpfs insertion order) — needs a run on a filesystem with different `readdir` semantics, or a container image rebuilt from scratch.
- Whether the `UnicodeDecodeError` path is reachable in practice for real users. It needs `locale.getpreferredencoding(False)` to be non-UTF-8 — true under `LANG=C`/`LC_ALL=C` with UTF-8 mode disabled (proved), and on Windows with a legacy code page **unless** `locale.getpreferredencoding(False)` is called first (CPython's UTF-8 mode triggers on Windows via PEP 540, so it is likely safe there) — needs a real Windows run to confirm.
- Whether `story_manager`'s deliberate non-use of the loader's `events_path` was intended. The API accepts both paths (`story_manager.py:38-40`) and `story_tool.py:13-16` exposes both as flags, yet the loader derives one from the other (`yaml_loader.py:48`) — needs the author's intent, or an issue tracker.

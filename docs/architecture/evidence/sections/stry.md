# Text-Adventure-TUI: STRY — Story discovery, validation, templating + author CLI

Prefix: STRY · Commit: `7f349d1` · Depth: deep
Scope: `text_adventure_tui_lib/story_manager.py` (263, read fully), `story_tool.py` (168, read fully).
Read for context (not analysed; owned by other sections): `text_adventure_tui_lib/game.py` (250-314, 330-449), `text_adventure_tui_lib/yaml_loader.py` (1-142, LOAD), `text_adventure_tui_lib/event_manager.py` (1-95, 95-224, 222-281, EVT), `text_adventure_tui_lib/data_structures.py` (1-45, DATA), `text_adventure_tui_lib/game_state_manager.py` (1-56, DATA), `README.md` (140-239), `DEVELOPER_GUIDE.md` (30-159, 455-499), both shipped arc YAMLs, `events/*.yaml` (grep only).
Method: full read of both owned files; 7 probes under `/tmp/opencode/cdd-text-adventure-tui/probe/` (`stry-01`…`stry-07`), all run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` (stale 0.1.1 copy in site-packages shadows the repo); real CLI runs of `list`, `validate`, `validate <id>`, `info`, no-arg; `flake8` on both owned files; greps for cross-references. The two shipped stories are used as the fixture for every behavioural claim.
Limits: no Ollama server in this environment, so `game_loop` cannot be played end-to-end; the LLM call at `game.py:280` and the intent classifier are untested here. The turn-20 checkpoint trace re-executes a verbatim copy of `game.py:346-377` against real template data (that block contains no LLM call — `verified (read: game.py:346-377)`), because reaching turn 20 live would need 20 successful LLM turns. The note in `/tmp` (shell) was blocked by the sandbox; the cwd experiment was run via `subprocess(cwd=...)` inside probe `stry-01`, which sets the child's working directory exactly as a shell `cd` would.

---

## Purpose

`StoryManager` turns the `story_parts/` directory into the main menu (discovery), gives authors a shallow structural validator and a three-file story scaffold, and `story_tool.py` is the thin argparse CLI over those three operations — `verified (read: text_adventure_tui_lib/story_manager.py:1-264, story_tool.py:1-169)`.

---

## Public surface

| Symbol / flag | Kind | Location | Notes |
|---|---|---|---|
| `StoryInfo` | dataclass (10 fields) | `story_manager.py:13-24` | Menu metadata; built only by `discover_stories` |
| `ValidationResult` | dataclass (`is_valid`, `errors`, `warnings`) | `story_manager.py:27-32` | Plain lists of strings |
| `StoryManager.__init__(stories_path, events_path)` | constructor | `story_manager.py:38-40` | Stores two `Path`s; nothing else |
| `StoryManager.discover_stories() -> List[StoryInfo]` | public | `story_manager.py:42-72` | Non-recursive glob `*_story_arc.yaml` (`:47`); sorted by title (`:72`) |
| `StoryManager.validate_story(story_id) -> ValidationResult` | public | `story_manager.py:74-153` | Never raises for missing stories (returns `is_valid=False`) |
| `StoryManager.create_story_template(story_id, title, author="Unknown")` | public | `story_manager.py:155-256` | Writes 3 files; **no `mkdir`, no overwrite guard** |
| `StoryManager.get_story_info(story_id)` | public | `story_manager.py:258-264` | Re-runs `discover_stories()` then linear scan |
| `story_tool.py --stories-path` | CLI flag | `story_tool.py:13-15` | **Relative** default `text_adventure_tui_lib/story_parts` |
| `story_tool.py --events-path` | CLI flag | `story_tool.py:16-18` | **Relative** default `text_adventure_tui_lib/events` |
| `story_tool.py list` | CLI subcommand | `story_tool.py:23, 48-66` | `list_parser` variable unused (F841) |
| `story_tool.py validate [story_id]` | CLI subcommand | `story_tool.py:26-27, 68-114` | id optional; batch mode exits 1 on any error (`:114`) |
| `story_tool.py create <id> <title> [--author]` | CLI subcommand | `story_tool.py:30-33, 116-130` | try/except → exit 1 on write failure (`:128-130`) |
| `story_tool.py info <story_id>` | CLI subcommand | `story_tool.py:36-37, 132-165` | exit 1 only when story not found (`:134-136`) |

No `__all__`, no module-level singletons, no logging — `verified (read: story_manager.py:1-11, story_tool.py:1-10)`.

---

## Key data structures

### `StoryInfo`
Shape: `id, title, description, author, difficulty, tags, content_warnings, total_turns_estimate, version` — `verified (read: story_manager.py:13-24)`.
Created by `discover_stories` from the arc YAML with per-field `.get` defaults (`story_manager.py:55-65`); defaults differ from the loader's (`yaml_loader.py:82-91`) only in `description` (`"No description available."` vs `""`) — `verified (read: story_manager.py:58, yaml_loader.py:85)`.
Read by: `game.py:401-414` (menu rendering) and `story_tool.py:56-66, 138-150`. Lifetime: one list per `discover_stories()` call, discarded after render — `verified (read: game.py:397)`.

### `ValidationResult`
Shape: `is_valid: bool`, `errors: List[str]`, `warnings: List[str]` — `verified (read: story_manager.py:27-32)`.
Created only in `validate_story` (`story_manager.py:83, 153`). `is_valid` is `len(errors) == 0` (`:153`) — warnings never fail a story. Consumed by `story_tool.py:74-84, 96-107, 154-165`.

### The three files `create_story_template` writes
| File | Path arithmetic | Contents of note |
|---|---|---|
| `<id>_story_arc.yaml` | `stories_path / f"{story_id}_story_arc.yaml"` (`:189`) | `starting_location: "start"` (`:160`), `initial_story_part: f"{story_id}_intro.txt"` (`:161`), one checkpoint at turn 20 with `force_end_game` + `flag_messages` keyed on flag `success` (`:168-181`) |
| `<id>_intro.txt` | `stories_path / f"{story_id}_intro.txt"` (`:201`) | 5-line boilerplate (`:194-199`) |
| `<id>_story_events.yaml` | `events_path / f"{story_id}_story_events.yaml"` (`:248`) | `story_start` (MANUAL trigger, `change_location: "start"`, `override_narrative`, `modify_prompt`, `:206-225`) and `example_event` (AND of `location=="start"` + `player_action_keyword ["look around","examine"]`, sets `looked_around`, `:226-245`) |
Written with `yaml.dump(..., sort_keys=False)`; existing files are **silently overwritten** — `verified (read: story_manager.py:190-191, 201-203, 249-250)` (no `exists()` guard anywhere in `:155-256`).

---

## Invariants

| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| story id == arc filename stem minus `_story_arc` | `story_manager.py:53` (derived, not checked) | `yaml_loader.py:38, 76` re-derives it independently; save files embed it (`game.py:221`) |
| A story exists ⟺ `<id>_story_arc.yaml` sits at the TOP level of `stories_path` | `story_manager.py:47` (glob, non-recursive) | Nothing; the old-format directory is invisible to both menu and validator — `verified (run: probe stry-02)` |
| `validate_story` checks events at `events_path`, the loader reads `stories_path.parent/"events"` | `story_manager.py:103` vs `yaml_loader.py:48` | Nobody reconciles them; validation can bless files the game never reads — `verified (run: probe stry-05)` |
| `story_start` event exists in the story events file | `story_manager.py:116-122` (error) | `yaml_loader.py` new branch never checks; `game.py:272` force-executes the id and silently no-ops if absent |
| `is_valid` means "structure parses and required keys exist", **not** "playable" | `story_manager.py:74-153` | `story_tool.py` exit codes and the docs (`README.md:210-216`) both imply more than is checked |
| Discovery order is deterministic | `story_manager.py:72` (`sorted by title`) | Menu numbering (`game.py:401`) inherits it |

---

## Dependencies out

| Target | Called at | Why |
|---|---|---|
| `yaml.safe_load` | `story_manager.py:50, 88, 110` | Parse arc + events |
| `yaml.dump` | `story_manager.py:191, 250` | Write arc + events template |
| builtin `open()` (no `encoding=`) | `story_manager.py:49, 87, 109, 190, 202, 249` | Same encoding hazard as the loader (LOAD section proved it bites under `LANG=C`) |
| `Path.glob`, `Path.exists` | `story_manager.py:47, 81, 99, 104` | Discovery + file probing |
| `load_story_and_player` (from `.yaml_loader`) | `story_manager.py:144` | The only "does it actually load" check; wrapped in `except Exception` (`:145-146`) |
| bare `print()` | `story_manager.py:69, 252-256` | Warnings + creation report; **`rich` is never imported in `story_manager.py` or `story_tool.py`** — `verified (run: grep rich → 0 hits)` |
| `argparse`, `sys` | `story_tool.py:5-6` | CLI |

Notably NOT imported: `rich`, `event_manager`, `data_structures.Story` (imported at `story_manager.py:9` but **never used** — flake8 F401, `verified (run: flake8 → story_manager.py:9:1 F401 '.data_structures.Story' imported but unused)`).

---

## Dependencies in

| Caller | Location | What it expects |
|---|---|---|
| `main_menu` | `game.py:19` (import), `game.py:389-391` (construct ONCE, outside the `while True` at `game.py:393`) | `discover_stories()` every menu iteration (`game.py:397`); story ids from `StoryInfo.id` feed `game_loop(selected_story.id)` (`game.py:435`) |
| `game_loop` (indirect) | via `load_story_and_player` (`game.py:254`) | The arc/events files this module scaffolds must satisfy the loader's contract (LOAD section) |
| nothing else | `verified (run: grep -rn 'story_manager\|StoryManager\|story_tool' --include='*.py' … → only game.py:19,391,397)` | — |
| tests | **none** — `verified (run: grep over tests/ → 0 hits for story_manager/story_tool)` | The author CLI and validator have zero test coverage |

`main_menu` uses **`Path(__file__).parent`** for both paths (`game.py:389-390`), so the shipped game is immune to the cwd problem that breaks `story_tool.py` (see Surprises S7) — `verified (read: game.py:389-391)`.

---

## Side effects

| Effect | Location | Trigger condition | Reversible? |
|---|---|---|---|
| Opens + parses every top-level arc YAML | `story_manager.py:47-50` | every `discover_stories()` call — i.e. **every main-menu iteration** (`game.py:397`) and every `list`/`validate`/`info` invocation | N/A (read-only) |
| Opens arc + story events (+ loader re-opens both + general events) | `story_manager.py:87, 109, 144` | every `validate_story()` — measured **5 opens** for one call | N/A |
| Writes `<id>_story_arc.yaml`, `<id>_intro.txt`, `<id>_story_events.yaml` | `story_manager.py:190-191, 201-203, 249-250` | `create_story_template` / CLI `create` | Only by hand; **overwrites existing files without warning** |
| Bare `print()` to stdout | `story_manager.py:69` | malformed arc YAML during discovery | N/A |
| Process exit via `sys.exit(1)` | `story_tool.py:114, 130, 136` | batch-validate failure, create failure, info-not-found | N/A |

---

## Error and edge behaviour

| Situation | What happens | Location | Evidence |
|---|---|---|---|
| Malformed arc YAML during discovery | bare `print("Warning: Could not load story arc …")`, story skipped, rest continue | `story_manager.py:68-70` | `verified (run: probe stry-07c — bad arc printed warning, good story still listed)` |
| `stories_path` does not exist | `Path.glob` over missing dir → silently empty list → "No stories found." → **exit 0** | `story_manager.py:47`, `story_tool.py:50-52` | `verified (run: probe stry-01 — from /tmp/opencode: stdout 'No stories found.\n', exit 0; probe stry-07d)` |
| Missing `<id>_story_events.yaml` | warning only ("Story events file not found"), then the loader call at `:144` may still succeed (loader also tolerates missing story events) → **can be `is_valid=True`** | `story_manager.py:103-105` | `verified (read: yaml_loader.py:59-63)` |
| `trigger:`/`actions:` keys present but YAML-null | key-presence checks (`"trigger" not in event`) pass → no warning → `None` reaches `EventManager` and crashes later | `story_manager.py:133-137` | `verified (read: story_manager.py:133-137; corroborated by LOAD probe load-09)` |
| `create` into nonexistent directory | `FileNotFoundError` from `open(...,'w')`; CLI catches it (`story_tool.py:128-130`) → prints ❌ → exit 1 | `story_manager.py:190` | `verified (run: probe stry-07b)` |
| `validate <bad-id>` or `validate <invalid-story>` | prints ❌ + errors, **returns normally, exit 0** | `story_tool.py:69-84` (no `sys.exit` in the branch) | `verified (run: probe stry-04b a,b — both exit 0)` |
| `validate` (all stories), ≥1 invalid | prints per-story results, "⚠️  Some stories have validation errors.", `sys.exit(1)` | `story_tool.py:110-114` | `verified (run: probe stry-04b c — exit 1)` |
| `info <missing>` | "❌ Story … not found." → exit 1 | `story_tool.py:134-136` | `verified (run: EXIT_INFO_MISSING=1)` |
| `info <existing-but-invalid>` | prints "❌ Story validation: FAILED" + errors → **exit 0** | `story_tool.py:154-165` (no `sys.exit`) | `verified (run: probe stry-04b d — exit 0)` |
| No subcommand | `parser.print_help()` → return → **exit 0** | `story_tool.py:41-43` | `verified (run: EXIT_NOARG=0)` |
| Global flags placed AFTER the subcommand (e.g. `validate my_story --stories-path X`) | argparse rejects them (subparsers don't inherit) → `error: unrecognized arguments` → **exit 2** | `story_tool.py:20-27` | `verified (run: probe stry-04 first case — exit 2)` |
| Unknown flag / missing flag value | argparse error → exit 2 (standard) | `story_tool.py:12-18` | `inferred (because argparse's default behaviour; not separately exercised)` |
| Ctrl-C | uncaught `KeyboardInterrupt` traceback (no handler anywhere in `story_tool.py`) | whole file | `verified (read: story_tool.py:1-169)` |

### Cross-check on the `initial_story_part` fallback (assigned question)

`validate_story` line 97 falls back to `"01_intro.txt"` when the arc omits `initial_story_part`, then checks `stories_path / initial_story_part` (`story_manager.py:97-100`). Findings:

- **Neither shipped arc omits it**: `whispers_of_the_salted_crypt_story_arc.yaml:3` → `01_intro.txt`; `the_clockwork_heist_story_arc.yaml:3` → `clockwork_intro.txt` — `verified (read: both arcs)`. The fallback branch is dormant for shipped content; `validate` for both stories produced **zero warnings** (`verified (run: python story_tool.py validate <id> → '✅ Story is valid!' twice)`.
- The suspected "checks the wrong file" bug **does not exist**: the fallback string `"01_intro.txt"` is exactly the loader's default (`yaml_loader.py:83`) and `game.py:264` reads `stories_path / story.initial_story_part`, so `stories_path / "01_intro.txt"` (`story_manager.py:98`) is the same file the game would read — `verified (read: story_manager.py:97-98, yaml_loader.py:83, game.py:264)`.

---

## Real CLI output (assigned question 2)

`python story_tool.py list` from the repo root — `verified (run)`:

```
Available Stories:
==================================================
📖 The Clockwork Heist
   ID: the_clockwork_heist
   Author: Text Adventure TUI Team
   Difficulty: medium
   Tags: heist, stealth, urban, crime, fantasy
   Estimated turns: 15
   Content warnings: theft, mild violence
   Description: You're a master thief planning the heist of a lifetime. ...

📖 Whispers of the Salted Crypt
   ID: whispers_of_the_salted_crypt
   Author: Text Adventure TUI Team
   Difficulty: beginner
   Tags: mystery, adventure, coastal, rescue, mentor
   Estimated turns: 25
   Content warnings: mild peril, mysterious disappearance
   Description: Your mentor Master Elian has vanished without a trace. ...
```

`python story_tool.py validate` — `verified (run)`:

```
Validating all stories...
==================================================
✅ The Clockwork Heist (the_clockwork_heist)
✅ Whispers of the Salted Crypt (whispers_of_the_salted_crypt)

🎉 All stories are valid!
```

Per-id: `validate the_clockwork_heist` → `✅ Story is valid!`; `validate whispers_of_the_salted_crypt` → `✅ Story is valid!`. **Zero warnings, zero errors, exit 0 for everything shipped** — `verified (run)`.

The old-format id is refused by validation: `validate_story("Whispers_of_the_Salted_Crypt")` → `is_valid: False`, `errors: ['Story arc file not found: …story_parts/Whispers_of_the_Salted_Crypt_story_arc.yaml']` — `verified (run: probe stry-02d)`.

---

## What `validate_story` does NOT check (assigned question 3 — precise gap list)

`validate_story` performs exactly these checks — `verified (read: story_manager.py:74-153)`: arc file exists; arc parses as YAML; `title` + `starting_location` keys present; `initial_story_part` file exists (with fallback, see above); `<id>_story_events.yaml` exists at `events_path`; that file's top level is a list; some event has `id == "story_start"`; every event is a dict; every event has an `id` key; `trigger`/`actions` **keys** present. Plus the loader smoke-test at `:144`.

Not checked (each row: what an author can break, where it detonates, why validation stays green):

| # | Gap | Where it detonates | Evidence |
|---|---|---|---|
| 1 | **`general_events.yaml` is never opened** (validation hardcodes `<id>_story_events.yaml` at `:103`) | `yaml_loader.py:54` — a typo there crashes **every** story at load; `validate` stays green | `verified (read: story_manager.py:103; corroborated by LOAD probe load-03 case d)` |
| 2 | **Trigger condition types** — unknown `type:` never rejected | `event_manager.py:184-250`: unmatched type leaves `met=False` → event silently never fires | `verified (read: event_manager.py:180-252)` |
| 3 | **Action types** — unknown verb never rejected | `event_manager.py:106-154`: `if/elif` chain with **no `else`** → action silently ignored | `verified (read: event_manager.py:106-154)` |
| 4 | **`operator` values** on `turn_count_*`/`stat_check` — only `== >= <= > <` implemented; anything else → condition never true | `event_manager.py:209-221, 223-235, 238-250` | `verified (read)` |
| 5 | **Referenced locations** — `starting_location`, `change_location` values, `location` condition values are free strings with no registry or cross-check | mismatch = event never fires / player stranded; e.g. template writes `location: start` matching its own `starting_location: "start"` only by author discipline | `verified (read: story_manager.py:160, 233; event_manager.py:185-186)` |
| 6 | **Flag names** — no cross-check between `set_flag` actions and `flag_set`/`flag_not_set` conditions, nor with checkpoint `flag_messages[].flag` | the template's own `success` bug (Surprise S4); shipped arcs at least reference flags their events set | `verified (read: story_manager.py:168-181, 238)` |
| 7 | **Event ids referenced by `present_choices`/`add_choice` `action:` fields** — dangling ids unchecked | `event_manager.py:139-147` builds the choice; click-time `execute_event_actions` (the **live second definition**, `event_manager.py:260-281`) returns an empty-shaped dict **silently** — dead button, no message | `verified (read: event_manager.py:139-147, 267-275)` |
| 8 | **`add_item` key vocabulary** — engine reads `item_id` (`event_manager.py:111`) while shipped YAML writes `value:` (whispers `:41-42`, `:95-96`; clockwork `:186-187`) | `add_item(None)` → inventory gets literal `None`; later `inventory_has "elians_journal"` conditions never fire → story may soft-lock; **validation passes both shipped stories** | `verified (read: event_manager.py:110-111; grep of events/*.yaml)` |
| 9 | **Duplicate event ids** (within or across files) | `event_manager.py:8` dict-comprehension silently last-wins | `verified (read: event_manager.py:8; LOAD probe load-02)` |
| 10 | **Null-valued keys** — `trigger:` with no value passes the key-presence check | `AttributeError` at `event_manager.py:170` at trigger-evaluation time | `verified (read: story_manager.py:133-137; LOAD probe load-09)` |
| 11 | **Checkpoint structure** — `turn` int-ness, `flag_messages[].flag` correctness | wrong turn = checkpoint never fires; wrong flag = wrong ending message (S4) | `verified (read: story_manager.py:74-153 — no checkpoint code at all)` |
| 12 | **`options` semantics** — `priority` (documented at `DEVELOPER_GUIDE.md:74`) is ignored by the engine entirely; `once` values unchecked | author writes `priority: 1` expecting ordering, gets file order | `verified (read: event_manager.py:50-81 — only `once` is read)` |
| 13 | **`initial_player_stats` / `initial_inventory` types** | verbatim into `Player` (`yaml_loader.py:66-69`); wrong shape breaks stat ops later | `verified (read)` |
| 14 | **Old-format story directories** | unreachable from menu (below) AND rejected by validation — never validated by anyone | `verified (run: probe stry-02d)` |

So the answer to "does validation predict playability": **no.** A story can be `is_valid=True` and still: crash at load (gap 1/10), load but lose its `story_start` (events-path divergence, below), soft-lock on inventory (gap 8), or end every run with the failure message (gap 6). Both shipped stories validate clean today (`verified (run)`), and shipped story #1 (clockwork) carries gap 8 and shipped #2 (whispers) carries gap 8 twice.

---

## Reachability of the old format (assigned question 1)

`discover_stories` globs `self.stories_path.glob("*_story_arc.yaml")` (`story_manager.py:47`) — single `*`, which cannot match `/`, so it is **top-level only**. `verified (run: probe stry-02)`:

```
(a) stories_path.glob('*_story_arc.yaml') →
      story_parts/the_clockwork_heist_story_arc.yaml
      story_parts/whispers_of_the_salted_crypt_story_arc.yaml
(b) story_parts/Whispers_of_the_Salted_Crypt/ contains:
      chapter1_study.yaml  chapter2_coast.yaml  chapter3_crypt.yaml  game_setup.yaml
    glob('*_story_arc.yaml') inside that dir → []
(c) discover_stories ids → ['the_clockwork_heist', 'whispers_of_the_salted_crypt']
    'Whispers_of_the_Salted_Crypt' in ids → False
(d) _load_story_old_format('Whispers_of_the_Salted_Crypt', …) → loads fine:
    story.id='story_start', title='The Missing Mentor', 8 events
```

The only UI path into the loader is `game_loop(selected_story.id)` where `selected_story ∈ discover_stories()` (`game.py:397, 428-435`) — so `text_adventure_tui_lib/story_parts/Whispers_of_the_Salted_Crypt/` (4 YAML files) **can never be selected**, and the old-format loader branch (`yaml_loader.py:96-142`, reached only when no arc file exists, `yaml_loader.py:41-45`) is **unreachable from the shipped UI**. The directory is dead shipped content (LOAD section reached the same conclusion independently; the resume path `game.py:451` cannot rescue it either because old-format saves embed `id="story_start"`, which resolves to neither branch's content — LOAD's probe `load-07`).

---

## The `--events-path` divergence (assigned questions 4 + 5 context)

`validate_story` checks `<events_path>/<id>_story_events.yaml` (`story_manager.py:103`), then calls `load_story_and_player(story_id, self.stories_path)` (`story_manager.py:144`) — and the loader **always** derives its events directory as `stories_path.parent / "events"` (`yaml_loader.py:48`), ignoring `StoryManager.events_path` entirely.

Reproduced end-to-end (`verified (run: probe stry-05-eventspath-validate.py)`):

```
layout: pkg/story_parts (arc+intro), pkg/events (ONLY general_events.yaml),
        elsewhere/demo_story_story_events.yaml (with story_start)
validate_story('demo_story') → is_valid: True, 0 errors, 0 warnings
load_story_and_player(...)   → event ids loaded: [6 general ids]; story_start ABSENT
game.py:272 shape call       → returns silent empty-shaped dict (no narrative override)
```

Consequence: **anyone passing `--events-path` gets a validator that checks a file the game will never read.** A story can validate clean and then start without its `story_start` event (the intro `.txt` is used verbatim and every authoring hook in the story file is dead). This also means `StoryManager.events_path` is real for validation but fiction for loading — the two paths only agree when `events_path == stories_path.parent/"events"`, which is exactly the shipped default and the only configuration anybody tests.

---

## Template story: does it validate and start? (assigned question 5)

`verified (run: probe stry-03-template-e2e.py)` — package dirs copied to `/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-template`, `StoryManager` pointed at the copy (repo untouched):

| Step | Result |
|---|---|
| `create_story_template('probe_story', 'Probe Story', 'Tester')` | writes all 3 files |
| `validate_story('probe_story')` | **`is_valid: True`, 0 errors, 0 warnings** |
| `discover_stories()` | sees it, sorted first by title |
| `load_story_and_player` | `starting_location='start'`, `initial_story_part='probe_story_intro.txt'`, 8 events (6 general + 2 template) |
| engine spin-up (`game.py:255-261` shape) | location `start`, turn 0 |
| `execute_event_actions('story_start')` (`game.py:272` shape) | override narrative applied; location unchanged (`change_location: "start"` is a **no-op** — it was already `start`) |
| pre-choice sweep with empty input (`game.py:285` shape) | `example_event` does **not** fire — `player_action_keyword` requires non-empty input (`event_manager.py:193`) |
| player text `"I look around the desk"` | **fires**: substring match (`"look around" in "i look around the desk"`, `event_manager.py:191-197`), flag `looked_around` set, post-narrative injected |
| repeat same input | does not re-fire (`once: True` honoured, `event_manager.py:77-78`) |

Verdict: **yes — a template story validates, loads, starts, and its example event works**, modulo the LLM (unavailable here). The template's trigger vocabulary (`MANUAL`, `AND`, `location`, `player_action_keyword`, `game_start`) and action vocabulary (`change_location`, `override_narrative`, `modify_prompt`, `set_flag`, `inject_narrative` + `position`) all match what `event_manager.py` implements — `verified (read: story_manager.py:206-245; event_manager.py:106-154, 163-258)`.

Two caveats found on the way:
- `story_start`'s `mode: MANUAL` means its `conditions: [{type: game_start}]` are **never evaluated** — `_evaluate_trigger` returns `False` for MANUAL before reading conditions (`event_manager.py:173-174`), and `game.py:272` force-executes the id instead. The `game_start` condition on the template's `story_start` is decorative — `verified (read: event_manager.py:173-174; run: probe stry-03)`.
- `story_start` is never recorded in `triggered_event_ids` by that path (the live `execute_event_actions` marks only `once` events, `event_manager.py:277-279`; template `story_start` has no `options`), so re-execution would be possible — harmless today, but it means the once-machinery is bypassed for the one event every story depends on — `verified (run: probe stry-03 step 7: 'story_start recorded as triggered? False')`.

## The turn-20 checkpoint (assigned question 6)

Template checkpoint: `{turn: 20, force_end_game: True, prompt_injection: "The story reaches its natural conclusion.", flag_messages: [{flag: "success", …}]}` (`story_manager.py:168-181`). The only flag any template event can set is `looked_around` (`story_manager.py:238`); `general_events.yaml` contains **no `set_flag` at all** (`verified (run: grep set_flag general_events.yaml → 0 hits)`), and nothing else in the engine sets `success` except `end_game` actions with `success: true` — which set `game_ended_success`, not `success` (`event_manager.py:148-154`), and the template defines no `end_game` action anyway. So flag `success` is **unsettable** in a template story.

Trace of `game.py:346-377` at the end of the 20th turn (`turn_count` starts at 0, `data_structures.py:43`; incremented per turn at `game.py:347`; checkpoint fires when `get_turn_count()==20`, i.e. after 20 completed turns, before any 21st LLM call) — re-executed verbatim against real template data, `verified (run: probe stry-07a)`:

1. `prompt_injection` is appended to `llm_instructions` (`game.py:354-355`) — then discarded, because…
2. `force_end_game` branch (`game.py:356`): `flag "success"` not in flags → `message_if_not_set` wins (`game.py:366-369`).
3. Player sees, in order (`game.py:371-376`):
   - **"Your adventure ends, but perhaps not as you hoped."**
   - `📖 STORY CONCLUDED 📖` banner
   - "Thank you for playing!"
   - "Press Enter to return to the main menu..."
4. `return` to `main_menu` (`game.py:377`). The success message ("You have succeeded in your quest!") is **unreachable**; the checkpoint's `prompt_injection` is a dead write (the LLM is never called again that session).

---

## Lifecycle and concurrency

- **`StoryManager` is stateless** apart from the two `Path` attributes (`story_manager.py:38-40`). No caches, no counters, no module globals — `verified (read: story_manager.py:35-264)`.
- **Safe to construct once and reuse across the whole `main_menu` loop** — the shipped app does exactly that (`game.py:391` before the `while True` at `game.py:393`; `discover_stories()` called once per iteration at `game.py:397`). Each call returns fresh objects; nothing accumulates — `verified (read: game.py:389-397)`.
- **Thread-safe**: all methods only read the filesystem and build fresh locals; two threads sharing one manager cannot corrupt each other (worst case: duplicated I/O). No locking exists or is needed — `inferred (because every method touches only `self.stories_path`/`self.events_path`, both immutable after `__init__`)`.
- **Cost model** (`verified (run: probe stry-06-infocost.py)`): one `discover_stories()` = **N arc open+parse** (N=2 stories → 2 opens, confirmed). One `get_story_info()` = N opens (re-discovers everything, `story_manager.py:260`). One `validate_story()` = **5 opens** (arc ×2 — its own at `:87` plus the loader's at `yaml_loader.py:42` — story events ×2, general events ×1; 3 unique files). Full `python story_tool.py info <id>` ≈ **N + 5** opens. Scales O(N) per menu redraw for the game (every menu iteration re-parses all arcs, `game.py:397`), which is negligible at N=2 (~10 KB YAML) but is the first thing to cache if the library grows — `inferred (because parse time is sub-millisecond at this content size)`.
- Teardown: none needed; every file handle is scoped in `with` blocks — `verified (read: story_manager.py:49, 87, 109, 190, 202, 249)`.

---

## Configuration

| Knob | Default | Source | Runtime or restart |
|---|---|---|---|
| `--stories-path` | `Path("text_adventure_tui_lib/story_parts")` — **relative** | `story_tool.py:13-15` | per invocation |
| `--events-path` | `Path("text_adventure_tui_lib/events")` — **relative** | `story_tool.py:16-18` | per invocation (and largely ignored — see divergence) |
| effective game paths | `Path(__file__).parent / "story_parts"` and `/events` | `game.py:389-390` | fixed at import |
| loader events dir | hardcoded `stories_path.parent / "events"` | `yaml_loader.py:48` | not configurable |
| template defaults | difficulty `medium`, 20 turns, health 100, `author="Unknown"` | `story_manager.py:162-166, 183-186` | baked into written files |
| YAML output style | `default_flow_style=False, sort_keys=False` | `story_manager.py:191, 250` | — |

**Relative-default consequence** (`verified (run: probe stry-01-relative-cwd.py)`): from the repo root, `list` shows both stories; from `/tmp/opencode` (child process cwd), `python story_tool.py list` prints `No stories found.` and **exits 0**; `validate` prints `No stories found to validate.` and exits 0. No error, no hint that the paths didn't resolve. Contrast `game.py:389-390`, which anchors on `Path(__file__).parent` and is therefore cwd-independent. The tool is only usable from the repo root (or with absolute flags placed **before** the subcommand).

---

## Extension points

- **New story field** (e.g. `mood`): the STRY-side edit is `story_manager.py:55-65` (add `story_data.get("mood", …)` to `StoryInfo` + a field at `:13-24`); the other three edits are `data_structures.py`, `yaml_loader.py`, and the docs (LOAD section documents the full four-step). `StoryInfo` and `Story` are kept in sync by hand — nothing enforces it — `verified (read: story_manager.py:13-24, 55-65)`.
- **New validation rule**: `README.md:222` officially names `story_manager.py` as the place ("Add validation rules in `story_manager.py`"). The natural insertion points are the per-event loop (`story_manager.py:125-137`) for vocabulary checks and a new block before `:144` for cross-reference checks — `verified (read)`.
- **New CLI subcommand**: add a `subparsers.add_parser(...)` in `story_tool.py:20-37` and an `elif args.command == …` dispatch block after `:116`. Remember `args.command` can be `None` (`:41-43`) and that global flags only parse before the subcommand — `verified (read + run)`.
- **New story**: the supported flow is `create` → edit the 3 files → `validate` (`DEVELOPER_GUIDE.md:137-149`); `create` is verified to produce a menu-visible, loadable, playable scaffold (probe stry-03).

---

## Tests

| Test file | What it asserts about STRY | Coverage notes |
|---|---|---|
| `tests/test_game_engine.py`, `tests/test_new_engine.py`, `tests/test_game_basics.py` | **nothing** — no test imports `story_manager` or `story_tool` | `verified (run: grep -rn 'story_manager\|StoryManager\|story_tool' tests/ → 0 hits)` |

Zero coverage for: discovery (glob + sort + malformed-arc skip), the entire validator, the template writer, and the whole CLI. The validator's only indirect exercise is via the loader smoke-test it performs on shipped stories — by a human running it, not by CI.

---

## Surprises

- **S1 — The old-format story directory is triple-dead**: invisible to the menu (non-recursive glob, `story_manager.py:47`), rejected by the validator (`story_manager.py:80-83`), yet perfectly loadable if the id were ever passed by hand (8 events, `verified (run: probe stry-02d)`). It still ships in the package (LOAD section, `MANIFEST.in`). A newcomer will waste time editing files that no code path can reach.
- **S2 — Validation and loading read different directories.** `validate_story` checks `events_path` (`story_manager.py:103`) but the loader it calls ignores it (`yaml_loader.py:48`). `--events-path` produces green checkmarks for files the game will never open — `verified (run: probe stry-05)`.
- **S3 — "Comprehensive validation … Cross-reference checking" (`README.md:210-216`) does not exist.** The validator checks ~9 structural facts (see the gap table); it knows nothing about trigger/action vocabularies, operators, locations, flags, referenced event ids, checkpoints, or `general_events.yaml`. Both shipped stories validate `✅` while clockwork carries a guaranteed `add_item(None)` (engine reads `item_id`, YAML writes `value:`, `event_manager.py:111`).
- **S4 — The template ships an unwinnable ending.** Its checkpoint messages key on flag `success`, which no template event (and nothing else) can set; every template story ends at turn 20 with "Your adventure ends, but perhaps not as you hoped." — and the same checkpoint's `prompt_injection` is a dead write (the `return` at `game.py:377` discards it before the next LLM call) — `verified (run: probe stry-07a)`.
- **S5 — `execute_event_actions` is defined twice in `event_manager.py`** (`:18-36` and `:260-281`); the second definition silently wins (also flake8 F811, per ledger). The live version has **no DEBUG prints** and returns a silent empty-shaped dict for missing ids. This contradicts any claim that a dangling `story_start`/choice id produces a visible "DEBUG: Event … not found" message — that message is dead code in the shadowed first definition — `verified (run: probe stry-05 returned the 5-key dict, not `{}`; read: event_manager.py:18-36 vs 260-281)`. (EVT owns the fix; STRY records it because the validator's silence about dangling ids is what makes it reachable.)
- **S6 — Exit codes are useless for CI.** `validate <id>` exits 0 even for an invalid or nonexistent story (`story_tool.py:69-84`); `info` exits 0 with "❌ Story validation: FAILED" (`:154-165`) and exits 1 only for not-found (`:134-136`); only batch `validate` exits 1 (`:114`). A CI step running `validate` per story can never go red — `verified (run: probe stry-04b)`.
- **S7 — The author CLI is cwd-fragile and fails silently**: relative default paths (`story_tool.py:13-18`) make it report "No stories found." / "No stories found to validate." from any other directory, exit 0 — `verified (run: probe stry-01)`.
- **S8 — Global flags must precede the subcommand**; `validate my_story --stories-path X` is an argparse exit-2 error — `verified (run: probe stry-04)`.
- **S9 — `create` silently overwrites** existing arc/intro/events files of the same id (no exists-check, `story_manager.py:189-250`) — `verified (read)`.
- **S10 — `list_parser` is dead** (flake8 F841, `story_tool.py:23`), and `story_manager.py` imports `Story`, `Dict`, `Any`, `Tuple` it never uses (F401 ×4) — `verified (run: flake8)`.
- **S11 — Error output style is inconsistent with the app**: the game renders everything through `rich` (`game.py:385, 400-433`), but `story_manager.py` prints its discovery warning with bare `print()` (`:69`) and never imports `rich` (`verified (run: grep rich → 0 hits in story_manager.py, story_tool.py)`); in the TUI, that warning would bypass rich's console entirely.
- **S12 — `get_story_info` is O(N) re-parses for an O(1) question** (`story_manager.py:258-264` calls `discover_stories()`), and the CLI then adds 5 more opens by validating in the same command — `verified (run: probe stry-06)`.
- **S13 — The suspected "wrong file" fallback bug does not exist**: neither shipped arc omits `initial_story_part` (whispers `:3`, clockwork `:3`), and if one did, `stories_path / "01_intro.txt"` is exactly what the loader+game would use (`yaml_loader.py:83`, `game.py:264`) — `verified (read)`.

## Docs vs code

| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| "comprehensive validation: Required field checking; File existence verification; YAML syntax validation; Event structure validation; **Cross-reference checking**" | `README.md:210-216` | first four are real (shallowly); cross-reference checking exists nowhere in `story_manager.py:74-153` | **False for the last item** |
| Manual story creation "The story will automatically appear in the main menu" | `README.md:168-173` | true iff the arc file is top-level `*_story_arc.yaml`; a nested or misnamed file is silently invisible (`story_manager.py:47`) | **True but fragile** (no error on wrong placement) |
| `StoryManager` creation snippet | `README.md:150-166` | works verbatim — probe stry-03 is that snippet | **Accurate** |
| "Discovers available stories automatically / Validates story structure and content / Creates story templates" | `DEVELOPER_GUIDE.md:38-43` | accurate as far as it goes; "content" validation is ~9 structural checks | **Accurate, overstates depth** |
| Workflow: `create` → edit → `validate` | `DEVELOPER_GUIDE.md:137-149` | verified end-to-end (probe stry-03); note flags-before-subcommand and repo-root-only caveats | **Accurate with unlisted caveats** |
| Validation Tools commands | `DEVELOPER_GUIDE.md:463-473` | all three commands run as documented (`verified (run)`) | **Accurate** |
| "Test in debug mode … verify save/load" | `DEVELOPER_GUIDE.md:475-492` | validation cannot substitute for play-testing — see gap table | **Accurate advice, understated necessity** |

---

## Applied layer checklists

### CLI (ENTRY checklist applied to `story_tool.py`)

- First line that runs: `main()` under `if __name__ == "__main__"` (`story_tool.py:168-169`); no side effects at import — `verified (read)`.
- Argument parser: 2 global `Path` flags with **relative** defaults (`:13-18`); 4 subcommands (`list`, `validate [id]`, `create id title [--author]`, `info id`) (`:20-37`); **subparsers created without `required=True`** (`:20`), so no command → `args.command is None` → help + exit 0 (`:41-43`, `verified (run: EXIT_NOARG=0)`); unknown args after a subcommand → argparse exit 2 (verified run); unknown flag before → exit 2 (`inferred (argparse default)`).
- Order of operations: parse args → construct `StoryManager` (`:46`) → single dispatch (`:48-165`). No config files, no env vars, no logging — `verified (read: story_tool.py:1-169)`.
- Loop/shutdown: none (single pass); exits via falling off `main()` (0), `sys.exit(1)` ×3 (`:114, 130, 136`), argparse (2). Ctrl-C = raw traceback.
- The unused `list_parser` assignment (`:23`) is the classic "flag parsed but never read" cousin: harmless, but flake8 flags it (F841) and CI is already red on lint per the ledger.

### Content / config-as-behaviour (CONF checklist applied)

- The YAML this section **writes** is behaviour: `create_story_template` emits an arc + events file that the engine executes as a program (locations, flags, triggers, prompts). Nothing enforces consistency between what it writes — `starting_location: "start"` (`:160`) vs `change_location: "start"` (`:215`) is a no-op by luck; `flag: success` (`:175`) vs the actions actually written (`:238`) is broken by design. `verified (read: story_manager.py:158-246; run: probe stry-03/07)`.
- Schema ownership is split: the loader owns parsing (LOAD), `event_manager` owns vocabulary (EVT), and the validator owns **none of it** — it re-implements 9 shallow checks instead of delegating to the other two, which is why the gap table exists — `verified (read: story_manager.py:74-153)`.
- Precedence/defaults: template defaults are baked into written files (difficulty/turns/health), so editing defaults in code affects only future stories — `verified (read: story_manager.py:162-186)`.
- `general_events.yaml` is shared behaviour across all stories, edited by hand, and is outside both the validator's and the template writer's field of view — the highest-leverage file with the least tooling — `verified (read: story_manager.py:103, 155-256)`.

---

## Unknowns

- Whether `story_tool.py` was ever intended to run from outside the repo root (a `Path(__file__).parent` default like `game.py:389` would fix S7) — needs the author's intent or issue history.
- Whether the duplicate `execute_event_actions` (S5) is a botched merge or a deliberate replacement — needs `git log -p text_adventure_tui_lib/event_manager.py` (EVT owns; STRY only records the observable consequence).
- Whether `validate <id>`'s always-zero exit was ever relied upon (some wrappers treat any exit 0 as pass) — needs CI/hook history; today's `.github/workflows` content is TOOL territory and out of this section's scope.
- Whether `--events-path` has ever been used successfully in any workflow — its only consistent value equals the derived default — needs usage history.
- Whether the template's unreachable `success` ending was meant to pair with an `end_game` action that was never added to the template — needs author intent.
- Whether `get_story_info`'s O(N) re-discovery matters at any realistic library size — needs the intended number of stories (content roadmap).

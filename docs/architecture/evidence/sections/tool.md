# Text-Adventure-TUI: TOOL — Tests, CI, packaging, doc promises

Prefix: TOOL · Commit: 7f349d1 (2025-07-22) · Depth: deep
Scope (read fully): `tests/test_game_engine.py` (85), `tests/test_new_engine.py` (92),
`tests/test_game_basics.py` (3), `setup.py` (52), `MANIFEST.in` (6), `requirements.txt` (3),
`requirements-dev.txt` (9), `.github/workflows/python-ci.yml` (43).
Read for reconciliation: `README.md` (275), `README_OLD.md` (387, headers + targeted sections),
`DEVELOPER_GUIDE.md` (587), `docs/architecture.md` (105), `docs/customization.md` (120),
`AGENTS.md` (26).
Method: read + 8 command runs (`pytest`, both flake8 CI gates, `twine check`, `unzip -l/-p`
on the built wheel, `story_tool.py list`/`validate`, an import test, and a Python 3.8.20
import probe) + `git log -p` on the workflow. Limits: no Ollama server and no PyPI
credentials in this environment; nothing here proves what a *published* release contains
beyond the local `dist/` artifacts.

---

## Purpose

Guard the engine with a 7-test suite, a two-gate flake8 CI, and a setuptools package —
and document how to extend the game. As shipped, the CI cannot run (wrong trigger
branch), its 3.8 leg cannot even import the code, the lint gate fails with 153
violations, and most of the documentation describes an earlier architecture.

## Public surface

| Surface | Kind | Location | Notes |
|---|---|---|---|
| `pytest` | CI gate | `.github/workflows/python-ci.yml:40-42` | passes: 7 passed in 0.02s (verified run) |
| flake8 gate 1 `--select=E9,F63,F7,F82` | CI gate | `python-ci.yml:34` | **passes** (verified run: `0`, exit 0) |
| flake8 gate 2 `--max-complexity=10 --max-line-length=88` | CI gate | `python-ci.yml:36-37` | **fails**: 153 violations, exit 1 (verified run) |
| `python -m build` + `twine check dist/*` | CI gate | `python-ci.yml:44-46` | twine check **PASSED** on both local artifacts (verified run) |
| `text-adventure-tui` console script | packaging | `setup.py:40-43` | maps to `main_menu`; **the built wheel maps to `game_loop` instead** (see Surprises) |
| `python -m text_adventure_tui_lib.game` | documented run | `README.md:22` | works: `__main__` guard calls `main_menu()` (`game.py:465-466`); import verified clean, both `main_menu` and `game_loop` present (verified run) |
| trigger branches | CI config | `python-ci.yml:3-7` | push/PR to `initial-game-structure` **only** |

## Key data structures

### Test fixtures
`tests/test_new_engine.py:15-33` builds the **only** loader fixture in the repo: a
`tmp_path/"test_story"` directory containing one `game_setup.yaml` — which exercises the
**old-format branch** (`yaml_loader.py:45`). There is no fixture anywhere for the
new-format branch the shipped stories use. No `conftest.py` exists
(verified run: `glob tests/conftest.py` → none).

### Packaging metadata
`setup.py` declares 3 packages (`:16`), non-recursive `package_data` globs (`:19-22`),
`python_requires=">=3.7"` (`:33`), and 3 runtime deps (`:34-38`).

## Invariants

| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| CI runs on every change | `python-ci.yml:3-7` | **violated**: trigger branch `initial-game-structure` does not exist; default branch is `main` (verified run: `git branch -a`) |
| Code imports on all matrix Pythons 3.8–3.11 | `python-ci.yml:15` | **violated**: import raises `TypeError` on 3.8 (verified run, below) |
| Lint passes | `python-ci.yml:34-38` | **violated**: 153 violations on gate 2 |
| Tests pass | `python-ci.yml:40-42` | holds (7 passed, verified run) |
| `validate` exit code signals story health | `story_tool.py:114` | only the batch form exits 1; `validate <id>` always exits 0 (verified read: `story_tool.py:71-84`) |
| Wheel matches the repo | `setup.py` | **violated**: `dist/` wheel is an older architecture (see Surprises) |

## The CI is dead, three independent ways

1. **Wrong trigger branch.** `python-ci.yml:3-7` fires only on push/PR to
   `initial-game-structure`. Current branch is `main`; remotes are `main`,
   `codegen-bot/fix-entry-point-and-enhance-docs`,
   `coderabbitai/docstrings/0d2ffe9a`, `fix-llm-verbosity-and-code-improvements`
   (verified run: `git branch -a`). No `initial-game-structure` exists.
   `git log -p --follow` shows the workflow was **born triggering on `main`**
   (commit `7d4713d`) and was repointed to `initial-game-structure` by `0c0a071`
   — CI has been unreachable since that commit — verified (run: git log -p).
2. **The 3.8 matrix leg cannot import the code.** `event_manager.py:7` annotates
   `events: list[Event]` and `game.py:73,122,169-170` use `list[str]`,
   `tuple[str, list[str]]`, `list[dict]` with **no** `from __future__ import
   annotations` anywhere in the repo (verified run: grep → 0 hits). Annotations are
   evaluated at `def` time, and PEP 585 generics only work from 3.9. Verified run on
   the machine's real Python 3.8.20:
   `import text_adventure_tui_lib.event_manager` (rich stubbed) →
   `TypeError: 'type' object is not subscriptable`; likewise a bare
   `def f(x: list[str]) -> str`. So even a push to the right branch fails the 3.8 leg
   at collection.
3. **The style gate fails today.** Verified run of the exact CI command
   (`flake8 . --count --max-complexity=10 --max-line-length=88 --statistics
   --exclude=setup.py`) → exit 1:

   | Count | Code | Meaning |
   |---|---|---|
   | 6 | C901 | `'main' is too complex (29)` — `story_tool.py:11` |
   | 41 | E501 | line too long (>88) |
   | 73 | W293 | whitespace on blank lines |
   | 11 | W291 | trailing whitespace |
   | 9 | F401 | `pytest` imported but unused (tests) |
   | 4 | E128 | continuation-line indent |
   | 2 | E302, 2 W292 | blank lines / missing newline at EOF |
   | 1 | **F811** | `execute_event_actions` redefined (`event_manager.py:260` shadows `:18`) |
   | 1 | F841 | `list_parser` unused (`story_tool.py:23`) |
   | 1 | F541 | f-string without placeholders |
   | 1 | E111, 1 E117 | indentation (`event_manager.py:204-205`) |
   | **153** | total | |

   Gate 1 (syntax/undefined-names only) passes: 0 findings (verified run). So the code
   is syntactically sound; the failures are style plus the two real smells F811/F841.

## Tests

### What the 7 tests actually assert

| Test | Asserts | Quality |
|---|---|---|
| `test_game_basics.py:1-3` | `assert True` | placeholder, asserts nothing |
| `test_game_engine.py:15-35` `test_player_action_trigger` | exact-match `player_action` condition → `set_flag` fires | real |
| `test_game_engine.py:38-59` `test_turn_count_in_location_trigger` | `turn_count_in_location >= 3` with `turns_in_location=3` injected at `:51` | real |
| `test_game_engine.py:62-85` `test_add_choice_action` | `location` condition → `add_choice` lands in `added_choices` with `trigger:` action | real, but see the bogus-flag note |
| `test_new_engine.py:36-42` `test_load_story` | old-format load: `story.id == "story_start"`, stats, inventory | real — and **asserts the old-format id bug** (`story.id` becomes the event id; fixing `yaml_loader.py:123` breaks this test) |
| `test_new_engine.py:45-68` `test_game_state_manager` | `update_stat`, `add_item`, `remove_item`, `set_flag`, `clear_flag` | real |
| `test_new_engine.py:71-92` `test_event_manager` | `location` condition → `set_flag` | real, same bogus-flag note |

### The bogus-flag detail
`tests/test_game_engine.py:76` and `tests/test_new_engine.py:85` write
`game_state.flags["current_location"] = "start"` — a **flag** named `current_location`,
not the location field. The `location` condition is evaluated by
`event_manager.py:186` via `game_state_manager.get_current_location()`, which reads
`GameState.current_location` (`data_structures.py:44`, default `"start"`). The tests
pass because the **default** already equals `"start"`; the flag write is a no-op that
would mislead a reader into thinking flags drive location — verified (read) + verified
(run: probe `data-flagtrap.py` in the DATA report reaches the same verdict).

### Coverage gaps (verified by grep over `tests/`)

- **`game.py` is 100% untested.** No test imports it — the only
  `from text_adventure_tui_lib.game` grep hits are the longer
  `...game_state_manager` import (verified run). That leaves the menu, turn loop,
  all three LLM call sites, `handle_command`, `save_game_state`, and the resume path
  with zero coverage.
- **No Ollama mock exists anywhere** — `grep -rn "ollama|mock|monkeypatch|fake" tests/`
  returns nothing (verified run). There is no seam to fake the LLM even if someone
  wanted to: `ollama_client` is a module global assigned only in `main_menu()`
  (`game.py:44, 383`).
- **GameStateManager methods never called by any test**: `get_player`, `get_story`,
  `get_current_location` (directly), `set_current_location`, `get_turn_count`,
  `increment_turn`, `increment_turns_in_location` — 7 of 14 (verified run: method-call
  census over `tests/`). The three counters/location methods are the exact ones the
  checkpoint system at `game.py:347-377` depends on.
- **Action types never exercised** (8 of 10): `clear_flag`, `add_item`,
  `remove_item`, `change_location`, `update_stat`, `override_narrative`,
  `modify_prompt`, `inject_narrative`, `present_choices`, `end_game` — tests use only
  `set_flag` and `add_choice` (verified run: grep of `"type":` in tests). The two
  broken-in-production actions (`add_item` with `item_id`, `end_game` message
  clobbering) are in the untested set.
- **Condition types never exercised** (7 of 10): `flag_set`, `flag_not_set`,
  `player_action_keyword`, `player_intent`, `inventory_has`, `inventory_not_has`,
  `game_start`, `turn_count_global`, `stat_check` — tests use only `player_action`,
  `turn_count_in_location`, `location` (verified run).
- `test_load_story` exercises only the **old** loader branch; the new branch both
  shipped stories use has no test at all (also flagged by the LOAD report).

## Packaging

### The wheel does not contain this game

`unzip -l dist/text_adventure_tui-0.1.1-py3-none-any.whl` (verified run):

- **Missing entirely**: `yaml_loader.py`, `data_structures.py`,
  `game_state_manager.py`, `story_manager.py` — i.e. the whole modern architecture.
- Its `game.py` imports only `from .event_manager import EventManager` plus stdlib,
  `ollama`, `yaml`, `importlib.resources` (verified run: `unzip -p ... game.py`) — an
  **older, different architecture** built around `story_arc.yaml` /
  `short|medium|long_story_*.yaml`, which the current tree deleted (git history:
  deleted in `3d86cb5`).
- `entry_points.txt`: `text-adventure-tui = text_adventure_tui_lib.game:game_loop` —
  **not** `main_menu` as `setup.py:40-43` says. The commit that "fixed" the entry
  point (`cb9fddc`, PR #16) came after this artifact was built.
- It **does** ship `story_parts/Whispers_of_the_Salted_Crypt/*.yaml` (the dead legacy
  copies) alongside the old `story_arc.yaml` family.
- The same stale snapshot is what sits in `~/.local/lib/python3.13/site-packages/` on
  this machine (verified run: identical imports), which is why probes must set
  `PYTHONPATH` to the repo root.
- Consequence: a user who `pip install`s this project today gets the **old** game with
  the **old** entry point, and `text-adventure-tui` never reaches `main_menu()`.
  Verified consequence on this machine: the installed copy cannot even be imported as
  the modern package (`ModuleNotFoundError: text_adventure_tui_lib.yaml_loader`).
- `twine check dist/*` → **PASSED** for both artifacts (verified run), so distribution
  *metadata* is fine — it is the *content* that is stale.
- The sdist (`tar`) was not diffed file-by-file against the wheel; both pass twine
  (verified run). `unknown (needs a byte-level diff)` whether the sdist includes the
  tests directory.

### Placeholders shipped as-is
`setup.py:10` — `author_email="author@example.com", # Please update this with your
actual email`. The comment is still present in the built wheel's METADATA
(verified run: `unzip -p ... METADATA` shows `Author-email: author@example.com`).

### MANIFEST.in vs package_data
`MANIFEST.in:3-5` uses `recursive-include ... *.yaml` (recursive), while
`setup.py:19-22` `package_data` globs are non-recursive (`*.txt`, `*.yaml`). For the
**sdist** MANIFEST.in governs (recursive → legacy chapter YAMLs included); for the
**wheel**, non-recursive `package_data` would *normally* drop the subdirectory — yet
the wheel **does** contain `Whispers_of_the_Salted_Crypt/*.yaml`
(verified run), because `include_package_data=True` (`setup.py:45`) pulls from
MANIFEST.in/git. Net effect: both artifacts ship the dead legacy tree; the mechanism
is double-tracked and fragile.

### Dependency manifests

| Package | `requirements.txt` | `setup.py:34-38` | `requirements-dev.txt` |
|---|---|---|---|
| ollama | `>=0.1.0,<0.3.0` | same | — |
| rich | `>=10.0.0,<14.0.0` | same | — |
| PyYAML | `>=5.0,<7.0` | same | `>=5.0,<7.0` (**duplicated**) |
| flake8 | — | — | `>=3.8.0,<7.0.0` |
| build | — | — | `>=0.7.0,<1.1.0` |
| twine | — | — | `>=3.4.0,<5.0.0` |
| pytest | — | — | `>=6.0.0,<8.0.0` |
| coverage | — | — | `>=5.0,<8.0` |
| black | — | — | `>=22.0,<24.0` |
| isort | — | — | `>=5.0,<6.0` |

- Runtime pins are consistent between `requirements.txt` and `setup.py`
  (verified read). `PyYAML` is listed in **both** runtime and dev manifests.
- The local 7-test pass ran under **pytest 8.4.1** (system interpreter; verified run:
  pytest header) while `requirements-dev.txt` pins `<8.0.0` — this environment simply
  does not use the dev manifest; CI would install pytest 7.x. Both versions pass the
  suite (8.4.1 verified here).
- CI installs `requirements-dev.txt` then `pip install .` (`python-ci.yml:28-31`) —
  so the CI's pytest is `<8.0.0`, not the 8.4.1 used locally.

## Doc reconciliation

Verdict key: TRUE = code matches; STALE = described an earlier architecture; FALSE =
contradicts current code.

| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| Run with `python -m text_adventure_tui_lib.game` | `README.md:22`, `DEVELOPER_GUIDE.md:306,486` | `game.py:465-466` `main_menu()` guard; import verified clean (verified run) | TRUE |
| `python story_tool.py validate` → "🎉 All stories are valid!" | `README.md:30-31` | verified run prints exactly that, exit 0 | TRUE — and worthless: the validator passes both stories while their `add_item` actions are broken (EVT/CONF) |
| 4 stories shipped ("Should show both example stories" `README.md:34-35`) | `README.md:33-35` | 2 stories (`story_tool.py list` verified run) | TRUE (both shown) |
| In-game commands `/save`, `/debug`, `/quit`, `/force_event <id>` | `README.md:236-239` | all four implemented at `game.py:208-215`; `/quit` raises `SystemExit` (crashes out of menu loop) — reachable only by typing `/quit` in the choice prompt (`game.py:183-185`) | TRUE, quality caveat |
| "Save/Load System: Persistent game state" | `README.md:10` | flags/turns/location persist; **`Player` stats & inventory are re-created from YAML on resume** (`game.py:239` → loader), narrative not saved (`game.py:251` fallback) | PARTLY FALSE (misleading) |
| `docs/architecture.md`: no event system, no story manager, no save/load; `01_intro.txt` loaded as "the" story start | `docs/architecture.md:7-38, 44` | event system, story manager, save/load all exist; intro comes from each arc's `initial_story_part` (`yaml_loader.py:83`, `game.py:264`) | STALE (whole file describes the pre-`3d86cb5` game) |
| "Currently, the game is stateless between sessions. Saving/loading … would require a persistent storage mechanism" | `docs/architecture.md:71` | `/save` writes JSON to `~/.text_adventure_tui_saves/` (`game.py:39-40, 218-230`); menu offers Resume (`game.py:436-451`) | FALSE |
| Ollama host/model via `OLLAMA_HOST`/`OLLAMA_MODEL`, default `phi4:latest` | `docs/architecture.md:66-67`, `docs/customization.md:18` | `game.py:36-37` — exact match | TRUE |
| Edit `current_story_segment_id = "01_intro.txt"` in `game.py` to change the intro | `docs/customization.md:76-84` | identifier does not exist (verified run: grep → 0 hits); intro file comes from the arc's `initial_story_part` | STALE (instructions impossible to follow) |
| Quoted prompt bodies of `get_llm_story_continuation` / `get_llm_options` ("exactly 4 distinct… numbered list") | `docs/customization.md:88-110` | current prompts differ in wording and mechanism (`format="json"` at `game.py:144`; numbered-list prompt gone) | STALE (quoted code no longer exists) |
| Fallback choices are a hardcoded `hardcoded_choices` list | `docs/customization.md:112-121` | fallback is `["Look around.", "Check inventory.", "Wait.", "Leave."]` inline at `game.py:165`; identifier `hardcoded_choices` gone | STALE |
| "python game.py" | `docs/customization.md:24, 30` | no `game.py` at repo root (verified: file list) | FALSE |
| Extension points: add trigger in `EventManager._evaluate_trigger()`, action in `_perform_actions()` | `DEVELOPER_GUIDE.md:529-536` | both methods exist (`event_manager.py:163-258`, `:91-161`) | TRUE |
| "Add validation in `StoryManager`" for new trigger types | `DEVELOPER_GUIDE.md:531` | `validate_story` checks only structural keys; it has no trigger/action vocabulary at all (`story_manager.py:124-137`) | MISLEADING |
| `create` produces the 3 files "in `story_parts/`" | `DEVELOPER_GUIDE.md:167-170` | arc+intro → `stories_path`, events → `events_path` (`story_manager.py:189-201, 248-250`) — events land in a **different directory** than the guide implies | MISLEADING |
| Arc schema incl. `checkpoints.flag_messages` | `README.md:64-72`, `DEVELOPER_GUIDE.md:191-193` | consumed at `game.py:356-369` | TRUE (but `prompt_injection` on a `force_end_game` checkpoint is a dead write — ENTRY report) |
| General events provide "Health warnings, Location descriptions, Help system, Debug information, Time-based events" | `README.md:225-232` | all five exist in `general_events.yaml` (`:4, :33, :62, :81, :48`) | TRUE |
| `README_OLD.md` as a whole | `README_OLD.md` | describes the same pre-`3d86cb5` architecture as `docs/architecture.md` (story_arc.yaml, 3 length-tier stories); its YAML schema section (`:158-214`) happens to match the **new** arc format | STALE, superseded by README.md; kept with no deprecation note |
| Repo layout comment block | `README.md:194-208` | matches the tree | TRUE |

### AGENTS.md conformance (verified runs)

`AGENTS.md` prescribes: Black (88), isort, type hints on all signatures,
Google-style docstrings, `try/except` error handling. Measured:

| Rule | Measurement | Command |
|---|---|---|
| Black 88-col | 41 E501 + 86 whitespace violations under flake8's Black-aligned settings | CI flake8 run |
| Type hints "all function signatures" | 8 of 48 functions fully annotated (yaml_loader 4/4, game 4/11, everything else 0) | AST census |
| Google docstrings | 10 of 48 functions have any docstring (event_manager 1/8, game 1/11, gsm 0/16, story_manager 4/5, yaml_loader 4/4, story_tool 0/1) | AST census |
| `try/except` handling | 8 `except Exception`, 0 bare `except:` — broad but never bare | grep |
| isort | not run (not installed in this env) | — |

Verdict: the codebase conforms to almost none of AGENTS.md; AGENTS.md reads as an
aspiration (or was written for a different phase of the project).

## Extension points

- **Add a test**: drop a file in `tests/test_*.py`; pytest picks it up
  (`python-ci.yml:41` runs bare `pytest`). First file to open for style:
  `tests/test_game_engine.py`. The missing high-value tests are: any `game.py`
  behaviour (needs an `ollama_client` seam first), `save_game_state` round-trip, and
  the new-format loader branch.
- **Fix CI**: change `python-ci.yml:4,6` back to `main`; drop 3.8 from the matrix
  (line 15) or add `from __future__ import annotations` to `event_manager.py` and
  `game.py`; then clear the 153 style findings (or relax gate 2).
- **Release correctly**: the entry-point fix already in `setup.py:40-43` needs a
  rebuild — `dist/` and site-packages still carry `game_loop` and the pre-loader
  architecture.

## Surprises

- **The CI has never run against this architecture.** Born on `main`
  (`7d4713d`), repointed to a branch that was deleted/renamed before the modern engine
  landed (`0c0a071`) — verified (run: git log -p). Every "CI passed" assumption about
  the current code is unearned.
- **The built wheel is a different game.** Same version number (0.1.1), same name,
  older architecture, different entry point (`game_loop` vs `main_menu`) — verified
  (run: unzip). Version was never bumped when the engine was rewritten.
- **`validate <id>` cannot fail a build.** `story_tool.py:71-84` prints errors and
  exits 0; only the batch form exits 1 (`:114`) — verified (read). Any CI hook built
  on the per-story form silently passes broken stories.
- **The one test of the loader pins a bug.** `test_new_engine.py:38` asserts
  `story.id == "story_start"` — the old-format loader's event-id-as-story-id defect
  (`yaml_loader.py:123`). A correct fix turns the suite red.
- **Tests contain a misleading no-op.** The `flags["current_location"]` writes
  (`test_game_engine.py:76`, `test_new_engine.py:85`) do nothing; the location
  condition reads the real field whose default already matches — verified (run).
- **`flake8` gate 1 vs gate 2 split hides real smells.** Gate 1 is clean; the 153
  gate-2 findings include F811 (duplicate method) and F841 — i.e. the "style" gate is
  actually carrying two correctness findings.

## Docs vs code

Covered exhaustively in the reconciliation table above; summary counts:
**12 TRUE / partial-TRUE, 9 STALE, 3 FALSE, 2 MISLEADING** across the six documents.
The two worst offenders are `docs/architecture.md` (100% stale) and
`docs/customization.md` (gives impossible editing instructions).

## Unknowns

- Whether the `dist/` sdist contains the tests and docs (only the wheel was listed
  file-by-file) — needs `tar tzf dist/*.tar.gz`.
- Whether any published PyPI release exists with this 0.1.1 content — the local
  artifacts pass `twine check`, but nothing here proves they were uploaded — needs
  PyPI query or maintainer access.
- Whether `initial-game-structure` still exists as a *remote* branch on GitHub
  (only local refs were inspected) — needs `git ls-remote`.
- isort conformance was not measured (tool absent in this environment) — needs
  `pip install isort` and `isort --check-only`.
- Exact pytest behaviour under the pinned 7.x line (local verification used 8.4.1) —
  needs an install of `requirements-dev.txt` in a clean venv.

# Text Adventure TUI — architecture

> Verified against commit `7f349d1` (2025-07-22) on 2026-10-13 by a deep-tier codebase dive.
> Sections surveyed: 7 of 7 · Flows traced: 4 (of 8 identified; the other 4 were folded into these) ·
> Evidence: ~600 tagged claims — 563 verified (346 by executed probe), 23 inferred, ~42 open unknowns.
> Independent skeptic wave was skipped at user request; the orchestrator re-ran a sample of
> load-bearing probes instead (dead-code line number, C-locale decode crash, menu arithmetic,
> wheel contents, both flake8 gates, pytest, Python 3.8 import). Not verifiable here: a live
> Ollama server, a clean install, other OSes/locales.

## What this is

A terminal text-adventure engine: the *narrative prose* is generated live by a local Ollama
LLM, while all *branching, puzzles and state* are defined in YAML files interpreted by a
generic trigger/action event engine. Two example stories ship in `text_adventure_tui_lib/`.
~1,650 lines of Python, ~1,000 lines of story YAML. Single-threaded, no server, no database;
the only filesystem writes are JSON saves under `~/.text_adventure_tui_saves/`.

The single most important architectural fact: **the YAML content layer and the engine have
drifted apart**. The engine's `add_item` action reads an `item_id:` key
(`text_adventure_tui_lib/event_manager.py:111`) that no live story file uses — every live
story writes `value:` — so the flagship story is unwinnable and crashes one turn after its
first puzzle. A 0.1.1 release and a stale site-packages install on typical dev machines ship
a *different, older* game.

## How to run it

| Task | Command | Needs | Verified |
|---|---|---|---|
| Run (works) | `python -m text_adventure_tui_lib.game` | Ollama running locally for actual play; menu works without it | run: menu renders with no server |
| Run (declared) | `text-adventure-tui` console script | a **rebuilt** install — every artifact on a typical machine still points at the old `game_loop` of the 0.1.1 wheel | run: inspected `~/.local/bin/text-adventure-tui` |
| Test | `pytest` | — | run: **7 passed in 0.02s** |
| Lint (CI gate 1) | `flake8 . --select=E9,F63,F7,F82` | — | run: passes (0) |
| Lint (CI gate 2) | `flake8 . --max-complexity=10 --max-line-length=88` | — | run: **fails, 153 violations** |
| Validate stories | `python story_tool.py validate` | run from repo root (paths are relative, `story_tool.py:13-18`) | run: prints "🎉 All stories are valid!" |
| Build | `python -m build` | — | artifacts in `dist/` inspected; not rebuilt |

Requires **Python ≥ 3.12**: `game.py:83` puts a backslash inside an f-string expression, a
`SyntaxError` before 3.12 (verified: `py_compile` under 3.8/3.10/3.11 fails), and PEP 585
annotations (`list[str]` at `game.py:73,122,169`; `event_manager.py:7`) break import on 3.8
(verified on a real 3.8.20: `TypeError: 'type' object is not subscriptable`).

## The map

```text
                 python -m text_adventure_tui_lib.game / console script
                                    │
                 game.py  (ENTRY — menu, turn loop, all LLM calls)
                   │        │              │
                   │        │              └── ollama.Client.chat()  ×1–3 per turn  [network]
                   │        │
                   │        ├── EventManager  (EVT — trigger evaluation, action dispatch)
                   │        │       ▲ reads trigger/action vocabulary from…
                   │        │
                   │        ├── StoryManager (STRY — discovery, validation, templates)
                   │        │       └── story_tool.py (author CLI, argparse)
                   │        │
                   │        └── yaml_loader.load_story_and_player (LOAD — format bridge)
                   │                ▲ parses…
                   │
                   ├── GameStateManager (DATA — façade over mutable state)
                   │        └── data_structures.py: Player / Event / Story / GameState
                   │
                   └── save_game_state → ~/.text_adventure_tui_saves/*.json  [filesystem]

  content that IS the game logic (CONF):
    text_adventure_tui_lib/events/*.yaml            (6 general + 2×10 story events)
    text_adventure_tui_lib/story_parts/*_story_arc.yaml   (2 arcs)
    text_adventure_tui_lib/story_parts/*.txt        (intros — mostly dead, see FLOW-2)
    text_adventure_tui_lib/story_parts/Whispers_of_the_Salted_Crypt/  (dead legacy copies)
```

In five bullets a newcomer can repeat:

1. `game.py` is the whole application: menu, turn loop, three LLM call sites, slash commands, save writing.
2. `event_manager.py` is a hardcoded if/elif rule engine — 12 condition types, 10 action types, no registry.
3. Stories are YAML: one arc file (metadata) + one events file (behaviour); general events load first and win dict precedence.
4. `GameStateManager` wraps one `GameState` by reference; flags/location/counters persist via `/save`, but **player stats/inventory do not survive resume**.
5. Everything is re-read from disk constantly; there is no cache, no validation layer that catches content bugs, and no concurrency.

## Modules

### ENTRY — `text_adventure_tui_lib/game.py` (466 lines)

The entire application shell. Entrypoints: `__main__` guard (`game.py:465-466`) and the
console script (`setup.py:40-43`), both → `main_menu()` (`game.py:380-462`). Module level
captures `OLLAMA_HOST`/`OLLAMA_MODEL` at import time (`game.py:36-37`); `ollama_client` is a
module global assigned only in `main_menu` (`game.py:44,383`) and dereferenced by the three
LLM helpers (`game.py:86,110,140`).

Key facts:

| Fact | Location |
|---|---|
| Ollama client construction is offline-safe; outages detonate later in the loop | `game.py:382-386` vs `:140-165` |
| An outage **crashes the game**: `except` prints `raw_json_str`, bound only at `:146` → `UnboundLocalError`; the 4-choice fallback at `:165` only covers parse failures | `game.py:161-165` |
| 1–3 LLM round-trips per turn (see FLOW-3 ledger) | `game.py:280,312,322` |
| `llm_instructions` is created at `:284`, *after* the choices call at `:280` — `modify_prompt` can never steer the choices prompt | `game.py:280-284` |
| `/save` writes only `game_state` + `event_manager_state`; `narrative` and the whole `Player` are not persisted (resume shows "Your story continues...", stats/inventory re-read from YAML) | `game.py:218-230,239-251` |
| Counters increment *after* the game-end check; checkpoint scan runs *after* increment — checkpoint turn N fires in the turn bannered N−1, and ending turns are never counted | `game.py:334-353` |
| Checkpoint `prompt_injection` is a dead write (list recreated at `:284` next turn; force-end `return`s at `:377`) | `game.py:354-355` |
| With 0 stories the menu prints "1. Toggle / 2. Quit" but the parser still tests 1/2/3 = Resume/Toggle/Quit — the printed labels lie (run-verified) | `game.py:419-422` vs `:426-462` |
| Free text is never accepted as an action — input must be a digit or `/command`; "natural language" is only ever LLM-authored choice labels | `game.py:176-199` |
| `save` files accumulate forever; never pruned | `game.py:219-230` |

### EVT — `text_adventure_tui_lib/event_manager.py` (281 lines)

The rule engine. `EventManager` collapses events into an id-keyed dict preserving list order
(`event_manager.py:8`); `check_and_trigger_events` (`:38-89`) evaluates every event's trigger
and dispatches actions; `_evaluate_trigger` (`:163-258`) and `_perform_actions` (`:91-161`)
are hardcoded if/elif chains — 12 condition types, 10 action types, no registry, no `else`.

Key facts:

| Fact | Location |
|---|---|
| `execute_event_actions` is defined **twice**; the second binding wins (flake8 F811). The dead first def printed DEBUG-not-found and never marked `once`; the live one marks `once` **before** running actions — so `/force_event` and `trigger:` choices permanently consume a once-event even if its actions crash | `event_manager.py:18-36` (dead), `:260-281` (live), `:277-279` vs `:77-78` |
| `add_item` reads `action.get("item_id")`; every live story writes `value:` → `inventory.append(None)` → next turn `', '.join(inventory)` raises `TypeError` and kills the loop. **This single line (`:111`) is why the flagship story is unwinnable** | `event_manager.py:110-111`; `game.py:127-137` |
| Unknown condition types are silently False (no `else` before the append at `:252`); under AND (default) one typo disables the whole event | `event_manager.py:184,252` |
| `player_action_keyword` is a case-insensitive **substring** test with no word boundaries: `"search desk"` does not match "I search the desk" (run-verified) | `event_manager.py:191-197` |
| Override breaks the pass (`:80-81`) and skips the LLM continuation (`game.py:318-327`), so a `modify_prompt` paired with an override is a dead write | `event_manager.py:80-81,123-124` |
| `end_game` overwrites the override with its `message` (default "The story ends here.") — shipping endings' epilogues are clobbered; the message then never displays because the loop breaks before the next `display_story` | `event_manager.py:148-154`; `game.py:318-344` |
| `present_choices` ignores `text:` and per-choice `condition:` (documented in DEVELOPER_GUIDE.md:363-365) | `event_manager.py:139-147` |
| DEBUG prints (`Event 'x' triggered!`) are **not** gated by debug mode | `event_manager.py:60-62` |
| No exception handling: an action raising mid-list keeps earlier mutations, skips the rest, kills the process; no rollback | `event_manager.py:91-161` |

### DATA — `data_structures.py` (45) + `game_state_manager.py` (56)

Four dataclasses (`Player`, `Event`, `Story`, `GameState`) with untyped `Dict/List[str, Any]`
payloads and no construction-time validation; the only hard check in the pipeline is
`data["id"]` (`yaml_loader.py:22`). `GameStateManager` stores its `GameState` **by reference**
and its getters return the live mutable objects (`game_state_manager.py:14-15,24-25,35-36`).

Key facts: `set_current_location` resets `turns_in_location` only on an actual change
(`:44-47`) — which makes `story_start`'s `change_location` a provable no-op (see FLOW-2);
`increment_turn`/`increment_turns_in_location` are called every turn (`game.py:347-348`);
there is no concurrency anywhere in the repo (grep-verified: no threading/async/locks); no
schema version in saves; `json.dump(..., default=lambda o: o.__dict__)` (`game.py:229`)
serialises the whole `GameState` including the discarded-on-resume `Story`.

### LOAD — `yaml_loader.py` (142 lines)

A two-branch format bridge: if `<name>_story_arc.yaml` exists → new format (arc + general
events + story events, in that order, `yaml_loader.py:38-63`); else → legacy per-story
directory (`:96-142`). Event dict keys are whitelisted to five (`:21-27`); every other key an
author writes vanishes silently. `.get` defaults cover *missing* keys only — a present-but-null
`trigger:` yields `None` and crashes later (`event_manager.py:170`).

Key facts:

| Fact | Location |
|---|---|
| Event load order is load-bearing: general events first → earlier dict slots → they shadow same-id story events and their overrides win the `break` | `yaml_loader.py:52-63`; `event_manager.py:8,80-81` |
| Legacy branch mines the `story_start` *event* for story metadata → `story.id == "story_start"` → saves named `story_start_*.json` can never resume (`ValueError: No events found`) | `yaml_loader.py:112-124,108-109`; `game.py:221,451` |
| The events directory is *derived* (`stories_path.parent / "events"`), so `StoryManager`'s `events_path` and `story_tool.py --events-path` validate files the loader never reads | `yaml_loader.py:48`; `story_manager.py:103,144` |
| `open()` with no `encoding=`: the `•` bullets in `general_events.yaml:73-76` crash **both** stories with `UnicodeDecodeError` under a C locale (re-verified) | `yaml_loader.py:10,54`; `game.py:266` |
| No caching: 3 menu redraws + 1 game start = 10 YAML reads (measured) | `story_manager.py:49`; `yaml_loader.py:42,54,61` |
| Every `Story` default is written twice (loader `.get` defaults mirror dataclass defaults; currently agree, nothing pins them) | `yaml_loader.py:82-91`; `data_structures.py:26-35` |
| The whole `story_parts/Whispers_of_the_Salted_Crypt/` tree is unreachable: `discover_stories` globs top-level only, nothing produces that story id | `yaml_loader.py:100-106`; `story_manager.py:47` |

### STRY — `story_manager.py` (263) + `story_tool.py` (168)

Discovery, validation, templating, and the author CLI. `discover_stories` re-globs and
re-parses every arc on **every menu redraw** (`story_manager.py:47-50`, called from inside
`game.py:393`'s loop). `validate_story` performs ~9 structural checks — required arc fields,
list-shaped events file, a `story_start` event present (`story_manager.py:116-122`) — and
**nothing else**: no trigger/action vocabulary, no flag/location/item cross-references, no
reachability. It never opens `general_events.yaml` (`:103`). The template generator writes an
arc whose turn-20 forced ending keys on a `success` flag that no template event ever sets —
every template story ends "Your adventure ends, but perhaps not as you hoped."
(`story_manager.py:168-181`).

`story_tool.py`: `list` and batch `validate` work (verified run); `validate <id>` always
exits 0 even when the story is invalid (`:71-84`); paths default to *relative* strings, so the
tool silently finds nothing outside the repo root while `game.py` anchors on `Path(__file__)`
(`story_tool.py:13-18` vs `game.py:389-390`); `list_parser` is dead (flake8 F841).

### CONF — the story content (13 files, ~1,000 lines)

The YAML **is** the game logic. Both shipped stories are flag/location/item state machines:

- **Whispers of the Salted Crypt** (beginner, 25 turns): 10 story events + 6 general. The
  intended chain is `find_elians_journal → read_journal_clue → find_hidden_key →
  arrive_at_bluffs → tide_recedes → enter_the_crypt → rescue_elian → two endings`. The chain
  is **broken at the first link** by the `add_item` key mismatch: `elians_journal` never enters
  the inventory correctly, so `inventory_has: elians_journal` (`whispers…yaml:60`) can never
  fire, `runic_key` is never granted, `rescue_elian` is unreachable, and the checkpoint's
  `elian_is_found` epilogue can never be the "found" variant.
- **The Clockwork Heist** (medium, 15 turns): same `value:`-vs-`item_id` defect on its
  `add_item` uses; same class of brokenness.
- The endings route a `present_choices` action string (e.g. `end_story_success_heroic`,
  `whispers…yaml:212-218`) verbatim through `game.py:196-197` into an exact-match
  `player_action` condition (`event_manager.py:200-201`) — the selection *is* the trigger.
- The dead legacy copies under `story_parts/Whispers_of_the_Salted_Crypt/` are the mirror
  image: they use the engine's **correct** `item_id:` key but the **wrong** condition name
  `flag_is_set` (3×; engine implements `flag_set`, `event_manager.py:187`) — each copy fails
  on a different key, evidence of a half-migrated rewrite.
- `general_events.yaml`: `inventory_full_warning` fires on the substring `"get"` with no
  inventory check (false positives); `first_time_in_location` is `once` **globally**, so it
  describes only the first location of a game, ever; `help_command`/`debug_info` need the
  player to type free text, which the input loop never accepts.
- Dead/orphan content: `01_intro.txt` (read then unconditionally overwritten — see FLOW-2),
  `whispers_intro.txt` and `idea.txt` (referenced by nothing), the legacy directory (ships in
  the wheel anyway, `MANIFEST.in:3-5`).

### TOOL — tests, CI, packaging, docs

| Fact | Evidence |
|---|---|
| **CI cannot run**: workflow triggers only on `initial-game-structure`, a branch that does not exist (originally `main`, repointed by commit `0c0a071`) | `.github/workflows/python-ci.yml:3-7`; `git log -p` |
| **Its matrix is unrunnable anyway**: Python 3.8–3.11 all fail to *compile* the code (f-string backslash, `game.py:83`; verified py_compile) — and the matrix floor 3.8 also fails PEP 585 at import (verified on 3.8.20) | CI `:15`; `game.py:83,73,122` |
| **Style gate fails**: 153 violations incl. F811 (duplicate method) and F841; syntax gate passes | run, both gates |
| Tests: 7 pass in 0.02s; `game.py` has **zero** coverage (no test imports it; no Ollama mock exists); 8 of 10 action types and 7 of 10 condition types never exercised; two tests write a misleading no-op flag `flags["current_location"]`; one test **pins the loader bug** (`story.id == "story_start"`, `test_new_engine.py:38`) | `tests/*.py`; greps |
| The built wheel (`dist/…0.1.1`) is an **older architecture**: no `yaml_loader/story_manager/game_state_manager/data_structures`; entry point `game:game_loop`, not `main_menu`; `twine check` passes anyway | `unzip -l/-p` (verified) |
| `author_email="author@example.com"` placeholder ships in METADATA | `setup.py:10`; wheel METADATA |
| AGENTS.md conformance: 10/48 functions have docstrings, 8/48 fully annotated, 41 E501 — Black/isort/type-hint rules essentially unmet | AST census + flake8 |

## Flows

### FLOW-1 — Launch → story menu (traced; probes `f1-*`)

Import-time config (`game.py:1-44`) → offline-safe `ollama.Client` (`:382-386`) →
`StoryManager` anchored on `Path(__file__)` (`:389-391`) → infinite menu loop: title →
`discover_stories()` **per redraw** (`:397` → `story_manager.py:42-72`) → render →
`Prompt.ask` (`:424`) → dispatch (`:426-462`). With 2 stories the mapping is
1/2 = stories, 3 = Resume, 4 = Toggle, 5 = Quit; content-warning y/n gates every story start
(`:431-434`). With 0 stories the printed labels are lies (run-verified: printed "1. Toggle"
actually Resumes; Quit is the unprinted `3`). Out-of-range digits redisplay **silently**
(no `else` on the digit chain). Resume globs `~/.text_adventure_tui_saves/*.json` by mtime
(`:438-451`) and needs the key chain `game_state.current_story.id` or it `KeyError`s. The only
mutations are the module globals `ollama_client` and `DEBUG_MODE_ENABLED`; the flow writes
nothing to disk. Ctrl-C/EOF at any prompt is uncaught → traceback.

### FLOW-2 — New-game prelude (traced; probe `f2-prelude.py` replays `game.py:252-274` against the real YAML)

`display_title` → `load_story_and_player` (3 YAML reads; `Player` from the **arc**; 16-event
dict, general first — probe-printed order) → `GameState(current_location=story.starting_location)`
with dataclass defaults → wrap by reference → read `initial_story_part` into `narrative` →
`execute_event_actions("story_start", gsm, [])`. For Whispers, `story_start`'s four actions
reduce to: `set_flag` (the **only durable write** of the whole prelude), `change_location`
(no-op — location already seeded), `override_narrative` (replaces the intro), `modify_prompt`
(appended into the literal `[]` at `game.py:272` — garbage on statement end). Net: **the intro
`.txt` never reaches the screen**; the game enters the loop bannered **"Turn 0"** with one
boolean set. Every prelude failure mode (empty arc → `AttributeError`; malformed events → raw
`KeyError`; C locale → `UnicodeDecodeError`) is process-fatal — the menu validates none of it.

### FLOW-3 — One turn of the loop (traced; stub-driven `game_loop`, probes `f3-*`)

Ordered: banner "Turn N" (`:277`) → **LLM#1** options/summary (`:280`, temp 0.7, `format="json"`;
its summary *overwrites* `narrative` and the previous context is discarded) → display (`:281`)
→ fresh `llm_instructions` (`:284`) → **pre-choice event pass** on empty input (`:285-287`)
→ pre-injections shown *after* the main text (`:290-291`) → `get_player_choice` (digits and
`/commands` only, `:168-199`) → either **EVENT branch** (`:300-306`: forced execution, `continue`
— no intent, no continuation, **counter frozen**) or **LLM#2** intent (`:312`, always) →
**post-choice event pass** (`:313-315`; its `added_choices`/pre-injections are dropped — only
the pre-pass's are ever rendered) → override branch (`:318-319`, skips LLM#3) or **LLM#3**
continuation (`:322-327`, the *only* consumer of `llm_instructions`) → post-injections
(`:330-331`) → game-end check *before* counters (`:334-344`) → increments (`:347-348`) →
checkpoint scan (`:351-377`).

LLM-call ledger (run-verified): normal turn = **3** calls; override turn = **2**;
EVENT-triggered turn = **1** (frozen counter). Checkpoint `prompt_injection` reaches no prompt
on any path (run-verified: 0 of 24 prompts). Footgun: `:305`
`event_results.get("override_narrative", narrative)` — the key is always present and `None`
unless an override ran, so any `trigger:`-routed event without an override sets
`narrative = None` and the next prompt's situation is literally `'None'` (run-verified; latent
— no shipped YAML uses `trigger:` choices today, but `/force_event` typos and future content
hit it). Failure modes: outage → `UnboundLocalError` crash; 0/>4 choices or bad JSON →
graceful fallback (`:165`); intent/continuation failures → sentinel strings that *become*
`narrative`; Ctrl-C anywhere → uncaught.

### FLOW-4 — One YAML event → state mutations (traced; worked example `find_elians_journal`, probe `f4-probe1.py`)

Bytes → `yaml.safe_load` (no encoding) → concatenated list (general first; this event at
index 7) → `Event` via the 5-key whitelist (`yaml_loader.py:20-28`; unknown keys silently
dropped — probe-verified) → dict position 7 in `EventManager` → per-pass: once-skip
(`:51-55`) → `_evaluate_trigger` (`location` equality; keyword substring needing truthy input;
`flag_not_set` live-dict read; unknown type ⇒ False; AND `all()` at `:254-255`) → ungated
DEBUG print (`:60-62`) → `_perform_actions`: `set_flag` persists, `add_item` grants `None`
(the bug), `override_narrative` is a local, `modify_prompt` appends into the caller's
per-turn list (probe identity-verified) → merge, once-mark *after* success (`:77-78`),
**break on override** (`:80-81`) → `game.py` swaps `narrative` and skips the continuation, so
this event's own prompt guidance is a dead write. A crash mid-action-list keeps earlier
mutations and kills the process (probe-verified; no rollback).

Field-level chain for the bug, end to end:
`add_item / value: "elians_journal"` (whispers…yaml:41-42) → loader passes verbatim
(`yaml_loader.py:25`) → `event_manager.py:110-111` reads `item_id` → `None` →
`game_state_manager.py:27-29` appends → `inventory == [None]` (probe) → `inventory_has`
conditions never fire → `game.py:127-137` `', '.join` → `TypeError` crash one turn later.

### Identified but not separately traced

FLOW-5 (event-supplied choice routing) and FLOW-8 (intent classification) were folded into
FLOW-3 hops 7–11; FLOW-6 (save/resume) is covered piecemeal (FLOW-1 resume hops, DATA
round-trip, FLOW-3 counters) but no tracer walked a full resume end-to-end; FLOW-7
(`story_tool create` → validate → play) was exercised to the template-and-validate stage by
STRY probes but never played. These four are the natural next tracers.

## What is surprising

1. **The shipped flagship story is unwinnable, and the validator blesses it.** `add_item`
   reads `item_id:` (`event_manager.py:111`); all five live `add_item` uses write `value:`.
   Inventory becomes `[None]`, `inventory_has` chains die, and the game *crashes* on
   `', '.join` one turn after the first puzzle — while `story_tool.py validate` prints
   "🎉 All stories are valid!" (both run-verified).
2. **An Ollama outage is a crash, not a fallback.** The `except` at `game.py:163` prints
   `raw_json_str`, which is unbound when the connection fails → `UnboundLocalError`. The
   fallback at `:165` only covers parse/count failures (run-verified).
3. **The released artifact is a different game.** The 0.1.1 wheel (and the stale site-packages
   copy shadowing every probe) contains the pre-rewrite architecture with entry point
   `game_loop`, while `setup.py` declares `main_menu` — and its `add_item` reads `value:`,
   the opposite convention. Version was never bumped across the rewrite.
4. **Most documented steering machinery is dead code at runtime**: `modify_prompt` can never
   reach the choices prompt (`:284` is created after `:280`), checkpoint `prompt_injection`
   reaches no prompt on any path, the intro `.txt` is discarded, `story_start`'s
   `change_location` is a no-op, and `Event.name` is loaded then never read.
5. **CI has never run against this architecture** (wrong trigger branch, unrunnable matrix,
   failing style gate) — and the two tests that do cover triggers pass for the wrong reason
   (`flags["current_location"]` no-ops; the `location` default already matches).

## Docs vs code

12 claims TRUE / partial, 9 STALE, 3 FALSE, 2 MISLEADING across the six documents (full
per-section tables in the working files). The load-bearing rows:

| Claim | Doc | Reality | Verdict |
|---|---|---|---|
| "the game is stateless between sessions" | docs/architecture.md:71 | `/save` writes JSON; menu offers Resume (`game.py:218-230,436-451`) | FALSE — file is 100% stale (describes the pre-event game) |
| Save/Load: "Persistent game state" | README.md:10 | `Player` stats/inventory re-created from YAML on resume (`game.py:239-247`) | PARTLY FALSE |
| Edit `current_story_segment_id = "01_intro.txt"` in game.py | docs/customization.md:76-84 | identifier does not exist (grep: 0 hits); intro comes from the arc and is then discarded | STALE — instructions impossible |
| Quoted prompt bodies / `hardcoded_choices` | docs/customization.md:88-121 | current prompts differ (`format="json"`, `game.py:144`); fallback is inline at `game.py:165` | STALE |
| "python game.py" | docs/customization.md:24,30 | no such file | FALSE |
| Extension points `_evaluate_trigger` / `_perform_actions` | DEVELOPER_GUIDE.md:529-536 | both exist (`event_manager.py:163-258`, `:91-161`) | TRUE |
| "Add validation in StoryManager" for new trigger types | DEVELOPER_GUIDE.md:531 | `validate_story` has no trigger vocabulary at all | MISLEADING |
| `python story_tool.py validate` → "🎉 All stories are valid!" | README.md:30-31 | prints exactly that (run) — for a story whose first puzzle crashes the game | TRUE but worthless |
| In-game commands `/save /debug /quit /force_event` | README.md:236-239 | all implemented (`game.py:208-215`) | TRUE |
| OLLAMA_HOST/OLLAMA_MODEL, default `phi4:latest` | docs/architecture.md:66-67 | `game.py:36-37` | TRUE |
| README_OLD.md | whole file | describes the pre-`3d86cb5` architecture; kept with no deprecation note | STALE |

## Where to change what

- **Fix the broken stories (one line):** `event_manager.py:111` — `action.get("item_id")` →
  `action_value` (already extracted at `:104`), matching `remove_item` (`:113`) and
  `inventory_has` (`:203`). Repairs `read_journal_clue`/`rescue_elian` reachability and the
  `TypeError` crash. Update the legacy copies' `flag_is_set` → `flag_set` if they are ever
  revived.
- **Survive an Ollama outage:** bind `raw_json_str = ""` before the `try:` at
  `game.py:139-146` (or guard the print at `:163`); the `:165` fallback already handles the
  rest.
- **Let event guidance reach the LLM:** create `llm_instructions` before `:280`, pass it into
  `get_llm_options` (`:122`), and fix the three instruction-destroying paths
  (`:305`'s `None`, `:318`'s skip, `:355`'s checkpoint append).
- **Make the EVENT branch sane:** at `game.py:305` test `is not None` (like `:318` does);
  decide whether `EVENT_TRIGGERED` turns should `increment_turn` (`:300-306` vs `:347`).
- **Add a condition/action type:** one `elif` in `event_manager.py:185-250` (conditions) or
  `:106-154` (actions) — no registry; end with a `met =` assignment or the event silently
  dies. Update `DEVELOPER_GUIDE.md:87-121` (it currently matches the implemented set).
- **Add a story:** `story_parts/<id>_story_arc.yaml` + `events/<id>_story_events.yaml`
  (must contain a `story_start` event); use `item_id:` only after fixing `:111`; check with
  `python story_tool.py validate` (structural only). Schema: `README.md:53-106`.
- **Revive CI:** `.github/workflows/python-ci.yml:4,6` → `main`; `:15` → `["3.12", "3.13"]`
  (or add `from __future__ import annotations` + fix `game.py:83`); clear the 153 style
  findings; then rebuild/reinstall so the console script matches `setup.py:42`.
- **Rewrite the docs:** `docs/architecture.md` and `docs/customization.md` describe a
  previous game; `README_OLD.md` should be deleted or marked superseded.

## Unknowns

Needs a **live Ollama server** (absent here): what turn-1 text the player actually reads
(LLM summary of the override); real choice-label wording, hence whether substring keyword
triggers and `player_intent` events ever fire in practice; whether `format="json"` is
honoured by `phi4:latest`; per-turn latency of up to 3 sequential calls; which exception a
downed server raises into the `:163` crash.

Needs a **clean install/venv**: whether `pip install .` of the current tree yields a working
`text-adventure-tui` (this machine's site-packages is contaminated with 0.1.1); whether the
sdist matches the wheel's contents; whether a published PyPI release exists.

Needs **author intent**: was the half-migrated `item_id`/`value` key an oversight; is
`story_start`'s no-op `change_location` vestigial; is the template's never-set `success` flag
deliberate; was the duplicate `execute_event_actions` merge debris.

Needs **other environments**: Windows/locale behaviour of the no-encoding `open()` calls
(`yaml_loader.py:10`, `game.py:266`); tty Ctrl-C/EOF exit statuses; `Path.glob` ordering
guarantees for the legacy branch (`yaml_loader.py:103`).

Needs **history/upstream**: whether the legacy chapter format was ever reachable in a
release; whether any real save files exist that the unresumable-old-format bug would bite.

## Method, coverage, limits

Every hand-written file in the repo (37 files: 9 library modules, 3 tests, `story_tool.py`,
`setup.py`, 3 manifests, CI, 6 docs — plus the 13 content files under CONF) is assigned to
exactly one section in the coverage ledger; generated/undiscovered paths (`dist/`,
`egg-info`, `__pycache__`, `.temp/`, `LICENSE`, `.gitignore`) are excluded with reasons.
Seven surveyor reports and four tracer reports total ~2,700 lines of evidence-bearing working
files with ~600 evidence tags (563 verified — 346 by executed probe — 23 inferred). The
independent skeptic wave was skipped at user direction; the orchestrator instead re-ran a
sample of the most load-bearing probes (duplicate-method line number, C-locale decode crash,
zero-story menu arithmetic, wheel listing/METADATA/entry point, both flake8 gates, pytest,
Python 3.8 import, `PYTHONPATH` shadowing) and read every working file in full. The full
evidence chain — the coverage ledger, the repository inventory, all seven section reports,
all four flow traces, and every probe script with its captured output — is preserved in-repo
under `docs/architecture/evidence/` (`sections/`, `flows/`, `probe/`, `ledger.md`,
`inventory.txt`).

# Text-Adventure-TUI: ENTRY — console entry, main menu, game loop, LLM calls, commands, save/resume

Prefix: ENTRY · Commit: 7f349d1 · Depth: deep
Scope: `text_adventure_tui_lib/game.py` (466 lines, read fully). Promise docs read: `README.md`, `DEVELOPER_GUIDE.md`, `docs/architecture.md`, `docs/customization.md`, `setup.py`, `.github/workflows/python-ci.yml`. Neighbour files opened only for contract cross-checks: `event_manager.py` (lines 18–37, 110–160, 255–281), `game_state_manager.py` (49–56), `data_structures.py` (defaults).
Method: 7 probes under `/tmp/opencode/cdd-text-adventure-tui/probe/entry-probe0{1,2,3,4,5,6,7}-*.py`, all run with `PYTHONPATH=<repo>` from the repo root (probe04 hung — infinite loop, superseded by bounded probe05; kept for the record). Plus `py_compile` under python3.8/3.10/3.11, one real-process EOF probe of `python -m text_adventure_tui_lib.game`, and `git show ff2878e` for checkpoint history.
Limits: no Ollama server exists in this environment — every LLM round-trip was observed through fake clients, so the *shape* of each call (prompt, temperature, format flag) is verified but real-server error types and latency are not. Probe04 (unbounded) hung; its questions were re-proven by probe05/06/07.

## Purpose

One file, `game.py`, is the entire application shell: process entry (module `__main__` + console script target), main menu, the per-turn orchestration loop that makes 1–3 Ollama round-trips per turn, the in-game slash commands, and save-file writing — verified (read: game.py:1-466).

## Public surface

| Symbol | Kind | Location | Notes |
|---|---|---|---|
| `main_menu()` | entry function | game.py:380-462 | target of both documented entry points; builds `ollama.Client` then loops menu — verified (read: game.py:380-397) |
| `game_loop(story_name, saved_state=None)` | entry function | game.py:233-377 | one play session; `return`/`break` both mean "back to menu" — verified (read: game.py:344,377) |
| `get_llm_options(narrative, gsm) -> (str, list[str])` | LLM call | game.py:122-165 | temperature 0.7, `format="json"`; returns rewritten narrative + ≤4 choices — verified (read: game.py:139-159) |
| `get_llm_story_continuation(narrative, choice, instructions) -> str` | LLM call | game.py:72-94 | temperature 0.5 — verified (read: game.py:86-90) |
| `get_player_intent(input, gsm) -> str` | LLM call | game.py:97-120 | temperature 0.2, returns lowercased keyword — verified (read: game.py:109-117) |
| `get_player_choice(choices, added_choices, gsm, em) -> (str, event_id\|None)` | input loop | game.py:168-199 | returns `("EVENT_TRIGGERED", id)` for event-sourced choices — verified (read: game.py:193-195) |
| `handle_command(cmd, gsm, em)` | command dispatch | game.py:202-215 | `/save`, `/debug`, `/force_event`, `/quit` — verified (read: game.py:208-215) |
| `save_game_state(gsm, em)` | persistence | game.py:218-230 | writes one timestamped JSON under `~/.text_adventure_tui_saves/` — verified (read: game.py:219-222) |
| `display_title`, `display_story`, `debug_print` | render helpers | game.py:48-68 | thin `rich` wrappers — verified (read: game.py:48-68) |
| module `__main__` block | entry | game.py:465-466 | `python -m text_adventure_tui_lib.game` — verified (read: game.py:465-466) |
| console script `text-adventure-tui` | entry | setup.py:40-43 | maps to `main_menu` — verified (read: setup.py:40-43) |

All of these are importable by any other module; nothing is underscore-private — verified (read: game.py:44-230). The package `__init__.py` is empty, so importing `text_adventure_tui_lib.game` has no side effects beyond module-level `rich`/`ollama` setup — verified (read: ledger DATA row; probe01 imported the module and printed `ollama_client = None`).

### Ways to start the game (question 1)

| Way | Source | Status on Python ≥3.12 | Status on 3.8–3.11 (the CI matrix) |
|---|---|---|---|
| `python -m text_adventure_tui_lib.game` | README.md:22,41; game.py:465-466 | reaches menu without an Ollama server (verified run: EOF probe got to `Prompt.ask` with no server); crashes with `EOFError` traceback on Ctrl-D (verified run) | **fails at compile time**: `SyntaxError: f-string expression part cannot include a backslash` at game.py:83 (verified run: `py_compile` under 3.8, 3.10, 3.11 — all three reject the file) |
| console script `text-adventure-tui` | setup.py:40-43 | maps to `main_menu`; on *this machine* the installed script instead calls `game_loop()` from a stale 0.1.1 site-packages copy whose `game.py` is a different, older program (verified run: `head /home/nick/.local/bin/text-adventure-tui` → `sys.exit(game_loop())`; site-packages `game.py` has `game_loop` at :555, `main_menu` at :805) | same, plus the install itself would fail to import |
| `from ...game import main_menu; main_menu()` | README.md:38 (verification snippet) | works (probe01 imported the module) | same SyntaxError at import |

So: **every documented entry point fails on every Python version the project's own CI matrix tests** (`.github/workflows/python-ci.yml:13-15` pins 3.8/3.9/3.10/3.11), because game.py:83's f-string `{'\n- '.join(instructions)}` needs PEP 701 (Python ≥3.12) — verified (run: py_compile ×3 interpreters). The flake8 step of CI would fail even earlier on those interpreters — inferred (because flake8 parses with the running interpreter's grammar, and the file does not parse). README.md:47 promises "a compatible Python version (3.7+)" — false; the real floor is 3.12 (also `list[str]` annotations at game.py:73,122 need ≥3.9, but the f-string fails first — verified run via tool-py38 probes and the 3.12 floor).

## Key data structures

### `ollama_client` (module global)
Shape: `None` or an `ollama.Client`. Created only inside `main_menu` (game.py:383, under `global` at :381). Dereferenced by exactly three functions: game.py:86, :110, :140 — verified (read: game.py:44,381,383,86,110,140).

**What happens if the LLM helpers run before `main_menu()` (question 2)** — verified (run: probe01):
- `get_llm_story_continuation` → `AttributeError('NoneType' object has no attribute 'chat')` is caught by its own except (game.py:92-94) → returns `"The path forward is hazy..."`. Silent, graceful.
- `get_player_intent` → same → returns `"unknown_intent"` (game.py:118-120). Silent, graceful.
- `get_llm_options` → the same `AttributeError` is caught at game.py:161, but the handler itself dereferences `raw_json_str` at :163 → **`UnboundLocalError` escapes the function**. The only helper that cannot survive a missing client is the one the loop calls first.
Tests never import `game.py` at all (verified run: grep over `tests/` imports — only `game_state_manager`, `data_structures`, `yaml_loader`, `event_manager`), so no test hits this today; any future test that calls these helpers without `main_menu` gets exactly the above.

### `narrative` (game_loop local, question 3)
One string threaded through the `while True` at game.py:276-377. Per iteration:
1. Top of loop: holds whatever the *previous* iteration left — the intro text on iteration 1 (game.py:264-274), then the previous turn's **action continuation** (game.py:326) or **event override** (game.py:319) — verified (run: probe03/probe05 `NARRATIVE_IN` logs: iteration 1 = intro text, every later iteration = `<<CONTINUATION...>>` or `<<OVERRIDE>>`, never the summary).
2. game.py:280 replaces it with the options-call's `narrative_summary` — this is the string displayed at :281.
3. Post-choice: game.py:318-319 (event override) or :322-327 (continuation) overwrites it again; :327 displays the continuation.

So the LLM is doing **two different jobs**: at :280 it *summarizes* (its output is shown but then discarded as context), at :322 it *continues* (its output is shown and becomes next turn's context). The summary the player reads at turn N is never the context at turn N+1 — verified (run: probe03, 25 iterations, panel order `[SUMMARY N][CONT N]` repeating, `NARRATIVE_IN[N+1] == CONT N`).

**LLM round-trips per turn** — verified (run: probe03 = 75 calls / 25 turns; probe05 path A/B; probe07):
| Turn shape | Calls | Sequence |
|---|---|---|
| normal | 3 | options(0.7) → intent(0.2) → continuation(0.5) |
| post-choice event overrides narrative (game.py:318) | 2 | options → intent; continuation skipped |
| player picked an event-sourced choice (`EVENT_TRIGGERED`, game.py:300-306) | 1 | options only; `continue` at :306 precedes the intent call at :312 |

### `llm_instructions` (list[str], question 5)
Created **fresh inside the loop** at game.py:284 — i.e., *after* the options call at :280 has already been sent. Its only producers: pre-choice `check_and_trigger_events` (:285-287, via `modify_prompt`, event_manager.py:123), the `EVENT_TRIGGERED` execution (:301-303), post-choice check (:313-315), checkpoints (:355). Its only consumer: `get_llm_story_continuation` at :322-324 (joined into the prompt at :82-83). Therefore:
- **No `modify_prompt` instruction is ever part of the choices prompt** — structurally impossible (created after the send) and confirmed: probe03/probe05 recorded 35+ options calls, `Important context to consider` present in **0** of them — verified (run).
- On turns where an event overrides the narrative (:318) the instructions are collected and then silently dropped: the continuation that would have carried them is skipped, and :284 empties the list before the next turn — verified (read: game.py:284,318-327; run: probe05 path B).
- Same for the `EVENT_TRIGGERED` path: `execute_event_actions` appends into the list at :301-303, then `continue` discards it — verified (read: game.py:300-306).
- Checkpoint `prompt_injection` (:355) is appended *after both* LLM calls of the current iteration → **never reaches any prompt**; verified (run: probe06a — 0 of 10 prompts contained the marker). The original implementation (commit ff2878e) injected checkpoints *before* building the prompt (verified run: `git show ff2878e:...game.py` lines 142-149 "Check for checkpoint injection" precedes the LLM call) — so the current behaviour is a regression introduced by the rewrite, not a never-implemented feature.

### Save file dict (question 9)
Shape written by `/save` (game.py:225-229): exactly `{"game_state": <GameState.__dict__>, "event_manager_state": {"triggered_event_ids": [...]}}` — verified (run: probe03 saved a real game; top-level keys `['event_manager_state', 'game_state']`, **no `narrative` key**).
Resume (game.py:237-251): `main_menu` passes the **whole dict** as `saved_state` (game.py:451); `game_loop` indexes `saved_state["game_state"][...]` and `saved_state["event_manager_state"]` (:243-250) — consistent, works — verified (run: probe06b fed that exact shape). Then :251: `narrative = saved_state.get("narrative", "Your story continues...")`. Since nothing ever writes `narrative`, **every resume starts with the placeholder as the LLM context**: probe06b recorded the first options prompt's situation line as literally `'Your story continues...'`, and the header showed the restored `Turn 5`. The player's actual last scene is unrecoverable; what they *see* on the resumed first turn is a fresh LLM summary invented from the placeholder (the literal placeholder is displayed only if the options call fails cleanly, because the fallback returns `current_narrative` — verified run: probe02 cases B/C/D). Additionally the `Player` is rebuilt fresh from YAML on resume (game.py:239-247 restores only flags/turn_count/current_location/turns_in_location): a save carrying inventory `SAVED_SWORD` resumed with prompt line `- Inventory: Empty` — verified (run: probe06b; same conclusion in sections/data.md "re-created from YAML on resume").

## Invariants

| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| `ollama_client` is non-None before any loop turn | game.py:383 runs before menu offers stories | any direct caller of the three LLM helpers (probe01 disproves safety) — verified (run) |
| `narrative` at top of iteration ≥2 is a continuation/override, never a summary | game.py:319,326 are the only writers after :280 | nothing; probe03/05 confirm — verified (run) |
| `llm_instructions` never reaches the choices prompt | game.py:284 (creation point) | story authors writing `modify_prompt` expecting it to steer choices — verified (run: 0/35+) |
| checkpoint `turn` N fires exactly once, at the end of the Nth completed turn | game.py:347 (increment) then :351-353 (equality test) | checkpoint authors; a `turn: 0` checkpoint can never fire, and after a resume only turns > saved `turn_count` can — verified (read: game_state_manager.py:55-56; run: probe06a/a2) |
| choices count is exactly 1–4, else fallback | game.py:156-157 raises, :161-165 catches | — verified (read) |
| turn header shows the pre-increment count (`Turn 0` first) | game.py:277 | new readers comparing header to checkpoint numbers — verified (run: probe06a shows `Turn 0` then `Turn 1`) |

## Dependencies out

| Target | Called at | Why |
|---|---|---|
| `ollama.Client.chat` (network, no timeout argument passed) | game.py:86-90, 110-114, 140-145 | the three LLM round-trips; model from `OLLAMA_MODEL`, host baked into client at :383 — verified (read) |
| `rich` Console/Prompt/Panel/Theme (module-level `console`, game.py:34) | throughout | all output; `Prompt.ask` reads stdin at :181, :424, :433, :447 — verified (read) |
| `event_manager.EventManager` (`check_and_trigger_events` :285,:313; `execute_event_actions` :213,:272,:301; `load_state` :250; `get_state` :227) | game.py as listed | trigger evaluation, action dispatch — verified (read) |
| `yaml_loader.load_story_and_player` | game.py:239, :254 | story+player construction on every session start *and* resume — verified (read); contract documented in sections/load.md |
| `game_state_manager.GameStateManager` | game.py:248, :260, and ~15 call sites in the loop | counters, flags, inventory, location — verified (read) |
| `story_manager.StoryManager.discover_stories` | game.py:397 | **re-run on every menu iteration** — verified (read: inside `while True` at :393) |
| `story_manager.Story` fields | game.py:352 (`story.checkpoints`), :264 (`initial_story_part`), :258 (`starting_location`) | — verified (read) |
| filesystem: `~/.text_adventure_tui_saves/` | game.py:219 (`mkdir`), :224 (write), :438-449 (glob+read) | save/resume — verified (read) |
| `sys.exit(1)` | game.py:386 | if `ollama.Client(...)` constructor raises — inferred (because `Client.__init__` only stores config, the branch is likely dead; not proven) |

## Dependencies in

| Caller | Location | What it expects |
|---|---|---|
| `__main__` block | game.py:465-466 | nothing; calls `main_menu()` |
| console script | setup.py:42 | `main_menu` importable from an installed package |
| README verification snippet | README.md:38 | import only |
| tests | none | no test imports `game.py` — verified (run: grep tests/) |
| neighbour sections | — | `event_manager.execute_event_actions(event_id, gsm, llm_instructions) -> dict` with keys `override_narrative`/`injected_narratives_pre`/`injected_narratives_post`/`added_choices` (game.py:273,290,294,301,305); `EventManager.get_state/load_state` round-trip (game.py:227,250); `GameStateManager.increment_turn` +1 (game_state_manager.py:55-56) — verified (read) |

## Side effects

| Effect | Location | Trigger condition | Reversible? |
|---|---|---|---|
| writes `~/.text_adventure_tui_saves/<story_id>_<timestamp>.json` | game.py:219-229 | player types `/save` | no delete/prune path exists — verified (read; sections/data.md agrees: "files accumulate, never pruned") |
| consumes stdin lines | game.py:181, :343, :376, :424, :433, :447 | every prompt | n/a |
| process exit via `sys.exit(1)` | game.py:386 | client constructor raises | — verified (read) |
| process exit via `SystemExit("Exiting game.")` | game.py:215 | `/quit` — propagates uncaught through both loops | — verified (read; run: probe06c) |
| toggles module global `DEBUG_MODE_ENABLED` | game.py:454 | menu toggle | yes (toggle back) |
| end-of-turn state mutation (turn/location counters, flags) | game.py:347-348 via GameStateManager | every iteration | only via resume — verified (read) |

## Error and edge behaviour

| Situation | What happens | Location |
|---|---|---|
| Ollama unreachable / chat() raises during `get_llm_options` | handler at :161 catches, then **crashes with `UnboundLocalError: raw_json_str` at :163**; the `"Look around./Check inventory./Wait./Leave."` fallback at :165 is NOT reached; the exception propagates through `game_loop`/`main_menu` (no try/except in either) and kills the process | game.py:163 — verified (run: probe02 case A, probe01) |
| chat() returns non-JSON, or JSON with 0 or >4 choices | clean fallback: returns `(current_narrative, ["Look around.", "Check inventory.", "Wait.", "Leave."])` | game.py:151-165 — verified (run: probe02 cases B, C, D) |
| continuation/intent calls fail (incl. `ollama_client is None`) | graceful strings `"The path forward is hazy..."` / `"unknown_intent"` | game.py:94, :120 — verified (run: probe01) |
| Ctrl-D / EOF at any `Prompt.ask` | `EOFError` traceback, uncaught | — verified (run: real `python -m` process with empty stdin) |
| Ctrl-C | `KeyboardInterrupt` uncaught — inferred (no signal handling anywhere in game.py:1-466) |
| `/save` with no story loaded | cannot happen from the menu; inside `game_loop` `get_story()` always set — inferred (from :221 using `get_story().id`) |
| save file missing a `game_state` subkey (hand-edited/older schema) | `KeyError`, unhandled, on resume | game.py:243-246 — verified (read; sections/data.md row "save file missing turns_in_location → KeyError") |
| `/force_event <missing-id>` | **silent**: live `execute_event_actions` returns a dict, `handle_command` ignores it; no message | game.py:212-213 + event_manager.py:260-272 — verified (run: probe06c printed nothing) |
| `/force_event <once-event-id>` | executes actions AND marks the event triggered (`triggered_event_ids` gains it) | event_manager.py:277-279 — verified (run: probe06c: inventory gained item, id recorded) |
| menu number out of range (e.g. `9` with 0 stories, `6` with 2) | digit passes `isdigit()`, matches no branch, **menu silently redisplays** (no "Invalid choice.") | game.py:426-460 — verified (run: probe06d) |
| non-digit menu input | `"Invalid choice."`, redisplay | game.py:461-462 — verified (run: probe06d) |
| invalid in-game choice (non-command, non-digit, out of range) | `"Invalid choice."`, re-lists choices | game.py:199 — verified (read) |

### Live vs dead `execute_event_actions` (question 8)
`event_manager.py` defines the method **twice**: lines 18-37 and lines 260-281. The class body executes top-down, so the **second definition (line 260) is live** — verified (run: probe06c printed `co_firstlineno == 260`; flake8 F811 flags it per the ledger). The dead first definition (18-37) differs behaviourally: on a missing event it *prints* `"DEBUG: Event '<id>' not found for force execution."` and returns `{}` instead of the structured dict, and on success it prints `"DEBUG: Forcing execution..."` and — importantly — **never marks `once` events as triggered** (the `once` bookkeeping at :277-279 exists only in the live version). It is unreachable code that preserves an older, chattier, once-ignoring semantics.
Also note `/force_event` passes a throwaway `[]` for instructions (game.py:213) and ignores the return dict — so a forced event's `modify_prompt` and `override_narrative` effects are discarded; only state mutations (items, flags, location, stats) land — verified (read: game.py:212-213; run: probe06c).

### `/quit` reachability
Reachable: `get_player_choice` lowercases input (game.py:181), any `/`-prefixed input goes to `handle_command` (:183-184), `/quit` raises `SystemExit` (:215) which no frame catches — verified (run: probe06c, including uppercase `/QUIT`). README.md:238's promise holds. The other three documented commands exist too (README.md:236-239 ↔ game.py:208-215) — verified (read).

### Menu arithmetic with zero stories (question 10)
With `available_stories == []` the menu *prints* "1. Toggle Debug Output" / "2. Quit" (game.py:420-422) but the dispatcher tests `len(available_stories)+1/+2/+3` = **1/2/3** (:428-460). Verified (run: probe06d, zero-story stub):
| User types | Printed label says | Actually dispatches to |
|---|---|---|
| `1` | Toggle Debug Output | **Resume Game** branch → "No saves found." (with empty save dir) |
| `2` | Quit | **Toggle Debug** → "Debug mode is now ON" |
| `3` | (nothing printed) | **Quit** — the only exit that works |
| `x` | — | "Invalid choice." |
| `9` | — | silent redisplay |
With the 2 shipped stories the numbers shift to 3=Resume, 4=Toggle, 5=Quit (formula at :416-418) — verified (read). `discover_stories()` runs on every menu iteration (:397 inside the :393 loop), so hot-plugging story files changes the numbering between iterations — verified (read).

### `break` vs `return` out of `game_loop` (question 11)
The `game_ended` path does `input(...)` then `break` (:343-344); the checkpoint `force_end_game` path does `input(...)` then `return` (:376-377). Both return `None` to `main_menu`'s call site (:435), which is inside `while True` → the menu redisplays and another story can be started. Equivalent for the caller; keeping the menu is the intended behaviour — verified (read: game.py:343-344,376-377,435; run: probe06a2 — `game_loop` returned `None` normally at a turn-2 checkpoint). Only `/quit` (SystemExit) and a crash skip the menu.

### Checkpoint semantics vs `increment_turn` (question 12)
`increment_turn` is `turn_count += 1` (game_state_manager.py:55-56) and runs at game.py:347 *before* the checkpoint test reads `get_turn_count()` (:351) and compares `==` (:353). A checkpoint declared at turn N therefore fires at the end of the iteration in which the count *becomes* N — the Nth completed player choice — verified (run: probe06a2, `turn: 2` ended the loop after exactly 2 iterations / 6 LLM calls). Consequences:
- `turn: 0` can never fire (count is 1 by test time) — verified (read + probe06a ran 3 turns with a turn-0 checkpoint, no effect).
- The `Turn N` header (:277) shows the *pre-increment* value, so the header reads one less than the checkpoint number that will end that same iteration (`Turn 1` header, checkpoint `turn: 2` ends it) — verified (run: probe06a2 output shows `Turn 0`, `Turn 1`, then conclusion).
- On resume, `turn_count` is restored (:244), so checkpoints are absolute against lifetime turns; any checkpoint ≤ the saved count is unreachable.
- Shipped content: whispers has checkpoint turns 15 (injection-only → dead, see above) and 25 (`force_end_game`, fired in probe03 at exactly iteration 25); clockwork has 10 and 15 — verified (read: `text_adventure_tui_lib/story_parts/whispers_of_the_salted_crypt_story_arc.yaml:20-28`, `.../the_clockwork_heist_story_arc.yaml:20-28`; run: probe03 ended at turn 25).

### `inject_narrative position: "pre"` (question 6)
In `event_manager._perform_actions`, `position == "pre"` routes text into `injected_pre` (event_manager.py:125-131), returned as `injected_narratives_pre`. `game_loop` displays those at :290-291 — i.e. **after** `display_story(narrative)` at :281. So "pre" does not mean "before the main narrative" on screen; it means "before the player's next choice". Actual panel order per turn: LLM summary → pre injections → [choice] → continuation/override → post injections — verified (read: game.py:281,290-291,330-331; run: probe03 panel order, where the pre-injection "You've been here for a while…" appears after each turn's summary). DEVELOPER_GUIDE.md:115 ("Add text before/after main narrative") is misleading for "before".

### Wasted LLM call on the override path (question 7)
`get_player_intent` runs unconditionally at game.py:312 on every choice-taking turn. When a post-choice event then overrides the narrative (:318), the loop makes **2 calls that turn (options + intent)** and skips the continuation — verified (run: probe05 path B). The intent keyword is passed into the post-choice trigger check (:313-315), so it is *consumed*; it is wasted only when no event in the story conditions on `player_intent`. Count of wasted calls per override turn: **1** (the intent call, whenever its keyword matches nothing), and **0** on turns where an intent-triggered event is exactly what causes the override — verified (read: game.py:312-315) plus the run evidence above.

## Lifecycle and concurrency

- Single process, single thread; no timers, threads, or async — verified (read: imports game.py:1-19).
- Two nested `while True` loops: menu (:393) and turn loop (:276). Menu iterates forever until Quit (`break` :460) or an exception; the turn loop until `break` :344, `return` :377, `SystemExit` :215, or crash — verified (read).
- `game_loop` is re-enterable across plays (menu calls it per story start/resume, :435, :451), but module globals (`ollama_client`, `DEBUG_MODE_ENABLED`, `console`) persist across plays within one process — verified (read: game.py:34,38,44,381-383). A second `main_menu()` call in the same process would just rebuild the client — inferred.
- `ollama.Client` is constructed once per `main_menu()` call (:383) and never re-created; changing `OLLAMA_HOST` later in the process has no effect — verified (read).
- No cleanup/atexit: save files are never pruned, no resource release on exit — verified (read: no such code in game.py).
- Shutdown paths: `break` → normal fall-off `main_menu` → interpreter exit; `/quit` → SystemExit with message; `sys.exit(1)` on client-constructor failure (:386). Exit code on `/quit` is the SystemExit string path (Python prints the message, exit status 1) — inferred (standard CPython semantics; message observed in probe06c).

## Configuration

| Knob | Default | Source | Read when | Change requires |
|---|---|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | env (game.py:36) | **import time**; consumed once at :383 | process restart — verified (read) |
| `OLLAMA_MODEL` | `phi4:latest` | env (game.py:37) | **import time**; on every LLM call (:87,:111,:141) | process restart — verified (read) |
| `DEBUG_MODE_ENABLED` | `False`, **hardcoded** (game.py:38) | not env | runtime, per `debug_print` (:48-50) | menu toggle only (:454); no env var exists — verified (read) |
| `SAVE_DIR_NAME` / `SAVE_GAME_PATH` | `.text_adventure_tui_saves` under `Path.home()` (game.py:39-40) | not configurable | import time | code change — verified (read) |
| LLM sampling temperatures | 0.7 / 0.2 / 0.5 (game.py:89,:113,:143) | hardcoded | per call | code change — verified (read) |

Because the env vars are read at import, `export OLLAMA_MODEL=…` *before* launching (as docs/customization.md:20-30 instructs) works; changing them mid-session does not — verified (read: module-level `os.environ.get`). No timeout, retry, or backoff is passed to any `chat()` call — verified (read: game.py:86-90,110-114,140-145).

## Extension points

- To change how choices are generated or add context to the choices prompt: `get_llm_options`, game.py:122-165 — but note instructions cannot reach it today without moving the `llm_instructions = []` creation (:284) above the :280 call.
- To add an in-game command: one `elif` in `handle_command`, game.py:208-215, plus a README line.
- To change turn structure (counters, checkpoint handling): the block game.py:346-377; checkpoint matching is plain `==` on `turn`.
- To change win/lose messaging: `flag_messages` handling game.py:356-369 and the `game_ended` block :334-344 (flags are set by events, not here).
- To add a new entry point or fix the console script: setup.py:40-43.
- First file a developer touching any of this opens: `text_adventure_tui_lib/game.py`.

## Tests

| Test file | What it actually asserts | Coverage notes |
|---|---|---|
| tests/test_game_engine.py:15-35 | a `player_action` event fires via EventManager | no game.py import — verified (run: grep) |
| tests/test_new_engine.py:36-45 | story loads; GameStateManager basics | no game.py import — verified (run: grep) |
| tests/test_game_basics.py:1 | placeholder | — verified (read: ledger) |

**Coverage of this section: zero.** No test imports `game.py`; menu, loop, commands, save, all three LLM helpers, and both entry points are untested — verified (run: grep over tests/; ledger's pytest run: 7 passed).

## Surprises

- **An Ollama outage does not fall back — it crashes the whole game with `UnboundLocalError`** (game.py:163), while the carefully written fallback choices one line later only cover parse/count failures — verified (run: probe02).
- **`modify_prompt` event actions can never influence the choices prompt** (created at :284 after the send at :280) and are dropped entirely on override and event-trigger turns — verified (run: 0/35+ prompts, probe03/05).
- **Checkpoint `prompt_injection` — documented in DEVELOPER_GUIDE.md:190-193 and shipped in both story arcs — never reaches any LLM prompt**; it worked in the original commit (ff2878e injected pre-call) and was lost in the rewrite — verified (run: probe06a; git show ff2878e).
- **`/save` then resume loses the scene**: the placeholder `"Your story continues..."` becomes the LLM context, and inventory/stats are rebuilt fresh from YAML — verified (run: probe03 + probe06b).
- **Zero-stories menu lies**: printed options 1/2 dispatch to Resume/Toggle, and Quit is the unprinted 3 — verified (run: probe06d).
- Every CI python (3.8–3.11) fails to even *compile* game.py:83 (f-string backslash needs 3.12), while README claims 3.7+ — verified (run: py_compile ×3).
- The `text-adventure-tui` command on this machine runs a **different, older program** (stale wheel's `game_loop`, story "short") — verified (run: inspected the installed script).
- `/force_event` ignores the event's `override_narrative` and `modify_prompt` (return value and instruction list discarded) and silently does nothing on unknown ids (the DEBUG prints exist only in the dead first definition) — verified (run: probe06c).
- The turn header says `Turn 0` on the first turn while checkpoints count the same turn as 1 — verified (run: probe06a/a2).
- A no-op-looking `has a line '- '`-style prompt check confirmed the *only* signal that matters is the literal `Important context to consider` block; everything else in the options prompt is template boilerplate — verified (run: probe03's per-call checks).

## Docs vs code

| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| Run with `python -m text_adventure_tui_lib.game` | README.md:22,41 | works on ≥3.12 only; SyntaxError 3.8–3.11 | partially true — verified (run) |
| "compatible Python version (3.7+)" | README.md:47 | floor is 3.12 (f-string PEP 701; `list[str]` needs 3.9) | false — verified (run) |
| CI matrix 3.8/3.9/3.10/3.11 | .github/workflows/python-ci.yml:13-15 | every matrix python fails to parse game.py; additionally 153 flake8 violations on 3.13 (ledger) | CI cannot be green — verified (run: py_compile) + ledger |
| In-game commands `/save /debug /quit /force_event` | README.md:236-239 | all four exist (game.py:208-215); `/quit` reachable | true — verified (run: probe06c) |
| "Use /save and /load commands during gameplay" | DEVELOPER_GUIDE.md:491 | no `/load` exists; resume is main-menu only | false — verified (read: game.py:208-215) |
| Checkpoint `prompt_injection: "Time is running short…"` example | DEVELOPER_GUIDE.md:190-193 | injection never reaches a prompt in current code | false (regression) — verified (run: probe06a) |
| `inject_narrative`: "Add text before/after main narrative" | DEVELOPER_GUIDE.md:115 | "pre" renders *after* the main narrative panel | misleading — verified (read: game.py:281 vs 290-291) |
| Set `OLLAMA_HOST`/`OLLAMA_MODEL` env vars | docs/architecture.md:66-67, docs/customization.md:7-45 | honoured, but read at import only | true with a restart caveat — verified (read) |
| Pull `llama3.1:8b` | README.md:20 | default model is `phi4:latest` (game.py:37); README never mentions it | inconsistent — verified (read) |
| Menu toggle enables "Game state information, Event trigger details…" | README.md "Debug Mode" section | toggle works; `debug_print` output depends on event_manager/other debug calls | partially verified (toggle: run probe06d) |
| Console script `text-adventure-tui` | setup.py:42 | points at `main_menu`, but this machine's installed script runs the stale wheel's `game_loop()` | environment caveat — verified (run) |

## Unknowns

- Which exception a *real* downed Ollama server raises through `ollama==0.2.1` (ConnectionError-shaped vs `ResponseError`) — needs a live Ollama server; the ULE crash is proven for *any* exception (probe02), only the type is unknown.
- Whether `format="json"` is honoured by the default `phi4:latest` on current Ollama, and real per-turn latency for 3 sequential round-trips — needs the server + model.
- Whether any `chat()` call can hang indefinitely (no timeout passed) — needs the ollama library's default timeout behaviour under a stalled server (not in game.py's control).
- Whether the stale 0.1.1 wheel behaviour reproduces on a clean `pip install .` of the current tree (expected: console script → `main_menu` per setup.py:42) — needs a clean venv install; this machine's site-packages is contaminated.
- Whether the menu's `discover_stories()` cost matters (re-run per iteration, plus 3 YAML reads per call per sections/load.md) — needs a large stories directory to observe.

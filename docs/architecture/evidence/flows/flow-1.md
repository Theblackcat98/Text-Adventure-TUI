# Text-Adventure-TUI: flow — FLOW-1 launch → story menu → first keystroke

Prefix: FLOW-1 · Sections touched: ENTRY, STRY, TOOL, LOAD (read-only support) · Commit: 7f349d1
Question it answers: What actually happens from launching `python -m text_adventure_tui_lib.game` (or the `text-adventure-tui` console script) until the story menu is rendered and the player can type a number?

Method: read of `game.py` (1-70, 233-240, 380-466), `story_manager.py` (1-72), `setup.py` (full); 9 probes under `/tmp/opencode/cdd-text-adventure-tui/flows/f1-*.out`, run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` (a stale 0.1.1 copy in `~/.local/lib/python3.13/site-packages/` shadows the repo). The menu itself needs no Ollama server, so everything from launch to Quit was exercised **live**; only `game_loop` internals are out of scope (FLOW-2).
Limits: no Ollama server exists here, so the `sys.exit(1)` client-constructor branch could only be traced statically; KeyboardInterrupt was injected via `timeout -s INT`, not a real tty Ctrl-C.

## Trigger

Three candidate starts; all of them end in `main_menu()` at `game.py:380` — except the one actually installed on this machine, which does not.

| Candidate | What runs first | Evidence |
|---|---|---|
| `python -m text_adventure_tui_lib.game` | The interpreter imports the package (`__init__.py` is 0 bytes — no side effects, verified run: `wc -c` → 0), then runpy executes `game.py` **as `__main__`**: module level `game.py:1-44` runs, then the guard `game.py:465-466` calls `main_menu()` | verified (read: game.py:465-466) + verified (run: f1-client.out — `game module file: .../Text-Adventure-TUI/text_adventure_tui_lib/game.py`, confirming PYTHONPATH wins over site-packages) |
| console script `text-adventure-tui` **as declared** | `setup.py:40-43` maps it to `text_adventure_tui_lib.game:main_menu`; setuptools generates a wrapper that imports `game` (module level runs) then calls `main_menu()` | verified (read: setup.py:40-43); declared behaviour only — see next row |
| console script `text-adventure-tui` **as installed here** | `~/.local/bin/text-adventure-tui` does `from text_adventure_tui_lib.game import game_loop` … `sys.exit(game_loop())` — the stale 0.1.1 wheel's entry point, a different, older program. Against the current tree, `game_loop()` with no args would pass `story_name=None` into `load_story_and_player` (game.py:233,239) and die in the loader's old-format branch (`yaml_loader.py:108-109`, per LOAD) | verified (run: `cat ~/.local/bin/text-adventure-tui`); loader consequence inferred (because story_name=None matches no arc file, and per sections/load.md a missing arc routes to the old branch whose empty case raises ValueError) |
| (`python -m text_adventure_tui_lib` alone) | Fails — the package has no `__main__.py` | verified (run: `ls text_adventure_tui_lib/` → no `__main__.py`) |

**Module-level code, in order** (`game.py:1-44`) — runs before any function, on *every* entry route: verified (read: game.py:1-44)
1. `game.py:1-19` — stdlib, `ollama`, `rich`, and the five sibling imports (`data_structures`, `event_manager`, `yaml_loader`, `game_state_manager`, `story_manager`) — none of which do work at import.
2. `game.py:22-34` — rich `Theme` + the module-global `console = Console(...)`.
3. `game.py:36-37` — `OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")`, `OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi4:latest")` — **captured at import time**; on this machine `OLLAMA_HOST` is already set in the environment (`0.0.0.0`), so the code default did not apply in probes — verified (run: f1-client.out).
4. `game.py:38-41` — `DEBUG_MODE_ENABLED = False` (hardcoded, no env), `SAVE_GAME_PATH = Path.home() / ".text_adventure_tui_saves"`, `GAME_TITLE`.
5. `game.py:44` — `ollama_client = None`.

Version caveat: on Python < 3.12 none of the above runs — `game.py:83`'s f-string backslash is a `SyntaxError` at compile time (verified run in ENTRY: `py_compile` under 3.8/3.10/3.11, cited from sections/entry.md). The flow below assumes ≥ 3.12.

## Hop-by-hop trace

| # | Hop | Location | State read | State written | External effect |
|---|---|---|---|---|---|
| 1 | Module import + `main_menu()` call | game.py:1-44, 465-466 → :380 | env `OLLAMA_HOST`, `OLLAMA_MODEL`, `Path.home()` | module globals: `console`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `DEBUG_MODE_ENABLED=False`, `SAVE_GAME_PATH`, `ollama_client=None` | none (verified run: f1-client.out — import produces no output) |
| 2 | Ollama client construction | game.py:382-386 (under `global` :381) | `OLLAMA_HOST` | **`ollama_client` = `ollama.Client` instance** (only writer in the program) | none — construction is offline; it only stores config. Verified (run: f1-client.out — `Client` built with no server running); network is touched only later, at `chat()` inside game_loop (FLOW-2) |
| 3 | `sys.exit(1)` guard | game.py:384-386 | — | — | process exit 1 — reachable only if the constructor raises; `Client.__init__` only stores config, so this is near-dead — inferred (because the offline construction succeeded and ENTRY's probe01 agrees; not proven impossible) |
| 4 | Path anchors + `StoryManager(...)` | game.py:389-391 | `__file__` | none (manager stores 2 Paths, stateless — story_manager.py:38-40) | none |
| 5 | Menu loop entered; `display_title()` | game.py:393-394 → 53-57 | `GAME_TITLE`, rich `console` | none | stdout: rich Panel "Terminal Text Adventure" (verified run: every f1-menu-*.out) |
| 6 | `discover_stories()` — **once per iteration, not once per program** | game.py:397 (inside `while True` :393) → story_manager.py:42-72 | `stories_path`; the N arc files | none persisted — fresh `StoryInfo` list per call | filesystem **reads**: top-level glob `*_story_arc.yaml` (story_manager.py:47, non-recursive — `*` cannot cross `/`), then `open` + `yaml.safe_load` per file (:49-50), id from filename stem (:53), `StoryInfo` with `.get` defaults (:55-65), sorted by title (:72). Cost: N arc opens+parses per redraw; LOAD measured 10 reads for 3 menu iterations + 1 game start with N=2 (cited from sections/load.md probe load-05); this flow's own 3-iteration probe printed 3 title panels (f1-menu-invalid.out) |
| 7 | Menu render | game.py:399-422 | `available_stories` (incl. `content_warnings`, `difficulty`, `tags`, `description`), `DEBUG_MODE_ENABLED` | none | stdout: story list (:401-414), then `N+1. Resume Game`, `N+2. Toggle Debug Output (ON/OFF)`, `N+3. Quit` (:416-418); with 0 stories the **mismatched** labels "1. Toggle Debug Output" / "2. Quit" (:420-422) |
| 8 | `Prompt.ask("Choose an option").strip()` | game.py:424 | stdin | none | stdout: prompt; stdin: one line consumed. This is the "player can type a number" moment |
| 9a | Digit 1..N → story select | game.py:428-435 | `available_stories[n-1]`, its `content_warnings` | none | stdout "Starting: \<title\>" (:430); if warnings exist (:431, both shipped stories have them — verified run: f1-menu-cw.out "Content warnings: theft, mild violence") print them (:432) and ask "Continue? (y/n)" default y (:433); a non-`y*` answer `continue`s to hop 5; otherwise **`game_loop(selected_story.id)` at :435** — FLOW-2's territory starts here (def at game.py:233). When game_loop returns (story end), control falls back into the `while True` → menu again — verified (read: game.py:435 inside :393 loop; ENTRY probe06a2 cited from sections/entry.md) |
| 9b | Digit N+1 → Resume | game.py:436-451 | `SAVE_GAME_PATH` | none | filesystem: `sorted(SAVE_GAME_PATH.glob("*.json"), key=os.path.getmtime, reverse=True)` (:438-440). Empty/missing dir → "No saves found." + `continue` (:441-443); else list saves (:444-446), `Prompt.ask("Select a save")` (:447), valid digit → `open` + `json.load` (:449-450) → **`game_loop(saved_data["game_state"]["current_story"]["id"], saved_data)`** (:451). The exact key chain `game_state` → `current_story` → `id` must exist or `KeyError` (uncaught). An invalid save selection (non-digit / out of range) falls out of :448's `if` with **no message** — silent redisplay (inferred from read: no `else` on :448 and no following branch consumes it) |
| 9c | Digit N+2 → Toggle debug | game.py:452-457 | `DEBUG_MODE_ENABLED` | **`DEBUG_MODE_ENABLED` flipped** (module global; persists across game sessions within the process; shown in menu label :417 and consumed by `debug_print` :48-50) | stdout "Debug mode is now ON/OFF" |
| 9d | Digit N+3 → Quit | game.py:458-460 → fall off `main_menu` | none | none | process exits, code 0 — verified (run: f1-menu-invalid.out `exit=0`) |
| 9e | Digit out of range (0, N+4, 9, …) | game.py:426-460 — passes `isdigit()` (:426), matches no branch (no `else` on the digit chain) | none | none | **nothing** — silent redisplay, no message. Verified (run: f1-menu-invalid.out — input `6` with 2 stories produced no output between two title panels). Note `"0".isdigit()` is `True` and `"-1".isdigit()` is `False` — verified (run: f1-isdigit.out) |
| 9f | Non-digit | game.py:461-462 | none | none | stdout "Invalid choice." → redisplay. Verified (run: f1-menu-invalid.out) |

## Diagram

```text
(a) python -m text_adventure_tui_lib.game      (b) text-adventure-tui
    runpy: pkg __init__ [0 bytes]                  setup.py:42 declares → game:main_menu
    → game.py executed as __main__                 ⚠ INSTALLED script here (~/.local/bin) calls
             │                                         game_loop() of the stale 0.1.1 wheel
             ▼
    game.py:1-34   imports, Theme, Console
    game.py:36-37  OLLAMA_HOST / OLLAMA_MODEL (env, import-time)
    game.py:38-41  DEBUG_MODE_ENABLED, SAVE_GAME_PATH, GAME_TITLE
    game.py:44     ollama_client = None
             │
    game.py:465-466  if __name__ == "__main__": main_menu()
             ▼
    game.py:382-386  ollama.Client(host=OLLAMA_HOST)      [except → print + sys.exit(1)]
             ▼                                          construction is offline-safe
    game.py:389-391  StoryManager(Path(__file__).parent/"story_parts", …/"events")
             ▼
    game.py:393  while True  ◄──────────────────────────────────────────────┐
             │                                                               │
    game.py:394  display_title() → game.py:53-57  stdout: title panel        │
             ▼                                                               │
    game.py:397  discover_stories() → story_manager.py:42-72  (per iteration!)│
        :47  glob "*_story_arc.yaml"  (top-level only)                        │
        :49-50  open + yaml.safe_load per arc   ── except Exception →         │
        :55-65  StoryInfo(.get defaults)            print + skip (:68-70)     │
        :72  sorted by title                                                  │
             ▼                                                               │
    game.py:399-422  render: stories 1..N, then N+1 Resume /                │
                     N+2 Toggle / N+3 Quit  — or the lying "1/2" if N==0    │
             ▼                                                               │
    game.py:424  Prompt.ask("Choose an option").strip()  ◄─ player input    │
             ▼                                                               │
    game.py:426-462  dispatch                                               │
        ├─ 1..N      :428-435 → warnings y/n (:431-434) → game_loop(id)       │
        │                                   (:435) ────────► FLOW-2           │
        ├─ N+1 Resume :436-451 → glob saves (:438-440) ─ empty→"No saves" ────┤
        │                            └→ json.load (:450) → game_loop(id,save) │
        ├─ N+2 Toggle :452-457 → DEBUG_MODE_ENABLED = not DEBUG_MODE_ENABLED  │
        ├─ N+3 Quit   :458-460 → break → process exit 0                       │
        ├─ digit, no branch :426-460 → silent redisplay ──────────────────────┤
        └─ non-digit  :461-462 → "Invalid choice." ───────────────────────────┘
```

## Decision branches

| Condition | Location | Branch taken | Consequence |
|---|---|---|---|
| N = `len(available_stories)` ≥ 1 | game.py:399 | story list rendered, fixed options = N+1/N+2/N+3 | with the 2 shipped stories (sorted by title): **1 = The Clockwork Heist, 2 = Whispers of the Salted Crypt, 3 = Resume, 4 = Toggle, 5 = Quit** — verified (run: f1-menu-cw.out — input `1` → "Starting: The Clockwork Heist") |
| N = 0 | game.py:419-422 | prints "No stories found!" + "1. Toggle Debug Output" + "2. Quit" — but the parser (:426-462) still tests 1/2/3 = Resume/Toggle/Quit | **printed labels are lies**: typed `1` (printed "Toggle") actually Resumes; typed `2` (printed "Quit") actually Toggles; Quit is the **unprinted `3`** — verified (run: f1-zerostub.out, stub copy with arcs removed: `1`→"No saves found.", `2`→"Debug mode is now ON", unprinted `3`→exit 0). ENTRY probe06d corroborates (cited from sections/entry.md) |
| Story has `content_warnings` | game.py:431-434 | print warnings + y/n prompt; non-`y*` → `continue` (menu), `y*` → game_loop | both shipped stories warn, so 1/2 always pass through the y/n gate — verified (run: f1-menu-cw.out — `n` returned to a fresh title panel) |
| Resume with 0 saves or missing save dir | game.py:438-443 | "No saves found." → menu | `Path.glob` on a **nonexistent** directory returns `[]`, it does **not** raise — verified (run: f1-glob.out — `dir exists: False`, `glob result: []`; f1-menu-resume.out — input `3` → "No saves found." → menu → `5` → exit 0) |
| Save selection valid digit | game.py:448-451 | json.load → game_loop with the save dict | requires the JSON key chain `game_state.current_story.id` (verified read: game.py:451); FLOW-6 owns the rest |
| Digit vs non-digit | game.py:426 vs :461 | digit → silent-or-dispatch; non-digit → "Invalid choice." | `" 5"` would be non-digit, but :424 `.strip()`s first, so leading/trailing spaces are harmless — verified (run: f1-isdigit.out `' 5'.isdigit()` → False, strip applied at :424 by read) |

## Error branches

| Failure | Location | Surfaced as | Recovery |
|---|---|---|---|
| `ollama.Client(...)` constructor raises | game.py:384-386 | rich "Ollama client init failed: …" + `sys.exit(1)` | none — process dies. Near-dead: construction verified offline-safe — verified (run: f1-client.out) + inferred (Client.__init__ stores config; ENTRY agrees it is likely dead) |
| **Any real Ollama outage** | not in this flow | nothing here — construction succeeds without a server; the failure detonates later, at the first `chat()` inside game_loop (ENTRY: `UnboundLocalError` at game.py:163, cited from sections/entry.md) | none — FLOW-2/3 territory |
| Malformed / undecodable arc YAML during discovery | story_manager.py:48, 68-70 | bare `print("Warning: Could not load story arc …")` — **bypasses rich entirely** (story_manager.py never imports rich, per STRY S11), story silently skipped, rest of menu fine | menu continues with fewer stories; numbering may shift between iterations since discovery re-runs per redraw — verified (read: game.py:397 inside :393) |
| `stories_path` missing entirely | story_manager.py:47 | glob over a missing dir → `[]` → "No stories found!" branch (game.py:419) | cannot happen with `Path(__file__).parent` anchoring unless the install is broken — verified (run: f1-glob.out for the glob semantics; STRY probe stry-01 corroborates) |
| Malformed save JSON | game.py:449-450 | `json.JSONDecodeError` — uncaught (no try in `main_menu` :380-462) | none — traceback, process dies — verified (read: no exception handling anywhere in game.py:380-466) |
| Save JSON valid but missing `game_state` / `current_story` / `id` | game.py:451 | `KeyError` — uncaught | none — traceback, process dies — verified (read: game.py:451) |
| EOF (Ctrl-D) at any `Prompt.ask` | game.py:424 (also :433, :447) | `EOFError` traceback through rich's `console.input` → builtin `input` — uncaught, exit 1 | none — verified (run: f1-eof.out — `EOFError: EOF when reading a line`, `exit=1`) |
| Ctrl-C / SIGINT at a prompt | game.py:424 | `KeyboardInterrupt` traceback — uncaught (no handler anywhere in game.py:1-466, per ENTRY) | none — verified (run: f1-ctrlc.out — `KeyboardInterrupt` via rich console.input; exit code 124 is the `timeout` wrapper's, not the game's — the child's own status under a real tty is an unknown below) |
| Python < 3.12 | import time | `SyntaxError` (f-string backslash, game.py:83) — the flow never starts | none — verified (run: ENTRY py_compile ×3, cited from sections/entry.md) |

## State mutations

Everything this flow changes, in the whole program:

- **`ollama_client`** (module global, game.py:44): `None` → `ollama.Client` instance, written exactly once per `main_menu()` call at game.py:383 under `global` (:381). Observable later by the three LLM helpers (:86, :110, :140) — the only writer in the codebase — verified (read: game.py:44, 381, 383; ENTRY confirms :86/:110/:140 are the only dereferences).
- **`DEBUG_MODE_ENABLED`** (module global, game.py:38): starts `False`; flipped at game.py:454 on menu option N+2. Observable in the menu label (:417) and by `debug_print` (:48-50); survives across game sessions within the process because `main_menu` is a single call frame looping internally — verified (read: game.py:38, 417, 454; run: f1-zerostub.out "Debug mode is now ON").
- Everything else is loop-local and discarded per iteration: the `StoryManager` (stateless — two Paths, story_manager.py:38-40), the `StoryInfo` list (fresh objects per `discover_stories`, story_manager.py:44-66), `choice`, `selected_story`, `saves`, `saved_data` — verified (read: story_manager.py:38-72, game.py:380-462).

**External effects:** stdout only, all through rich (`console` at game.py:34) — title panel, story list, prompts, "Invalid choice.", "No saves found.", "Debug mode is now ON" — except the discovery warning, which uses bare `print()` (story_manager.py:69). stdin: one line per `Prompt.ask` (:424, :433, :447). Filesystem: **reads only** — N arc YAMLs per menu redraw (:397 → story_manager.py:47-50), plus glob+read of save JSONs on Resume (:438-450). Nothing in this flow writes, creates, or deletes anything — verified (read: game.py:380-466 contains no `open(...,"w")`, no `mkdir`; the save-file `mkdir` at game.py:219 lives in `save_game_state`, reachable only from inside game_loop) — corroborated (run: all f1 probes left no new files).

## To change this flow

- **Fix the zero-story menu mismatch**: make the printed labels and the dispatcher agree. Minimal edit: special-case the empty list in the parser — at game.py:426-462, when `available_stories` is empty, test `1` → Toggle and `2` → Quit (matching what :420-422 prints) instead of reusing the N+1/N+2/N+3 offsets. The cleaner fix is to build a number→action map from the same list that renders :416-422.
- **Stop re-reading every story YAML on every redraw**: `story_manager.discover_stories()` at game.py:397 runs inside the `while True` at :393 (N open+parse per iteration; hot-plugging story files between iterations is the only behaviour lost by moving it). Either hoist the call above :393 (re-discover once after `game_loop` returns at :435/:451), or add a cache inside `StoryManager` (story_manager.py:42-72). At N=2 the cost is negligible (LOAD probe load-05: 10 reads for 3 iterations + 1 start); it is the first thing to cache if the story library grows.
- **Make the entry point match the declaration**: the repo's `setup.py:42` already says `main_menu`, but every installed artifact on this machine (stale 0.1.1 wheel in site-packages, `~/.local/bin/text-adventure-tui`, `dist/*.whl`) still wires `game_loop` — rebuild and reinstall (`python -m build` + `pip install .` in a clean venv) so the console script actually reaches `main_menu()`; a fresh install against the current tree is also the fix for the shadowing that forces `PYTHONPATH` on every probe.

## Unknowns

- **Whether `sys.exit(1)` at game.py:386 is reachable at all** — needs proof that `ollama.Client.__init__` can raise for some host value (offline construction succeeded, ENTRY calls it likely dead). Needs the ollama library's constructor source review or a fault-injection probe.
- **The child's real exit status and terminal behaviour on a genuine tty Ctrl-C** — f1-ctrlc proves the `KeyboardInterrupt` traceback is uncaught, but the observed 124 came from the `timeout` wrapper; needs an interactive session (or pty harness) to record it.
- **Whether a clean `pip install .` of the current tree yields a working `text-adventure-tui`** — expected yes per setup.py:42, but this machine cannot show it (site-packages is contaminated with 0.1.1; ENTRY lists it as an unknown too). Needs a clean venv.
- **Whether the per-iteration `discover_stories` cost matters at realistic library sizes** — negligible at N=2 (LOAD), untested beyond that. Needs a large `story_parts/` fixture.

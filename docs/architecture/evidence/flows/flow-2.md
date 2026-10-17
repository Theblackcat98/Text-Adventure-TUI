# Text-Adventure-TUI: flow — new-game prelude (menu pick → first turn prompt)

Prefix: FLOW-2 · Sections touched: ENTRY, LOAD, DATA, EVT, CONF
Question it answers: What happens between the player picking a story in the menu and the first turn's prompt appearing? Where does every piece of initial state come from?

Commit context: 7f349d1 (same tree as all Wave 1 reports).
Method: full read of `game.py:228-289`, `yaml_loader.py:1-142`, `data_structures.py:1-45`, `game_state_manager.py:1-56`, `event_manager.py:1-161,255-281`, `whispers_of_the_salted_crypt_story_events.yaml:1-30`, `whispers_of_the_salted_crypt_story_arc.yaml:1-47`, `01_intro.txt`; then one executed probe (`f2-prelude.py`) replaying game.py:252-274 verbatim against the real whispers YAML, plus error-path probes `f2-locale.py`/`f2-locale2.py` and the in-probe cases 7a/7b/7c. All probes run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` (stale 0.1.1 site-packages copy shadows the repo — probe printed the imported module path to prove it used the repo tree). Probe stdout: `/tmp/opencode/cdd-text-adventure-tui/flows/f2-prelude.out`.
Limits: no Ollama server exists in this environment, so the loop's first LLM call (game.py:280) could not be executed; everything after :277 is read-verified, with the call's failure/summary behaviour taken from ENTRY's run evidence. The `console.rule`/`display_story` rendering was not run (no tty value); the *string* "Turn 0" is proven by probe.

## Trigger

`main_menu` → `game_loop(story_name, saved_state=None)` at game.py:435 (new game) — verified (read: game.py:435, 451). This flow traces only the `else` branch taken when `saved_state` is falsy (game.py:237 → :252-274) — verified (read: game.py:237, 252). `saved_state=None` is what a fresh story pick passes — verified (read: game.py:435).

## Hop-by-hop trace

| # | Hop | Location | State read | State written | External effect |
|---|---|---|---|---|---|
| 1 | `display_title()` — reprints the game-title Panel banner (same banner the menu already showed) | game.py:234; def game.py:53-58 | none | none | rich Console output — verified (read: game.py:234, 53-58) |
| 2 | Anchor `stories_path = Path(__file__).parent / "story_parts"` — the package's *installed* location, not the CWD | game.py:235 | `__file__` | local var | none — verified (run: probe printed `<pkg>/story_parts`) |
| 3 | `load_story_and_player(story_name, stories_path)` (detail below) | game.py:254 → yaml_loader.py:32-93 | filesystem: arc YAML, `general_events.yaml`, `<story>_story_events.yaml` (3 files, all freshly parsed, no cache — LOAD) | builds `Story` + `Player` | 3 file reads (arc read once here; never inside this call a 4th time) — verified (read: yaml_loader.py:38-93) + (run: probe STEP 2) |
| 4 | `EventManager(story.events, console)` — dict-comprehension `{event.id: event}`; `triggered_event_ids = set()` | game.py:261 → event_manager.py:8-10 | the 16-Event list | `em.events` dict (16 entries), empty once-set | none — verified (read) + (run: probe printed all 16 keys in order) |
| 5 | `GameState(current_story, player, current_location=story.starting_location)` — flags/turn_count/turns_in_location take dataclass defaults | game.py:255-259 → data_structures.py:38-45 | `story.starting_location` = `"elian_study"` (arc:2) | `flags={}`, `turn_count=0`, `turns_in_location=0`, `current_location="elian_study"` | none — verified (read: data_structures.py:42-45) + (run: probe STEP 3) |
| 6 | `GameStateManager(game_state)` — stores the *reference*, no copy | game.py:260 → game_state_manager.py:5-6 | the GameState | none (wrap only) | none — verified (read: game_state_manager.py:5-6) |
| 7 | Intro read: `open(stories_path / story.initial_story_part).read()` → `narrative` | game.py:264-267 (`except FileNotFoundError` :268-269) | `initial_story_part` = `"01_intro.txt"` (arc:3); the file on disk (223 bytes) | `narrative` = file text | 1 file read, `open()` with **no `encoding=`** — verified (run: probe STEP 4, exact repr captured) |
| 8 | `execute_event_actions("story_start", gsm, [])` — forced bootstrap; the `MANUAL`+`game_start` trigger in the YAML is **never evaluated** on this path (forced execution skips `_evaluate_trigger` entirely) | game.py:272 → event_manager.py:260-281 (live) → `_perform_actions` :91-161 | `em.events["story_start"]`, `gsm` | flag write; `override_narrative` local; 1 instruction appended into the throwaway `[]` (see #9) | none — verified (run: probe STEP 5) |
| 9 | Once-marking check: `story_start` has no `options` key → `once` False → **not** added to `triggered_event_ids` (which stays empty) | event_manager.py:277-279 | `event.options` | none for whispers | none — verified (run: probe printed `set()` after) |
| 10 | Action `set_flag knows_elian_is_missing` → `flags["knows_elian_is_missing"] = True` | event_manager.py:106-107 → game_state_manager.py:17-18 | — | the only real state write of `story_start` | none — verified (run: probe STEP 5 `flags after`) |
| 11 | Action `change_location elian_study` → **no-op**: guard `if current_location != location` fails because GameState was already seeded from `starting_location` in hop 5 | event_manager.py:114-115 → game_state_manager.py:44-47 | `current_location` ("elian_study") | **none** (no write, no `turns_in_location` reset — moot at 0) | none — verified (read: game_state_manager.py:44-47) + (run: probe: location unchanged, turns_in_loc 0) |
| 12 | Action `override_narrative` → local var; returned under `"override_narrative"` in the **4-key** `_perform_actions` shape (no `modified_prompt_instructions` key) | event_manager.py:121-122, 156-161 | — | local `override_narrative` | none — verified (run: probe: `result keys` = 4, no prompt key) |
| 13 | Action `modify_prompt` → appends the study-guidance instruction into the *literal* `[]` passed at game.py:272; game.py binds neither the argument nor any return field carrying it → the list becomes garbage when the statement ends. **The instruction is dead on arrival.** | event_manager.py:123-124; game.py:272 | — | 1 element appended to an unreachable list | none — verified (run: probe STEP 5 printed the appended list, and its 4-key result shape) |
| 14 | `if story_start_results.get("override_narrative"): narrative = ...` — truthy → `narrative` (hop 7's intro text) is **unconditionally overwritten** | game.py:273-274 | result dict | `narrative` ← story_start override prose | none — verified (run: probe STEP 6: `narrative == intro file text? False`, `== override text? True`) |
| 15 | Loop entry: `while True` → `console.rule(f"Turn {game_state_manager.get_turn_count()}")` → renders **"Turn 0"** | game.py:276-277 | `turn_count` (0) | none | rich rule output — verified (read: game.py:276-277) + (run: probe end-state note `Turn 0`) |
| 16 | `get_llm_options(narrative, gsm)` — the story_start override is the *context*; what is displayed at :281 is the LLM's rewritten summary, not the override verbatim | game.py:280-281 | `narrative`, gsm (stats/inventory/flags/location) | `narrative` ← summary; `choices` ← ≤4 labels | 1st of 3 LLM round-trips — verified (read: game.py:280-281; summary-not-context: ENTRY, probe03) |
| 17 | `llm_instructions = []` — the list is created **here**, inside the loop, after the :280 send; it does not exist at any earlier point of this flow | game.py:284 | — | fresh empty list | none — verified (read: game.py:284) |

### Hop 3 detail — `load_story_and_player` (LOAD cross-section)

- Arc path `<stories_path>/<story_name>_story_arc.yaml` built at yaml_loader.py:38; existence check :41; parsed by `_load_yaml` (:8-11, bare `yaml.safe_load`, `open()` with no `encoding=`) — verified (read).
- `events_path = stories_path.parent / "events"` — **derived, hardcoded**, not a parameter (:48) — verified (read; LOAD documents the validator/loader divergence this causes).
- General events: `events/general_events.yaml` read and `extend`ed **first** (:52-56); story events `<story_name>_story_events.yaml` second (:59-63). Missing story-events file = silently fewer events, no warning (:60-63) — verified (read; LOAD).
- `Player` from the **arc file**: `stats=arc.get("initial_player_stats", {})`, `inventory=arc.get("initial_inventory", [])` (:66-69) — verified (run: probe → `{'health': 100, 'sanity': 100, 'knowledge': 10}`, `[]`, matching arc:7-11).
- `Story(id=story_name, ...)` at :75-79 — `id` is the filename stem; the arc never stores it — then **10 post-construction attribute writes** (:82-91): starting_location, initial_story_part, total_turns_estimate, description, checkpoints, tags, difficulty, content_warnings, author, version (each `.get` default mirrors the dataclass default; both are written redundantly — LOAD). All 10 confirmed for whispers by probe (estimate 25, difficulty "beginner", author "Text Adventure TUI Team", 2 checkpoints).
- Final event order (dict insertion order == evaluation order): `low_health_warning, inventory_full_warning, first_time_in_location, long_time_in_location, help_command, debug_info, story_start, find_elians_journal, read_journal_clue, find_hidden_key, arrive_at_bluffs, tide_recedes, enter_the_crypt, rescue_elian, end_story_success_heroic, end_story_success_cautious` — 16 events, general file first — verified (run: probe STEP 2; matches EVT's evt-p03).

### Hop 8 detail — which `execute_event_actions` is live

Two definitions: event_manager.py:18-36 and :260-281. The class body executes top-down, so the **second binding wins**: live = :260-281, dead = :18-36 — verified (run: `EventManager.execute_event_actions.__code__.co_firstlineno == 260` in probe) + (read: both defs) + flake8 F811 (ledger). Behavioural differences relevant here: the dead def printed `DEBUG: Event ... not found` and returned `{}`; the live def returns the structured 5-key dict and **marks `once` events at :277-279 before running actions** (the dead one never marked). For `story_start` (not `once`) the only difference reachable from this flow is silence on missing ids — verified (read: event_manager.py:18-36, 260-281; EVT evt-p01).

### Hop 7 detail — the intro file, verbatim

`story_parts/01_intro.txt` (whole file, 223 bytes incl. trailing `\n`) — verified (run: `cat` + probe repr):

> You find yourself in a dimly lit room. A single flickering candle on a rickety wooden table is the only source of light. The air is damp and smells of old parchment and something else... something metallic. What do you do?

It describes neither shipped story. `whispers_intro.txt` (a study scene matching this story) exists on disk but is referenced by nothing (CONF Q6) — verified (read: CONF).

## Diagram

```text
main_menu picks story ──►  game_loop(story_name, saved_state=None)      game.py:233
                                   │ saved_state falsy? ── yes ──►      game.py:237→:252
                                   ▼
display_title()                                                    game.py:234 → def :53-58   [banner]
stories_path = Path(__file__).parent/"story_parts"                 game.py:235                [anchor]
                                   ▼
load_story_and_player(story_name, stories_path)                    game.py:254 → yaml_loader.py:32
   ├─ arc file exists? ── no ──► _load_story_old_format            yaml_loader.py:38,41,45→:96-142
   ├─ parse arc (safe_load, no encoding=)                          yaml_loader.py:42 → :8-11
   ├─ extend general_events.yaml FIRST                             yaml_loader.py:52-56
   ├─ extend <story>_story_events.yaml                             yaml_loader.py:59-63
   ├─ Player(stats, inventory) from ARC                            yaml_loader.py:66-69  [arc:7-11]
   └─ Story(...) + 10 attribute writes                             yaml_loader.py:75-79, 82-91
                                   ▼
EventManager(story.events, console)   [dict comp; once-set empty]  game.py:261 → event_manager.py:8-10
                                   ▼
GameState(story, player, loc=story.starting_location)              game.py:255-259
   [defaults: flags={}, turn_count=0, turns_in_location=0]         data_structures.py:42-45
GameStateManager(game_state)  [reference, no copy]                 game.py:260 → game_state_manager.py:5-6
                                   ▼
narrative = open(story_parts/"01_intro.txt").read()                game.py:264-267
   └─ FileNotFoundError ──► narrative = "The story begins..."      game.py:268-269
                                   ▼
execute_event_actions("story_start", gsm, [])   ◄─ literal []      game.py:272
   ├─ LIVE def (2nd binding; :18-36 dead, F811)                    event_manager.py:260-281
   ├─ event missing? ──► 5-key dict, override None                 event_manager.py:268-275
   ├─ once? no options → not marked                                event_manager.py:277-279
   └─ _perform_actions                                             event_manager.py:91-161
        ├─ set_flag knows_elian_is_missing   → flags               event_manager.py:106-107 → gsm:17-18
        ├─ change_location elian_study       → NO-OP (== already)  event_manager.py:114-115 → gsm:44-47
        ├─ override_narrative                → local, returned     event_manager.py:121-122, :157
        └─ modify_prompt                     → appends into the    event_manager.py:123-124
│                                              literal [] of :272 → DISCARDED
                                   ▼
if override: narrative = override        [01_intro.txt never displayed]
                                                                      game.py:273-274
                                   ▼
while True → console.rule("Turn 0")      [turn_count still 0]        game.py:276-277
get_llm_options(narrative, gsm)          [override = LLM context;    game.py:280
                                          display = LLM summary]
llm_instructions = []                    [list born HERE, after the  game.py:284
                                          :280 send]
```

## Decision branches

| Condition | Location | Branch taken (whispers, new game) | Consequence |
|---|---|---|---|
| `saved_state` truthy? | game.py:237 | no → else block :252-274 | resume branch (:239-251) skipped entirely in this flow |
| `<name>_story_arc.yaml` exists? | yaml_loader.py:41 | yes (new format) | old-format fallback `_load_story_old_format` (:45, :96-142) never runs for shipped stories — verified (run: probe loaded via new branch) |
| `general_events.yaml` exists / truthy? | yaml_loader.py:53-55 | yes | 6 general events prepended; a falsy (empty) file would be *skipped silently* (:55 `if general_events_data:`) |
| `<story>_story_events.yaml` exists / truthy? | yaml_loader.py:60-62 | yes | 10 story events appended; missing file = silent fewer events |
| `open(intro)` raises FileNotFoundError? | game.py:268 | no (file exists) | fallback `"The story begins..."` not taken — verified (run: probe STEP 4) |
| `story_start_results.get("override_narrative")` truthy? | game.py:273 | yes (non-empty text) | `narrative` overwritten; **the intro file content never reaches the screen** — verified (run: probe STEP 6). Note truthiness: an override with `text: ""` would be falsy and the intro would survive — inferred (because `.get` returns the empty string, falsy in the `if`) |
| event id found? | event_manager.py:267-268 | yes | else the 5-key empty dict (see error branches) |
| `options.once`? | event_manager.py:278 | no (story_start has no `options`) | `triggered_event_ids` stays empty — verified (run: probe) |
| `current_location != "elian_study"`? | game_state_manager.py:45 | no | `change_location` writes nothing; `turns_in_location` not reset — verified (run: probe) |

## Error branches

| Failure | Location | Surfaced as | Recovery |
|---|---|---|---|
| Arc file present but **empty** (`yaml.safe_load` → `None`) | yaml_loader.py:42 → first arc `.get` at :67 | `AttributeError: 'NoneType' object has no attribute 'get'` — uncaught (no try in `game_loop` :233-377, none at the call site :435, none in `__main__` :465-466) → process traceback the instant the story is picked | none — verified (run: f2-prelude STEP 7c; LOAD pinned :67) |
| Events file malformed (top-level mapping, event missing `id`, YAML syntax error) | yaml_loader.py:22 (`KeyError: 'id'`), :11 (`yaml.YAMLError`) | raw exception, no filename/line context, uncaught | none — verified (read: yaml_loader.py:10-29) + (run: LOAD probes load-03-errors cases a-d) |
| Non-UTF-8 default locale (e.g. `LC_ALL=C`) | yaml_loader.py:54 → `_load_yaml` :10 (no `encoding=`); first offending bytes are the `•` bullets in `general_events.yaml:73-76` | `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 ...` uncaught → crash on story pick; the menu still *lists* stories because arc files are ASCII | none — verified (run: f2-locale2, traceback pinned yaml_loader.py:54 → :11) |
| Story YAML has **no `story_start` event** (or typo'd id) | event_manager.py:267-275 (**live** def) | 5-key dict, `override_narrative: None`; `game.py:273` falsy → intro text survives; **no message at all** (the chatty DEBUG print exists only in the dead def :26-29) | game starts from generic `01_intro.txt` (or `"The story begins..."`) — verified (run: f2-prelude STEP 7a with unknown id; live-def shape confirmed) |
| Intro file missing | game.py:268-269 | silent fallback `narrative = "The story begins..."` | none needed; player sees placeholder as LLM context — verified (run: f2-prelude STEP 7b) |
| Malformed action crashes `_perform_actions` mid-list | event_manager.py:102 (no try/except) | remaining actions skipped, exception propagates through :272 into `game_loop`, process dies | none (EVT verified this generally; whispers' `story_start` actions are well-formed — verified run: STEP 5 clean) |

## State mutations

Every piece of initial state and where it comes from, in write order (all confirmed by probe unless tagged):

1. `Player.stats = {'health': 100, 'sanity': 100, 'knowledge': 10}` — from arc:8-11, written at yaml_loader.py:67 — verified (run).
2. `Player.inventory = []` — arc:7, yaml_loader.py:68 — verified (run).
3. `Story.id = "whispers_of_the_salted_crypt"` (filename stem, game arg), `.title`, `.events` (16 Events) — yaml_loader.py:75-79 — verified (run).
4. Ten `Story` metadata attributes — yaml_loader.py:82-91 from arc:1-47 (estimate 25, difficulty "beginner", author, version, tags, warnings, description, 2 checkpoints) — verified (run).
5. `em.events` dict of 16 (general first), `em.triggered_event_ids = set()` — event_manager.py:8-9 — verified (run).
6. `GameState`: `current_location = "elian_study"` (game.py:258 from arc:2), `flags = {}`, `turn_count = 0`, `turns_in_location = 0` (dataclass defaults, data_structures.py:42-45) — verified (run).
7. `flags["knows_elian_is_missing"] = True` — story_start `set_flag`, event_manager.py:106-107 → game_state_manager.py:18. **The only durable write of the whole prelude's forced event** — verified (run).
8. `change_location elian_study` — **no write** (guard, game_state_manager.py:44-47) — verified (run).
9. `modify_prompt` instruction — appended into the literal `[]` at game.py:272; the list is not bound by game.py and is absent from the 4-key return dict (event_manager.py:156-161) → unreachable garbage. **This is where the story's "guide the player to the desk/bookshelf/map" instruction goes to die** — verified (run: probe printed the populated throwaway list).
10. `narrative` local: intro text (:267) → override prose (:274). Observable by the loop at :280 — verified (run).
11. NOT written: `turn_count`, `turns_in_location`, inventory, `triggered_event_ids` (story_start not `once`), and `llm_instructions` does not exist until game.py:284 — verified (run + read).

Observability: `flags`/`current_location` are read by every subsequent trigger evaluation (`_evaluate_trigger`), stats/inventory by the options prompt build (game.py:127-137) and `/debug`; `narrative` is consumed once at :280 then replaced by the LLM summary — verified (read) + (run: ENTRY probe03).

End state — what the player sees on turn 1: header rule **"Turn 0"** (game.py:277, probe), then at :281 whatever `get_llm_options` returned. Three sub-cases, none of which is the literal override text except the parse-failure fallback: healthy server → the model's rewritten summary of the override (ENTRY: summary shown, context discarded); clean parse failure (0/>4 choices) → `current_narrative` fallback at game.py:165, i.e. the override verbatim (ENTRY, probe02 cases B-D); connection failure → `UnboundLocalError: raw_json_str` at game.py:163 kills the process before anything displays (ENTRY, probe02 case A — the environment this repo is developed in). The intro .txt reaches the screen in **no** sub-case — verified (run: probe STEP 6) + (read: game.py:273-274; ENTRY for the LLM sub-cases).

## To change this flow

- To change the opening scene text for Whispers: edit `events/whispers_of_the_salted_crypt_story_events.yaml:13-20` (the `story_start` `override_narrative`). Editing `story_parts/01_intro.txt` has **no effect** on this story — it is read at game.py:264-267 and unconditionally discarded at :273-274; it only matters if `story_start` were removed/broken (then the generic dimly-lit-room text becomes the opening).
- To make `story_start`'s `modify_prompt` guidance actually reach the LLM: replace the literal `[]` at game.py:272 with a named list (e.g. `llm_instructions = []` created before :272) **and** move the re-creation at game.py:284 out of the loop (or merge into it) — today the instruction is appended to an object no one references, and even a bound list would be wiped by :284 before the continuation at :322-324 could use it on turn 1.
- To make the opening `change_location` meaningful (reset `turns_in_location`, or move starting-location logic into the event layer): drop `current_location=story.starting_location` from the `GameState(...)` call at game.py:258 so the guard at game_state_manager.py:44-47 stops swallowing `story_start`'s `change_location` — as written, the hop is a provable no-op for every story whose arc `starting_location` matches its `story_start` (both shipped stories).

## Surprises

- **The intro file is dead content in the live flow**: read, then overwritten before ever being displayed; `01_intro.txt` describes a room from neither story, while the matching `whispers_intro.txt` sits orphaned on disk (CONF Q6) — verified (run: probe STEP 6) — verified (read: CONF).
- **The initial location comes from two places that agree by luck**: `GameState` is seeded from arc `starting_location` (game.py:258), so `story_start`'s `change_location` — the action an author would expect to place the player — is a no-op (game_state_manager.py:45). If an author changes one but not the other, the event silently wins/loses depending on the guard — verified (run).
- **The prelude's only durable event effect is one boolean** (`knows_elian_is_missing`); the narrative override and the prompt guidance are locals/throwaways — verified (run: probe STEP 5 state diff).
- The live `execute_event_actions` marks `once` events *before* running actions (:277-279) — irrelevant for `story_start` (not once) but the same call path is shared with `/force_event` where it permanently consumes events (EVT) — verified (read + EVT probes).
- Every crash in this prelude is process-fatal: there is no try/except between the loader and `__main__` except the two narrow `FileNotFoundError`/`StopIteration` handlers; a story that validates in the menu (arc-only checks, story_manager.py) can still kill the game at pick time (empty arc, bad events file, non-UTF-8 locale) — verified (run: STEPS 7a-7c + f2-locale2) + (read: game.py:233-377 has no try).

## Unknowns

- What the player actually reads on turn 1 under a healthy Ollama server — the LLM's summary of the `story_start` override could paraphrase or mangle the scene; needs a live `phi4:latest` (ENTRY documented only the no-server crash path).
- Whether the `change_location` no-op in `story_start` is intended (author may believe the event places the player) or vestigial — needs author intent.
- Whether the UnicodeDecodeError path bites real users (Windows legacy code pages, PEP 540 UTF-8 mode interactions) — needs a Windows run (LOAD flagged the same unknown).
- Whether any real-world story file legitimately lacks `story_start` and plays from the generic intro — the 5-key empty-result path is proven (run), but no shipped/generated story hits it (`story_tool create` templates include one, CONF/STRY); needs user-authored stories to survey.

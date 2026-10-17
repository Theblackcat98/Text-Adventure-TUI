# Text-Adventure-TUI: EVT — Trigger evaluation and action dispatch

Prefix: EVT · Commit: `7f349d1` (2025-07-22) · Depth: deep
Scope (read fully): `text_adventure_tui_lib/event_manager.py` (281).
Read for promised behaviour: `DEVELOPER_GUIDE.md` (66-121, 330-386, 456-541), `README.md` (80-140).
Read as neighbours, not analysed: `game.py` (466), `yaml_loader.py` (142), `game_state_manager.py` (56), `data_structures.py` (45).
Content read to judge the engine: `events/general_events.yaml` (91), `events/whispers_of_the_salted_crypt_story_events.yaml` (269), `events/the_clockwork_heist_story_events.yaml` (action lines only), `story_parts/Whispers_of_the_Salted_Crypt/{game_setup,chapter1_study,chapter2_coast,chapter3_crypt}.yaml` (action/condition lines only).

Method: full read + grep + 19 runnable probes `probe/evt-p01-deadcode.py` … `probe/evt-p19-bare-endgame-and-yaml-shapes.py` (p01-p13 inherited from an interrupted earlier pass, re-read and re-run; p14-p19 added). All probes run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` because a stale 0.1.1 copy in `~/.local/lib/python3.13/site-packages/` shadows the repo (ledger: Environment notes). Baseline `pytest` → 7 passed (ledger). `grep -rn priority text_adventure_tui_lib/` → no matches (exit 1).

Limits: no Ollama server in this environment, so `player_intent` values in real play are unknown and the live loop was simulated by calling `EventManager` directly with the same argument shapes `game.py` uses. The dist/ wheel's `event_manager.py` was not unpacked.

---

## Purpose

Evaluate YAML-declared trigger conditions against game state and player input each pass, and dispatch the matching events' YAML-declared actions as state mutations, narrative injections, choice additions, and game-end flags — `verified (read: text_adventure_tui_lib/event_manager.py:38-161)`.

## Public surface

| Symbol | Kind | Location | Notes |
|---|---|---|---|
| `EventManager(events, console_instance)` | constructor | `event_manager.py:7-10` | Builds `{event.id: event}` dict; keeps the rich Console it prints to |
| `check_and_trigger_events(gsm, player_input_text, llm_prompt_instructions, player_intent="")` | method, the per-pass evaluator | `event_manager.py:38-89` | Called twice per turn by `game.py:285` and `game.py:313` |
| `execute_event_actions(event_id, gsm, llm_prompt_instructions)` | method, forced execution | `event_manager.py:260-281` (live) and `event_manager.py:18-36` (dead, shadowed — see F811 below) | Called from `game.py:213, 272, 301` |
| `get_state()` / `load_state(data)` | save/resume pair | `event_manager.py:12-16` | Persists only `triggered_event_ids` |
| `_perform_actions(event, gsm, llm_prompt_instructions)` | private dispatcher | `event_manager.py:91-161` | One branch per action type; no try/except |
| `_evaluate_trigger(trigger_config, gsm, player_input_text, player_intent)` | private condition evaluator | `event_manager.py:163-258` | Hardcoded if/elif chain; 12 condition types |

Everything else in the module is private by convention; there is no `__all__` — `verified (read: event_manager.py:1-281)`.

## Key data structures

### `self.events: dict[str, Event]`
Built at `event_manager.py:8` from the flat list `Story.events` — `verified (read: data_structures.py:24)` — which `yaml_loader.py:51-63` fills **general events first, then story events**, each file in YAML order — `verified (read: yaml_loader.py:51-63)`. Never mutated after construction. Read at `event_manager.py:24, 50, 267`.

### `self.triggered_event_ids: set[str]`
Once-guard. Written at `event_manager.py:78` (after a successful natural firing of a `once` event) and `event_manager.py:278-279` (in the live forced path, **before** actions run). Saved/loaded via `get_state`/`load_state` (`event_manager.py:12-16`), wired into `/save` at `game.py:227` and resume at `game.py:250` — `verified (read: all cited lines)`.

### Return dicts (two different shapes)
- `check_and_trigger_events` → 5 keys incl. `modified_prompt_instructions` (`event_manager.py:83-89`).
- `_perform_actions` → 4 keys, no `modified_prompt_instructions` (`event_manager.py:156-161`).
- Live `execute_event_actions`, event **not found** → 5 keys (`event_manager.py:269-275`); event found → the 4-key `_perform_actions` shape (via `:281`). Dead definition returned `{}` on not-found (`:30`). Callers only use `.get("override_narrative")` (`game.py:273, 305`), so the asymmetry is invisible today — `verified (run: probe evt-p17 part C)`.

## Invariants

| Rule | Enforced where | Or merely assumed by |
|---|---|---|
| Event ids are unique | **nowhere**; dict silently keeps last duplicate at first insertion position | `event_manager.py:8`; verified (run: probe evt-p08 part D: `[dup, other, dup]` → keys `['dup','other']`, story copy wins, general copy unreachable). No duplicate ids in shipped YAML — verified (run: probe evt-p03: 16 YAML events → 16 dict entries) |
| `once` events fire at most once per manager lifetime | `event_manager.py:51-55` (skip), `:77-78` (mark) — but forced path marks at `:277-279` with no guard against double-forcing | verified (run: probe evt-p06 #2) |
| An override narrative ends the evaluation pass | `event_manager.py:80-81` (`break` only when an override was produced) | verified (run: probe evt-p08 B/C) |
| Evaluation order = YAML order (general file, then story file) | insertion order of the dict at `event_manager.py:8` | verified (run: probe evt-p03) |
| Earlier events' state mutations are visible to later events in the same pass | nothing enforces it; it is a consequence of in-place mutation + `:50` iteration order | verified (run: probes evt-p08 A, evt-p11 4b/5b) |
| Unknown condition types evaluate to False | no `else` branch after `event_manager.py:250`; `met` keeps its `False` initialiser from `:184`, appended at `:252` | verified (run: probes evt-p04, evt-p12 B) |
| `game_ended` flag is only ever set by `end_game` actions | `event_manager.py:152-153` | read by `game.py:334` |

## F811: the two `execute_event_actions` definitions (assigned question 1)

`flake8` reports `F811 redefinition of unused 'execute_event_actions' from line 18` (ledger). In a Python class body the **second** binding wins, so the definition at `event_manager.py:260-281` is live and the one at `:18-36` is dead code.

`verified (run: probe evt-p01-deadcode.py)`:
```
live firstlineno : 260
has DEBUG print  : False
marks once event : True
```

| Difference | Dead def (`:18-36`) | Live def (`:260-281`) |
|---|---|---|
| DEBUG console output | prints `DEBUG: Event … not found` (`:26-29`) and `DEBUG: Forcing execution …` (`:32-35`) through `self.console` | silent |
| Not-found return | `{}` (`:30`) | full 5-key dict with `override_narrative: None` (`:269-275`) |
| `once` tracking | does **not** mark the event as triggered | marks `once` events at `:277-279` **before** running actions |

All three call sites get the live behaviour: `/force_event` → `game.py:213`; `story_start` bootstrap → `game.py:272`; `trigger:`-choice path → `game.py:301` — `verified (read: game.py:213, 272, 301)`. The behavioural consequence of the shadowing: **the live def permanently consumes a `once` event on forced execution, the dead def did not** (see question 4). Note the DEBUG prints that remain in the live class are the ones at `:60-62` in `check_and_trigger_events`, which are *not* gated by `game.py`'s `DEBUG_MODE_ENABLED` (that flag only gates `debug_print` in `game.py:48-50`) — every auto-triggered event prints a green `DEBUG: Event … triggered!` line to the player's console in normal play — `verified (run: probe evt-p18: emitted "DEBUG: Event 'dbg' triggered!\n")`.

## Duplicate ids, insertion order, evaluation order (question 2)

- `{event.id: event}` at `event_manager.py:8`: **the later event in the list wins** (dict value overwritten), but keeps the **first** insertion position — `verified (run: probe evt-p08 D)`.
- List order comes from `yaml_loader.py:51-63`: `general_events.yaml` extended first, then `<story>_story_events.yaml` — `verified (read: yaml_loader.py:51-63)`.
- `check_and_trigger_events` iterates `self.events.items()` at `event_manager.py:50`, so **dict insertion order decides evaluation order** — `verified (read: event_manager.py:50)`.

Actual evaluation order for `whispers_of_the_salted_crypt` — `verified (run: probe evt-p03)`:
```
 1 low_health_warning        9  read_journal_clue
 2 inventory_full_warning   10  find_hidden_key
 3 first_time_in_location   11  arrive_at_bluffs
 4 long_time_in_location    12  tide_recedes
 5 help_command             13  enter_the_crypt
 6 debug_info               14  rescue_elian
 7 story_start              15  end_story_success_heroic
 8 find_elians_journal      16  end_story_success_cautious
```

## One pass can fire many events; break-on-override; order dependence (question 3)

`event_manager.py:80-81` breaks **only** when an override narrative was produced, so any number of non-override events fire in one pass and all their `set_flag`/`change_location`/`remove_item` take effect — `verified (run: probe evt-p08 B: three chained events set flags a→b→c and inject pre+post in a single pass)`. A mid-pass override stops evaluation of everything after it — `verified (run: probe evt-p08 C)`; and it also stops evaluation of an event whose conditions *just became true* — `verified (run: probe evt-p10 #1: enter_the_crypt's change_location makes rescue_elian's location condition true, but the break at `:80-81` prevents rescue_elian from ever being evaluated in that pass)`.

The pass is order-dependent because each event's actions mutate the same state its successors' conditions read:

- Shipped-YAML proof A (flag across turns): `read_journal_clue` sets `knows_about_bluffs` (`whispers…yaml:65-66`); `find_hidden_key` requires `flag_set: knows_about_bluffs` (`whispers…yaml:88-89`) and can therefore never fire before it — `verified (read: whispers…yaml:65-66, 88-89)`.
- Shipped-YAML proof B (same pass, location): `arrive_at_bluffs` runs `change_location: saltstone_bluffs` (`whispers…yaml:119-120`); `tide_recedes` later in the dict tests `location == saltstone_bluffs` (`whispers…yaml:137-138`). With the turn counter neutralised, one input fires both in one pass; reversing the list order breaks it — `verified (run: probes evt-p10 #4, evt-p11 4b)`. (In the shipped file `tide_recedes` is additionally blocked because `change_location` resets `turns_in_location` to 0 via `game_state_manager.py:44-47` — `verified (run: probe evt-p10 #3)`.)
- Shipped-YAML proof C (same pass, item; override stripped): `find_elians_journal` + `read_journal_clue` (whose `inventory_has` is `whispers…yaml:60-61`) both fire for one input in `[find, read]` order; in `[read, find]` order only `find` fires — `verified (run: probe evt-p11 5b)`. The only variable was dict insertion order (`event_manager.py:8`).

## `once` consumption by the forced paths (question 4)

- Natural path: skip if already triggered (`event_manager.py:51-55`), mark **after** a successful firing (`:77-78`).
- Forced path (live def): marks **before** running actions (`event_manager.py:277-279`).

Consequences — `verified (run: probes evt-p06 #1/#2, evt-p13 B, evt-p09 C)`:
1. `/force_event find_elians_journal` (`game.py:213`) runs the actions *and* marks the event; the later natural "search desk" pass returns no override — the journal prose can never reach the player through normal play, and the state mutations of the forced run happened without any narrative.
2. A `trigger:`-labelled choice (`game.py:301`) consumes the target event's single firing. With `action: 'trigger:end_story_success_heroic'` the forced run bypasses the `player_action` condition at `whispers…yaml:227-228` entirely and fires the ending directly — `verified (run: probe evt-p09 C final part)`.
3. Double-forcing is not idempotency-guarded, but action re-runs are mostly harmless because `set_flag`/`add_item` are idempotent (`game_state_manager.py:17-18, 27-29`).
4. Non-`once` events are unaffected by forcing (`verified (run: probe evt-p06 #3)`).

## Condition-type catalogue: implemented vs documented (question 5)

Implemented in the if/elif chain — `verified (read: event_manager.py:185-250)`:

| Condition type | Engine lines | Docs |
|---|---|---|
| `location` | `:185-186` | DEVELOPER_GUIDE.md:90, README.md:111 |
| `flag_set` | `:187-188` | :95, :112 |
| `flag_not_set` | `:189-190` | :95, :112 |
| `player_action_keyword` | `:191-197` | :101, :113 |
| `player_intent` | `:198-199` | :102, :114 |
| `player_action` | `:200-201` | :103, :115 |
| `inventory_has` | `:202-203` | :96, :116 |
| `inventory_not_has` | `:204-205` | :96, :116 |
| `game_start` | `:206-207` | :98, :120 |
| `turn_count_in_location` | `:208-221` | :91, :117 |
| `turn_count_global` | `:222-235` | :92, :118 |
| `stat_check` | `:236-250` | :97, :119 |

Implemented and documented sets match exactly (12 = 12) — `verified (read: DEVELOPER_GUIDE.md:89-103, README.md:110-120)`.

`flag_is_set` (the misspelling) appears 3× in the old-format chapter files — `verified (run: grep -n flag_is_set)` at `chapter1_study.yaml:67`, `chapter2_coast.yaml:10`, `chapter3_crypt.yaml:12`. Runtime effect of the unknown type: `met` keeps its `False` initialiser from `event_manager.py:184`; the chain has no `else` and emits nothing; the `False` is appended at `:252`. Under `AND` the event can never fire; under `OR` it just wastes a slot — `verified (run: probes evt-p04 "UNKNOWN flag_is_set → False", evt-p12 B: `flag_is_set` with the flag SET → False, silently)`. `find_hidden_key` is therefore dead in the old-format load path (capitalised id → `yaml_loader.py:96` fallback) — `verified (run: probe evt-p13 C: whole old-format story, all-real conditions, empty input → nothing fired)`.

Related silent-False traps — `verified (run: probe evt-p04)`: `inventory_has` written with `item_id:` instead of `value:` → False (the condition reads only `condition.get("value")` at `:203`); any mode other than `AND`/`OR` after `.upper()` (`:171`) returns False at `:258` even with all conditions met ("XOR" → False); `trigger_config = None` raises `AttributeError` (no guard at `:170`).

## `player_action_keyword`: case-insensitive substring (question 6)

`event_manager.py:194-197` tests `str(keyword).lower() in player_input_text.lower()` — pure substring, no word boundaries. `game.py:181` lowercases typed input, but the string that actually reaches `check_and_trigger_events` at `game.py:313` is the raw LLM choice label (`game.py:190`) or an added-choice action string (`game.py:197`); both sides are lowercased at `:195` anyway.

- `keywords: ["Search Desk"]` still matches "search desk", "Search Desk", "I carefully search desk drawer" — `verified (run: probe evt-p05)`.
- But **not** "I carefully search the desk" (intervening word breaks the substring) — `verified (run: probe evt-p05)`.
- Short keywords false-positive on substrings: with `general_events.yaml:26`'s `keywords: ["take", "pick up", "grab", "get"]`, inputs containing "for**get**", "tar**get**", "bud**get**", "Let's **get** going" all fire `inventory_full_warning` ("Your hands are full…", `general_events.yaml:28-30`) — `verified (run: probe evt-p05)`. The event is not `once`, so it re-fires on every matching input.
- Empty `keywords` list → False (`:192-194` guard) — `verified (run: probe evt-p05)`.

## `player_action` exact match and the shipped ending chain (question 7)

`event_manager.py:200-201` requires `player_input_text.lower() == condition_value.lower()` — the whole input, exact after case-folding. Non-string `value` (int/None from YAML) raises `AttributeError` — `verified (run: probe evt-p05)`.

The chain the shipped endings rely on (`whispers…yaml:220-268`):
1. `rescue_elian` fires and its `present_choices` (`whispers…yaml:211-217`) appends two choices with `action:` values `end_story_success_heroic` / `end_story_success_cautious` (`event_manager.py:139-147`).
2. For the endings to be selectable, those choices must be in the menu. `game.py` reads `added_choices` **only** from the pre-choice pass result (`game.py:294`), i.e. from the `check_and_trigger_events` call at `game.py:285-287`, whose `player_input_text` is `""`. `rescue_elian` needs a `player_action_keyword` match (`whispers…yaml:192-193`), which can never be satisfied by empty input, so it can only ever fire in the **post-choice** pass (`game.py:313-315`) — whose `added_choices` are bound at `:313` but never read afterwards (only `override_narrative` at `:318` and `injected_narratives_post` at `:330` are consumed). `verified (read: game.py:285-331)` + `verified (run: probes evt-p14, evt-p15: PASS 1 added_choices [], PASS 2 has both choices, PASS 3 [] because `once` skipped it)`.
3. Even if the choices rendered: picking the menu item returns the action string verbatim (`game.py:192-197`; it does not start with `trigger:`, so `:197` returns `(action, None)`), which then flows through `game.py:309` → intent classification (`:312`) → `check_and_trigger_events` (`:313`) where the exact match at `event_manager.py:201` fires the ending — `verified (run: probe evt-p09 C: `check_and_trigger_events('end_story_success_heroic')` → ending flags set)`.
4. Typing those words manually as free text is **impossible**: `get_player_choice` (`game.py:176-199`) only accepts a digit within range or a `/`-command; anything else prints "Invalid choice." and re-prompts, so typed text never becomes `player_input_text` — `verified (read: game.py:181-199)` + `verified (run: probe evt-p14 final note)`. The engine's "natural language input" is in practice the LLM's 4 generated choice labels.

## `add_item` key mismatch — highest-value finding (question 8)

`event_manager.py:110-111` reads `action.get("item_id")`; `remove_item` (`:112-113`) reads `action.get("value")`. Shipped-YAML audit — `verified (run: probe evt-p19 part B)`:

| File:line | Action | Key written |
|---|---|---|
| `events/whispers…yaml:41` | `add_item` | `value: "elians_journal"` |
| `events/whispers…yaml:95` | `add_item` | `value: "runic_key"` |
| `events/the_clockwork…yaml:186` | `add_item` | `value: "temporal_gear"` |
| `story_parts/…/chapter1_study.yaml:17` | `add_item` | `item_id: "elians_journal"` (works) |
| `story_parts/…/chapter1_study.yaml:74` | `add_item` | `item_id: "runic_key"` (works) |

(Correction to the task premise: there are 5 `add_item` uses total — 3 write `value:` in the two **live** stories' event files, 2 write `item_id:` in the old-format chapter files. All 3 broken ones are in the live path.)

Probe result — `verified (run: probe evt-p02: shipped shape → inventory [None]; `item_id` shape → `['elians_journal']`; add-`item_id`-then-remove-`value` → `[]`)`. `add_item(None)` passes the `if item not in inventory` check in `game_state_manager.py:28` and appends `None`.

Downstream `inventory_has` conditions in the Whispers story that can never fire as written — `verified (run: probe evt-p02 inventory scan + evt-p11 5c)`:
- `read_journal_clue` requires `inventory_has: elians_journal` (`whispers…yaml:60-61`) — inventory holds `None`, not the journal.
- `rescue_elian` requires `inventory_has: runic_key` (`whispers…yaml:194-195`) — same.

Cascade (all `verified (read: whispers…yaml)` unless noted): `knows_about_bluffs` is set **only** by `read_journal_clue` (`:65-66`) → `find_hidden_key` (`:88-89`), `arrive_at_bluffs` (`:116-117`), `enter_the_crypt` (`:169-170`) can never fire → the story is unfinishable through normal play. And it is worse than "stuck": `verified (run: probe evt-p09 A)` — on the **next turn** `get_llm_options` builds its prompt f-string with `', '.join(inventory)` at `game.py:127-137`, *outside* the `try:` at `:139`, so `inventory=[None]` raises `TypeError: sequence item 0: expected str instance, NoneType found` and kills `game_loop` (the fallback at `game.py:165` is unreachable). Whispers therefore **crashes one turn after the first puzzle**. The Clockwork Heist has the same latent crash: `temporal_gear` → `[None]` after its turn-4 event (`verified (run: probe evt-p09 B turn 4: inv=['smoke_bomb', None])`), so its next `get_llm_options` would crash the same way — `inferred (because it is the identical `', '.join` code path demonstrated with `[None]`)`. The clockwork story *does* reach its `end_game` in the probe (`evt-p09 B turn 5`), but only because the probe bypasses `get_llm_options`.

## `update_stat` edge cases (question 9)

`event_manager.py:116-120` reads `stat` and `change_by`, computes `get_stats().get(stat_name, 0) + change_by`, writes back.

| YAML shape | Result | Evidence |
|---|---|---|
| `stat` + numeric `change_by` | correct relative update | verified (run: probe evt-p07 #1/#2: stealth 80→70, health 100→80) |
| `change_by` absent (`None`) | `TypeError: unsupported operand +: int and NoneType` — crashes, stat unchanged | verified (run: probe evt-p07 #3) |
| `change_by` non-numeric string | `TypeError: int + str` | verified (run: probe evt-p06 #4b) |
| `stat` absent | **no crash**: `stats[None] = 0 + change_by` — a literal `None` key appears in the stats dict | verified (run: probe evt-p07 #4: `{'health': 100, None: 5}`) |
| existing stat holds a string | `TypeError` (str + int) | verified (run: probe evt-p07 #7) |

Both shipped uses are correctly shaped: `the_clockwork…yaml:96-98` (`stat: "stealth"`, `change_by: -10`) and `:272-274` (`stat: "health"`, `change_by: -20`) — `verified (run: probe evt-p19 audit + evt-p07 #1/#2)`. `change_by: 0` is a no-op that still writes the key — `verified (run: probe evt-p07 #6)`.

## `present_choices` ignores `text:` and per-choice `condition:` (question 10)

`event_manager.py:139-147` copies only `label` and `action` from each choice; the action-level `text:` and any per-choice `condition:` are dropped.

- `whispers…yaml:212` writes `text: "What do you do?"` on the shipped `present_choices` → discarded; `override_narrative` stays `None` — `verified (run: probe evt-p06 #5: added_choices carry only label/action, override None)`.
- `DEVELOPER_GUIDE.md:359-369` documents `condition:` on a choice (lines 363-365) as gating a choice on `inventory_has`. The engine has no such logic, so documented conditional choices would always display, even when the player lacks the item. No shipped YAML uses `choice condition:` — `verified (read: whispers…yaml:211-217)` — so today it is a docs-only defect.
- Gameplay consequence in practice is moot for Whispers because the choices are dropped one level up by `game.py` (question 7), but the `text:` loss means even a working `present_choices` shows bare labels with no prompt line.

## `end_game` and what the player actually sees (question 11)

`event_manager.py:148-154`: `end_game` sets `game_ended` + `game_ended_success`/`game_ended_failure` (`success` defaults to `True` at `:150`) and sets `override_narrative = message`, default `"The story ends here."` (`:151, 154`).

- Because actions run in list order, `end_game`'s message **clobbers** an earlier `override_narrative` in the same event: the shipped endings list `override_narrative` (the 8-10 line epilogue, `whispers…yaml:232-241` / `:257-267`) *before* `end_game success: true` with no `message` (`whispers…yaml:242-243` / `:268-269`) → final `override_narrative` is `"The story ends here."` — `verified (run: probes evt-p06 #6, evt-p16)`.
- `game.py:318-319` assigns that string to `narrative`, skips the LLM continuation, then `game.py:334` sees `game_ended`, prints the `🎉 STORY COMPLETED SUCCESSFULLY! 🎉` banner (`:337`) and `break`s at `:344` — **before** the loop top's `display_story(narrative)` at `:280-281` ever runs. The epilogue prose and even the default message are assigned but never displayed; the player sees only the choice echo (`game.py:309`) and the banner — `verified (read: game.py:318-344)` + `verified (run: probe evt-p16)`.
- A bare `end_game` with no keys reports SUCCESS and the default message — `verified (run: probe evt-p19 part A: override 'The story ends here.', flags game_ended + game_ended_success)`. (Probe evt-p16's second half attempted this but its synthetic event never triggered because the input didn't match its trigger — superseded by evt-p19; kept as a dead end.)

## Permanently dead trigger combinations; `game_start` (question 12)

`verified (read: event_manager.py:170-177, 206-207, 254-258)` + `verified (run: probe evt-p08 E, evt-p04)`:

| Trigger shape | Auto-fire? | Why / where |
|---|---|---|
| `mode: MANUAL` (any case; `.upper()` at `:171`) | never via `check_and_trigger_events` | `:173-174` returns False. Reachable only via `execute_event_actions` (`game.py:213/272/301`) |
| `conditions: []` or missing | never | `:176-177` returns False (forced execution still works) |
| mode not `AND`/`OR` (e.g. `XOR`) | never | falls through to `:258` return False even with all conditions true |
| any condition of unknown type under `AND` | never | contributes False (`:184`, `:252`) |
| unknown type under `OR` | possible | other conditions can satisfy `any()` |
| `game_start` | **yes — during turn 0 only** | `:206-207` tests `turn_count == 0`; `turn_count` is incremented only at end of turn (`game.py:347`), so it fires in the pre-choice pass (`game.py:285`) — correcting the premise: `game_start` is *not* dead through the pass, `verified (run: probe evt-p08 E: flag 'g' set at turn 0)`. It fires again in the same turn's post-choice pass (`game.py:313`) if not `once` — `verified (run: probe evt-p08 E final line)`. Dead from turn 1 onward |
| `story_start` (shipped, `mode: MANUAL` + `game_start` condition, `whispers…yaml:4-7`) | only via `game.py:272` | MANUAL short-circuit at `:173-174`; the `game_start` condition is decorative |

The premise that `game.py:272` executing `story_start` before the loop makes `game_start` unfireable is **false**: `turn_count` is still 0 during the first turn's two passes because `increment_turn` runs at `game.py:347`, after the ending check.

## No exception handling; re-entrancy (question 13)

- `_perform_actions` has no try/except (`verified (read: event_manager.py:91-161)` + `verified (run: probe evt-p06 #8: source contains no try)`). One raising action aborts the loop at `:102`: **all remaining actions are skipped** and the exception propagates out of `check_and_trigger_events`/`execute_event_actions` into `game_loop`, which has no handler — verified (read: game.py:276-377, no try) — so the process dies with a traceback. `verified (run: probe evt-p06 #4: set_flag 'a' ran, update_stat raised, set_flag 'c' never ran)`.
- Once-marking asymmetry on failure: natural path marks only after success (`:77-78`), so a crashed natural firing can retry next pass; forced path marks **before** performing (`:277-279`), so a crashing forced run still consumes the `once` — `inferred (from the cited lines; the retry case itself not separately probed)`.
- Not re-entrant: `_perform_actions` calls only `GameStateManager` mutators; it never calls `check_and_trigger_events` or `execute_event_actions` — `verified (read: event_manager.py:102-154)` + `verified (run: probe evt-p06 #8)`. Events cannot trigger events within an action; cascades happen only across later passes (same pass if no override intervenes, question 3) or via the `trigger:` choice path.
- Malformed YAML that reaches the engine: `actions:` present-but-null → `Event.actions is None` → `TypeError: 'NoneType' object is not iterable` at `:102` — `verified (run: probe evt-p17 A)` (root cause `yaml_loader.py:25` default only covers a missing key — see load.md). `trigger: None` → `AttributeError` at `:170` — `verified (run: probe evt-p04)`. Non-string `player_action`/`player_action_keyword` values → `AttributeError` at `:195`/`:201` — `verified (run: probe evt-p05)`.
- `load_state` with a string instead of a list silently builds a set of characters (`set("ab") → {'a','b'}`) — `verified (run: probe evt-p12 C)`.

## The `modified_prompt_instructions` pass-through (question 14)

`event_manager.py:85` returns the caller's own list object under that key — `verified (run: probe evt-p06 #7: returned object IS the caller's list, True)`. `game.py` never reads the key; it keeps its own `llm_instructions = []` (`game.py:284`), which `modify_prompt` mutates in place (`event_manager.py:124`), and passes that same list to `get_llm_story_continuation` at `game.py:322-324`. The key exists only in the `check_and_trigger_events` and live-not-found return dicts, not in the `_perform_actions` shape — `verified (run: probe evt-p17 C)`. Note `llm_instructions` is re-created each turn (`game.py:284` inside the loop), so `modify_prompt` instructions have one-turn lifetime — `verified (read: game.py:276-284)`.

## Dependencies out

| Target | Called at | Why |
|---|---|---|
| `GameStateManager` mutators `set_flag/clear_flag/add_item/remove_item/update_stat/set_current_location` | `event_manager.py:107, 109, 111, 113, 115, 120, 152-153` | all state writes |
| `GameStateManager` readers `get_current_location/get_flags/get_inventory/get_stats` + `game_state.turn_count`, `game_state.turns_in_location` | `:186-188, 203, 205, 207, 211, 225, 240` | condition inputs |
| `rich.Console` (`self.console.print`) | `:26, 32` (dead), `:60-62` (live, ungated) | trigger DEBUG output |
| `data_structures.Event` | `:24, 50, 58, 77, 91, 102, 267, 278` | the rule rows |

State-façade contract details (live-object getters, dedupe add, location change resetting `turns_in_location`) are documented in `sections/data.md` and are load-bearing here: `set_current_location` zeroing `turns_in_location` (`game_state_manager.py:44-47`) is what keeps `tide_recedes` from chain-firing — `verified (run: probe evt-p10 #3)`.

## Dependencies in

| Caller | Location | What it expects |
|---|---|---|
| `game_loop` pre-choice pass | `game.py:285-287` (input `""`, no intent) | `injected_narratives_pre`, `added_choices` (the **only** read of `added_choices`, `game.py:294`), ignores the rest |
| `game_loop` post-choice pass | `game.py:313-315` (input = chosen label/action, intent from LLM) | `override_narrative` (`:318`), `injected_narratives_post` (`:330`) |
| `story_start` bootstrap | `game.py:272-274` | `override_narrative` replaces the intro file text |
| `trigger:` choice path | `game.py:301-305` | `override_narrative`, else keep current narrative |
| `/force_event` | `game.py:213` | nothing (output discarded) |
| `/save` / Resume | `game.py:227`, `game.py:249-250` | `get_state()`/`load_state()` round-trip of `triggered_event_ids` — `verified (run: probe evt-p13 A: resume refuses to replay the once-event)` |
| Tests | `tests/test_game_engine.py:33, 57, 81`, `tests/test_new_engine.py:90` | positional 3-arg form; `player_intent` default |

No other module imports `EventManager` — `verified (run: grep over text_adventure_tui_lib/ and tests/)`.

## Side effects

| Effect | Location | Trigger condition | Reversible? |
|---|---|---|---|
| Flags/inventory/stats/location mutated via gsm | `event_manager.py:107-120, 152-153` | event fires (natural or forced) | only by other events' actions |
| `triggered_event_ids` grows | `:78` (natural), `:278-279` (forced) | `once` events | persisted by `/save` |
| DEBUG line printed to the player's console | `:60-62` | **every** natural trigger, even with debug off (`DEBUG_MODE_ENABLED` not consulted) | no |
| Caller's `llm_prompt_instructions` list appended in place | `:124` | `modify_prompt` actions | no (list is per-turn, `game.py:284`) |

## Error and edge behaviour

Summarised from the sections above; every row probed:

| Situation | What happens | Location / evidence |
|---|---|---|
| Unknown condition type | silent False, no warning | `:184, 252`; probes evt-p04/p12 B |
| Unknown mode | silent False even if conditions true | `:258`; probe evt-p04 |
| `add_item` with `value:` | `None` appended to inventory → next turn `TypeError` in `game.py:127-137` | `:111`; probes evt-p02, evt-p09 A |
| `update_stat` missing `change_by` | `TypeError` mid-list, remaining actions skipped, crash to top level | `:118-120`; probe evt-p07 #3, evt-p06 #4 |
| `update_stat` missing `stat` | silent `stats[None] = change_by` | `:119-120`; probe evt-p07 #4 |
| Non-string `player_action` value | `AttributeError` | `:201`; probe evt-p05 |
| `actions:` null in YAML | `TypeError` at first action | `:102`; probe evt-p17 A |
| `trigger:` null / event id not found (forced) | clean empty-result dict (live def) | `:267-275`; probe evt-p17 C |
| Forced `once` event | single firing permanently consumed, actions run without narrative | `:277-279`; probes evt-p13 B, evt-p06 #1 |
| `end_game` after `override_narrative` | message clobbers the prose | `:121-122` vs `:154`; probe evt-p06 #6 |
| Duplicate event ids | last wins at first position, no warning | `:8`; probe evt-p08 D |

## Lifecycle and concurrency

Constructed at `game.py:249/261` per `game_loop` invocation (fresh on resume, then `load_state`); no teardown. Single-threaded: the only mutators run inside the synchronous game loop; no locks, none needed. No re-entrancy (question 13). `triggered_event_ids` is the only cross-turn internal state. — `verified (read: game.py:233-377)`.

## Configuration

| Knob | Default | Source | Runtime or restart |
|---|---|---|---|
| `options.once` | False | YAML `options` (`event_manager.py:52, 77, 278`) | per load |
| `trigger.mode` | `AND` (`.upper()`) | YAML (`:171`) | per pass |
| condition `operator` | `==` for counters, `>=` for `stat_check` | YAML (`:209, 223, 238`) | per evaluation |
| `inject_narrative.position` | `post` | YAML (`:127`) | per action |
| `end_game.success` / `message` | `True` / `"The story ends here."` | YAML (`:150-151`) | per action |
| `options.priority` | documented (`DEVELOPER_GUIDE.md:74`) | **never read anywhere** — `verified (run: grep -rn priority → no matches)` | n/a |

Events are loaded once per `game_loop` (`game.py:254-261`) and never hot-reload; the YAML files are effectively compiled at game start. Schema drift between docs and engine is listed under Docs vs code.

## Extension points

`DEVELOPER_GUIDE.md:526-541` promises: new trigger types → add evaluation in `EventManager._evaluate_trigger()` + "add validation in `StoryManager`"; new action types → add handling in `_perform_actions()` + "update return value structure".

Reality for a contributor:
- Adding a condition type = one more `elif` before `event_manager.py:250`. There is no registry, no `else`-warning; a typo'd type silently disables the event (question 5). Whether `StoryManager`/`story_tool validate` would flag an unknown type is owned by the STRY section — `unknown (needs STRY section's validation probe)`.
- Adding an action type = one more `elif` in `:106-154` **and** a result-plumbing decision: only the 4 result keys at `:156-161` reach `game.py`; anything new needs a new key in all three return sites (`:83-89`, `:156-161`, `:269-275`) and a consumer in `game.py` — `inferred (because `added_choices` is already silently dropped by one of the two call sites, question 7)`.
- The first file a developer would edit for either is `text_adventure_tui_lib/event_manager.py`.

## Tests

| Test file | What it actually asserts | Coverage notes |
|---|---|---|
| `tests/test_new_engine.py:71-92` | one `location`-triggered event sets a flag | Sets `flags["current_location"]` (`:85`) — the wrong dict; passes only because `GameState.current_location` defaults to `"start"` — `verified (read)` |
| `tests/test_game_engine.py:15-35` | `player_action` exact match fires | 3-arg call, intent default |
| `tests/test_game_engine.py:38-59` | `turn_count_in_location >=` fires | |
| `tests/test_game_engine.py:62-85` | `add_choice` returns label+action incl. `trigger:` prefix | the only test touching the choice pipeline |

Not covered at all: `execute_event_actions` (both defs), `once`, `end_game`, `present_choices`, `inject_narrative`, `modify_prompt`, `update_stat`, `add_item`/`remove_item`, save/load of `triggered_event_ids`, mode handling. The 7 passing tests all exercise the happy path of `check_and_trigger_events` — `verified (read: tests/, 3 files)`.

## Surprises

- **The flagship story crashes the game one turn after its first puzzle**: `add_item value:` → `inventory [None]` → `TypeError` in `get_llm_options`' prompt f-string, built outside its `try:` — `whispers…yaml:41`, `event_manager.py:111`, `game.py:127-139` — `verified (run: probes evt-p02, evt-p09 A)`.
- **The two shipped endings can never be selected and, if forced, display no ending prose**: choices produced in the post-choice pass are dropped (`game.py:294` reads only the pre-pass result), and `end_game`'s default message clobbers the epilogue before `game.py:344` breaks past the only `display_story` — `verified (run: probes evt-p14/p15/p16)`.
- `/force_event` permanently consumes a `once` event's single firing, silently — `event_manager.py:277-279` — `verified (run: probe evt-p13 B)`.
- Every auto-triggered event prints a `DEBUG:` line to the player's console even with debug mode off; the gated-looking DEBUG prints in `:26-35` belong to the dead definition — `event_manager.py:60-62`, `game.py:48-50` — `verified (run: probe evt-p18)`.
- Evaluation order is YAML file order, and one input can chain events (A's `change_location`/`add_item` satisfying B's conditions mid-pass) — order-dependence that story authors must reason about with no priority knob (documented `priority` is unread) — `verified (run: probes evt-p03, evt-p11)` — `verified (run: grep priority)`.
- The player can never type free text into the engine: only menu digits and `/`commands are accepted, so "natural language" triggers actually match LLM-generated labels — `game.py:181-199` — `verified (read)` + probe evt-p14.
- `game_start` fires twice per new game (pre- and post-choice passes at turn 0) unless `once` — `verified (run: probe evt-p08 E)`.

## Docs vs code

| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| `options.priority` controls execution priority | `DEVELOPER_GUIDE.md:74`; performance advice `:519` | never read | **false** |
| Choice-level `condition:` gates a `present_choices` option | `DEVELOPER_GUIDE.md:363-365` | dropped at `:143-146` | **false** |
| Trigger type list | `DEVELOPER_GUIDE.md:89-103`, `README.md:110-120` | exactly the 12 implemented | matches |
| Action type list | `DEVELOPER_GUIDE.md:105-121`, `README.md:122-132` | exactly the 10 implemented | matches |
| `end_game`: "End story with success/failure" | `README.md:132` | works, but the ending text is never shown and success defaults True | **misleading by omission** |
| Debug mode shows "Event trigger evaluations" | `DEVELOPER_GUIDE.md:456-461` | trigger DEBUG prints unconditionally; forcing prints nothing (dead def) | partially true, for the wrong reason |
| `add_item` listed without key name | `DEVELOPER_GUIDE.md:109`, `README.md:124` | engine reads `item_id:` (`:111`); shipped stories write `value:` | docs never state the key; content is broken |
| Event YAML schema (`once`, `mode`, conditions, actions) | `DEVELOPER_GUIDE.md:69-85`, `README.md:83-106` | structurally accurate | matches |

## Assigned-question index

Q1 F811 → "F811" section · Q2 duplicate ids/order → "Duplicate ids…" · Q3 break/order-dependence → "One pass…" · Q4 once consumption → "once consumption…" · Q5 condition catalogue → "Condition-type catalogue…" · Q6 keywords → "player_action_keyword…" · Q7 ending chain → "player_action exact match…" · Q8 add_item → "add_item key mismatch…" · Q9 update_stat → "update_stat edge cases…" · Q10 present_choices → "present_choices ignores…" · Q11 end_game display → "end_game and what the player actually sees…" · Q12 dead triggers → "Permanently dead trigger combinations…" · Q13 exceptions/re-entrancy → "No exception handling…" · Q14 pass-through key → "The modified_prompt_instructions pass-through…".

## Unknowns

- Whether `story_tool validate` / `StoryManager` catches unknown condition types or the `add_item value:` shape — needs the STRY section's validation findings (`DEVELOPER_GUIDE.md:531` promises validation lives there).
- Which definition of `execute_event_actions` ships inside `dist/`'s 0.1.1 wheel and the site-packages shadow copy — needs `unzip -p dist/*.whl …/event_manager.py`; if it is the dead-def-only era, `/force_event` semantics differ for installed users.
- Real `player_intent` strings in live play (LLM-classified, `game.py:97-120`) and therefore whether any `player_intent`-conditioned event can realistically fire — needs an Ollama server.
- Whether any real save files exist whose `triggered_event_ids` were produced by the dead-def era (which did not mark once-events) — needs a production save file.

# Text-Adventure-TUI: flow — FLOW-4 one YAML event → state mutations

Prefix: FLOW-4 · Sections touched: CONF, LOAD, EVT, DATA · Commit: `7f349d1`
Question it answers: How does one YAML event become state mutations? Follow a single event
from raw YAML bytes to flags/inventory/location writes, with every field read and every
default applied.

Worked example: `find_elians_journal`, `text_adventure_tui_lib/events/whispers_of_the_salted_crypt_story_events.yaml:25-49` —
`once: true`; trigger = AND of `location` + `player_action_keyword` + `flag_not_set`;
actions = `set_flag` + `add_item` + `override_narrative` + `modify_prompt` — verified (read: whispers…yaml:25-49).
Generalisation notes at each hop say what differs for other events.

Probes: `/tmp/opencode/cdd-text-adventure-tui/flows/f4-probe1.py`, run from the repo root with
`PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` (stale 0.1.1 site-packages copy shadows the repo — ledger: Environment notes).
Cited as `verified (run: f4-probe1.py §P1…P5)`. No project files were modified.

---

## Trigger

The event fires from the **post-choice pass** of the turn loop: `game.py:313-315` calls
`check_and_trigger_events(game_state_manager, player_choice, llm_instructions, player_intent)`
— verified (read: game.py:312-315). The pre-choice pass (`game.py:285-287`) passes `""` as
`player_input_text`, and `player_action_keyword` keeps `met = False` for falsy input
(`event_manager.py:193-194`), so a keyword-triggered event can only fire post-choice —
verified (read: event_manager.py:191-197) + verified (run: f4-probe1.py §P4: pre-pass with `""`
did not fire it; post-pass with `"search desk"` did).
(`location`/`flag`/`inventory`/`turn_count`-only events fire in either pass; `game_start`
only in the two passes of turn 0, because `increment_turn` runs at `game.py:347` — verified (read: game.py:347-348).)

## Hop-by-hop trace

| # | Hop | Location | State read | State written | External effect |
|---|---|---|---|---|---|
| 1 | YAML bytes on disk; file ends without trailing newline | whispers…yaml:25-49 (bytes) | — | — | file read |
| 2 | `_load_yaml`: `open(file_path, "r")` (no `encoding=`) → `yaml.safe_load` → one Python object | yaml_loader.py:8-11, called at :61 for this file (and :54 for general) | filesystem | — | `yaml.safe_load` parses; no custom tags executable |
| 3 | Top-level is a **list**; this event is the 2nd mapping in its file (index 1); loader concatenates `general_events.yaml` (6 events, :52-56) **then** story events (10, :59-63) → `all_events`, this event at **index 7** | yaml_loader.py:49-63 | — | `all_events: list[dict]` (throwaway) | — |
| 4 | `_create_events_from_data` builds one `Event` per dict: hard `data["id"]`, `.get` defaults for the rest, **all other keys silently dropped** | yaml_loader.py:14-29 (this event: :20-28) | raw dicts | `Event(id, name, trigger, actions, options)` | — |
| 5 | `Story(id=story_name, title, events=events)` — the event rides inside `Story.events` | yaml_loader.py:75-79 (events list built at :73) | arc YAML fields | `Story` | — |
| 6 | `EventManager(story.events, console)` (new game: `game.py:261`; resume: `game.py:249`) collapses the list into `self.events = {event.id: event}` — **list order becomes dict insertion order**; `find_elians_journal` lands at **position 7** | event_manager.py:8 | `Story.events` | `self.events` dict, `self.triggered_event_ids = set()` (:9) | — |
| 7 | Per-turn pass: `check_and_trigger_events` iterates `self.events.items()` in insertion order | event_manager.py:50; called from game.py:285-287 (input `""`) and game.py:313-315 (input = chosen label) | — | locals: override/injections/choices accumulators (:45-48) | — |
| 8 | Once-check: `event.options.get("once", False) and event_id in self.triggered_event_ids` → skip. First encounter: proceeds (`once: true`, set empty) | event_manager.py:51-55 | `options`, `triggered_event_ids` | — | — |
| 9 | `_evaluate_trigger`: `conditions = trigger_config.get("conditions", [])`, `mode = .get("mode","AND").upper()`; MANUAL → False (:173-174); empty conditions → False (:176-177) | event_manager.py:170-177 | `event.trigger` | — | — |
| 10 | Condition 1 `location`: `get_current_location() == "elian_study"` | event_manager.py:185-186 → game_state_manager.py:41-42 | `GameState.current_location` (`data_structures.py:44`) | — | — |
| 11 | Condition 2 `player_action_keyword`: `keywords = condition.get("keywords", [])` (:192); truthy-input guard (:193); `any(str(k).lower() in player_input_text.lower() for k in keywords)` — substring, case-insensitive, **no word boundaries** | event_manager.py:191-197 | `player_input_text` (the LLM choice label) | — | — |
| 12 | Condition 3 `flag_not_set`: `not get_flags().get("has_journal", False)` — **live dict read**; default False | event_manager.py:189-190 → game_state_manager.py:14-15 | `GameState.flags` (`data_structures.py:42`) | — | — |
| 13 | Mode AND → `all(results)` (each `met` appended at :252; `met` initialised False at :184, so an unknown type contributes False; no `else`, no warning) | event_manager.py:252, 254-255 | — | — | — |
| 14 | Fired → `console.print("DEBUG: Event 'find_elians_journal' triggered!", style="green")` — **not gated** by `DEBUG_MODE_ENABLED` | event_manager.py:60-62 | — | — | green DEBUG line to the player's console |
| 15 | `_perform_actions` iterates `event.actions` in list order (`:102`); per action: `type = action.get("type")` (:103), `action_value = action.get("value")` (:104) | event_manager.py:102-104 | `event.actions` | locals `override_narrative=None` (:97), injected lists (:98-99), choices (:100) | — |
| 16 | Action 1 `set_flag` → `gsm.set_flag("has_journal")` → `flags["has_journal"] = True` | event_manager.py:106-107 → game_state_manager.py:17-18 | `action_value` (:104) | `GameState.flags["has_journal"]` | — |
| 17 | Action 2 `add_item` → reads **`action.get("item_id")`** — the YAML wrote `value: "elians_journal"` (:41-42) → `add_item(None)` → `None not in []` → `inventory.append(None)` — **the None-inventory bug** | event_manager.py:110-111 → game_state_manager.py:27-29 | `action.get("item_id")` → None; live `player.inventory` | `Player.inventory` → `[None]` | — |
| 18 | Action 3 `override_narrative` → local `override_narrative = action.get("text", "")` — no state touched | event_manager.py:121-122 | `action.get("text","")` | local var only | — |
| 19 | Action 4 `modify_prompt` → `llm_prompt_instructions.append(action.get("instruction",""))` — **appends into the caller's list object** | event_manager.py:123-124 | caller's list | caller's `llm_instructions` (`game.py:284`) | — |
| 20 | Return 4-key results dict (`:156-161`); caller merges: override recorded (:67-68), pre/post injections extended (:69-74), choices extended (:75); **once-marking after success** (:77-78); **break on override** (:80-81) — every event after position 7 in this pass is skipped | event_manager.py:63-81 | results | `triggered_event_ids`, accumulators | — |
| 21 | Return 5-key dict — note `modified_prompt_instructions` **is** the caller's own list object | event_manager.py:83-89 | — | — | — |
| 22 | `game.py` consumes: `override_narrative` truthy → `narrative = override` **and the LLM continuation at :322-327 is skipped** — so this event's `modify_prompt` text (already appended at hop 19) is never sent anywhere; the list is re-created empty next turn (`game.py:284`) | game.py:318-327, 284 | results dict | `narrative` (local, next turn's display at :280-281) | LLM continuation call skipped |
| 23 | Post-injections displayed (:330-331 — none for this event); `game_ended` flag checked (:334 — not set by this event); turn advanced (:347-348) | game.py:330-348 | flags | turn counters | — |

All hops verified (read: cited lines) unless marked; runtime confirmation per hop in
verified (run: f4-probe1.py §P1-P5): parse/defaults/unknown-key drop (P1), dict position 7 (P2),
per-condition met values incl. empty-input and substring negatives (P3), the firing with
`flags={'knows_elian_is_missing':True,'has_journal':True}`, `inventory=[None]`, override text,
prompt-list identity `is` the caller's list, once-marking, and second-pass skip (P4).

## Diagram

```text
disk bytes: whispers…story_events.yaml:25-49 (CONF)
   │
   ▼
_load_yaml  open()+yaml.safe_load ................................ yaml_loader.py:10-11
   │ list[10 dicts]; this event = index 1 in file
   ▼
all_events = general 6 (yaml_loader.py:52-56) + story 10 (:59-63)  yaml_loader.py:49-63
   │ this event = index 7
   ▼
_create_events_from_data ......................................... yaml_loader.py:14-29
   │ data["id"] hard :22 · .get defaults :23-26 · unknown keys DROPPED
   ▼
Event dataclass .................................................. data_structures.py:11-17
   │ Story.events (yaml_loader.py:75-79)
   ▼
EventManager {event.id: event} ................................... event_manager.py:8  (game.py:261)
   │ insertion position 7 · triggered_event_ids=set() :9
   ▼
check_and_trigger_events (per pass) .............................. event_manager.py:38-89
   │      ▲ game.py:285-287 input ""  ·  game.py:313-315 input = choice label
   ├─ once-skip .................................................. :51-55
   ├─ _evaluate_trigger .......................................... :163-258
   │    ├─ location        :185-186 → gsm.get_current_location() .. game_state_manager.py:41-42 → GameState.current_location (data_structures.py:44)
   │    ├─ player_action_keyword :191-197 (substring, needs truthy input)
   │    ├─ flag_not_set    :189-190 → gsm.get_flags() ............. game_state_manager.py:14-15 → GameState.flags (data_structures.py:42)
   │    └─ AND all() .......:252, 254-255  (unknown type ⇒ False, :184, no else)
   ├─ DEBUG print (ungated) ....................................... :60-62  → console
   ├─ _perform_actions ............................................ :91-161
   │    ├─ set_flag  :106-107 → gsm.set_flag ...................... game_state_manager.py:17-18  ⇒ flags["has_journal"]=True   [persistent]
   │    ├─ add_item  :110-111 reads item_id (None!) → gsm.add_item  game_state_manager.py:27-29  ⇒ inventory.append(None)      [bug]
   │    ├─ override_narrative :121-122 ⇒ local only → returned :157
   │    └─ modify_prompt :123-124 ⇒ caller's llm_instructions list (game.py:284)                [per-turn]
   ├─ merge results :67-75 · once-mark :77-78 · BREAK on override :80-81
   ▼
return 5-key dict :83-89  ─────────────────────────────────────►  game.py:318-319 narrative = override
                                                                    (LLM continuation :322-327 SKIPPED ⇒
                                                                     the modify_prompt text is never sent;
                                                                     list re-created game.py:284 next turn)
                                                                  game.py:330-331 post-injections (none)
                                                                  game.py:334 game_ended check (no)
                                                                  game.py:347-348 turn advance
```

## Decision branches

| Condition | Location | Branch taken for this event | Consequence |
|---|---|---|---|
| `once` and already triggered | event_manager.py:51-55 | first encounter: proceed | 2nd identical pass: skipped, return dict all-empty — verified (run: f4-probe1.py §P4) |
| `mode == "MANUAL"` | event_manager.py:173-174 | no (mode `AND`) | evaluation continues |
| `conditions` empty | event_manager.py:176-177 | no (3 conditions) | an event with no conditions can never auto-fire |
| `location` equality | event_manager.py:185-186 | True (at `elian_study`) | contributes True |
| `player_action_keyword` truthy-input guard | event_manager.py:193 | True (post-choice input) | pre-pass input `""` ⇒ False ⇒ event cannot fire pre-choice |
| substring match | event_manager.py:194-197 | True for `"search desk"`, `"SEARCH DESK"`; False for `"I search the desk"`, `"search the desk"` | no word boundaries; intervening word kills the match — verified (run: f4-probe1.py §P3) |
| `flag_not_set` | event_manager.py:189-190 | True (`has_journal` absent; `.get(..., False)` default) | the event is self-disabling: after firing, flag set ⇒ condition False forever |
| AND over results | event_manager.py:254-255 | `all([True, True, True])` → True | OR mode would use `any()` (:256-257); any other mode string → False (:258) |
| override produced | event_manager.py:80-81 | True (this event always overrides) | `break`: no later event (e.g. `read_journal_clue` at position 8) evaluated this pass, even if its conditions just became true |
| `override_narrative` truthy at game level | game.py:318 | True | LLM continuation skipped (:320-327); `llm_instructions` never consumed this turn |

## Error branches

| Failure | Location | Surfaced as | Recovery |
|---|---|---|---|
| Event mapping missing `id` | yaml_loader.py:22 (hard `data["id"]`) | bare `KeyError: 'id'`, no filename/line; whole load aborts | none (validate_story catches it separately — load.md) |
| `trigger:` present but null (`data.get` default only covers a *missing* key) | yaml_loader.py:24 passes `None` → event_manager.py:170 `trigger_config.get(...)` | `AttributeError: 'NoneType' object has no attribute 'get'` on the first pass that reaches the event | none — verified (run: f4-probe1.py §P1 shows `trigger = None` survives the loader) |
| `actions:` present but null | yaml_loader.py:25 passes `None` → event_manager.py:102 `for action in event.actions` | `TypeError: 'NoneType' object is not iterable` at fire time — verified (run: f4-probe1.py §P1 shows `actions = None` survives) | none |
| Unknown condition `type` (e.g. `flag_is_set`) | event_manager.py:184 + no `else` before :252 | **no error**: `met` stays False; under AND the event is silently dead | authoring fix only |
| Exception in action 2 of 4 (`update_stat` with `change_by: null` → `TypeError`) | event_manager.py:102 loop, no try/except (:91-161) | exception propagates out of `check_and_trigger_events` into `game_loop`, which has no handler (`game.py:276-377`) ⇒ process dies with traceback. **Already-applied mutations persist**: probe shows `a_ran=True`, `c_never` absent, override never produced — verified (run: f4-probe1.py §P5). No transactionality, no rollback | none |
| Once-marking on crash | natural path marks only at :77-78 *after* success ⇒ crashed natural firing is **not** consumed (can retry); forced path (`execute_event_actions`) marks at :278-279 *before* performing ⇒ a crashing forced run **still consumes** the `once` — verified (run: f4-probe1.py §P5: `crashy` in triggered set only after forced call) | silent state divergence | none |

## State mutations

Everything one firing of `find_elians_journal` changes, and where each change is observable:

| Mutation | Written at | Stored in | Observable where | Survives `/save`? |
|---|---|---|---|---|
| `flags["has_journal"] = True` | event_manager.py:107 → game_state_manager.py:18 | `GameState.flags` dict (data_structures.py:42) | every later trigger via `get_flags()` (:188-190); banner checks `game.py:334,336` | Yes — `/save` dumps the whole `GameState.__dict__` (game.py:225-229) and resume reads `flags` (game.py:243) |
| `inventory.append(None)` (intended: `"elians_journal"`) | event_manager.py:111 → game_state_manager.py:27-29 | `Player.inventory` list — **shared reference**: `get_inventory()` returns the live list (game_state_manager.py:24-25); probe identity check True — verified (run: f4-probe1.py §P4) | `inventory_has` conditions (:203, 205); next turn's `get_llm_options` prompt `', '.join(inventory)` (game.py:127-137) → **`TypeError` kills the loop one turn later**; also `game.py:123-124` | Written into the JSON (whole GameState serialised, game.py:225-229) but **never restored**: resume rebuilds `Player` from YAML and reads only flags/turn_count/current_location/turns_in_location (game.py:239-247) — verified (read: game.py:239-247) |
| `triggered_event_ids.add("find_elians_journal")` | event_manager.py:77-78 (natural) / :278-279 (forced) | `EventManager.triggered_event_ids` set (:9) | once-skip on every later pass (:51-55) | Yes — `get_state()` (:12-13) saved at `game.py:227`, restored at `game.py:250` |
| `llm_instructions.append("The player has just found Elian's journal…")` | event_manager.py:124 | the caller's list object created at `game.py:284` (probe identity check `is` → True — verified (run: f4-probe1.py §P4)) | returned as `modified_prompt_instructions` (:85) but **game.py never reads that key**; the list itself is consumed only at `game.py:322-324`, unreachable whenever an override fired (:318) ⇒ for this event a **dead write**; list lifetime = one turn | No |
| `narrative` replaced by the override text | local at event_manager.py:122 → returned :157 → merged :67-68 → `narrative` at game.py:319 | local variable in `game_loop` | displayed next turn at `game.py:280-281` | No (per-call/transient; a resume falls back to the save's `narrative`, game.py:251) |
| `current_location` / stats | **untouched by this event** (no `change_location`/`update_stat` action) | — | location would be written by `set_current_location` (game_state_manager.py:44-47, which also zeroes `turns_in_location`); read by every `location` condition (event_manager.py:185-186) | location: yes (game.py:245) |

Generalisation: every one of the 10 action types writes through exactly these channels —
`GameStateManager` mutators (game_state_manager.py:17-56) for persistent state, locals +
return dict (event_manager.py:156-161) for transient narrative/choices, and the caller's
prompt list (:124) for per-turn LLM guidance.

## Field-level table — `find_elians_journal`, every YAML key

Core deliverable: YAML key → loader line → Event field → consumer line → effect.
All loader/engine lines verified (read); runtime effects verified (run: f4-probe1.py).

| YAML key (whispers…yaml) | Loader line | Event field (data_structures.py:11-17) | Consumer line | Effect |
|---|---|---|---|---|
| `id: find_elians_journal` (:25) | yaml_loader.py:22 (**hard** `data["id"]`; missing ⇒ `KeyError`) | `.id` | event_manager.py:8 (dict key), :50 (iteration), :77-78 (once mark), :278-279 (forced mark) | identity in `self.events`; once-tracking key |
| `name: "Discovering Elian's Journal"` (:26) | yaml_loader.py:23 (`.get("name","")`) | `.name` | **nothing** — `grep '\.name' event_manager.py` → no matches (verified (run)) | loaded then never read; dead weight |
| `options.once: true` (:27-28) | yaml_loader.py:26 (`.get("options",{})`) | `.options` | event_manager.py:52 (skip), :77-78 (mark), :278-279 (forced mark) | fires at most once per manager lifetime; skipped thereafter (:51-55) |
| `trigger.mode: AND` (:30) | yaml_loader.py:24 (`.get("trigger",{})`) | `.trigger` | event_manager.py:171 (`.get("mode","AND").upper()`), :254-255 | `all()` over condition results |
| `trigger.conditions[].type: location` + `value: "elian_study"` (:32-33) | passes through verbatim (loader never inspects conditions) | inside `.trigger` | event_manager.py:181-182 (`.get`), :185-186 | `get_current_location() == "elian_study"` — reads `GameState.current_location` |
| `type: player_action_keyword` + `keywords: [...]` (:34-35) | verbatim | inside `.trigger` | event_manager.py:191-197 (`keywords` read at :192 with `[]` default) | substring, case-insensitive, needs truthy input; exact strings "search desk"/"examine desk"/"look at desk"/"investigate desk" must appear contiguously in the LLM choice label |
| `type: flag_not_set` + `value: has_journal` (:36-37) | verbatim | inside `.trigger` | event_manager.py:189-190 | `not flags.get("has_journal", False)` — **default `False` applied** ⇒ True on first encounter; self-disabling after the firing |
| `actions[0].type: set_flag` + `value: "has_journal"` (:39-40) | yaml_loader.py:25 (`.get("actions",[])`) | `.actions` | event_manager.py:103-104, :106-107 → game_state_manager.py:17-18 | `flags["has_journal"] = True` — persistent |
| `actions[1].type: add_item` + **`value: "elians_journal"`** (:41-42) | verbatim | `.actions` | event_manager.py:110-111 reads **`item_id`**, not `value` → `None`; game_state_manager.py:27-29 | **`inventory.append(None)`** — the key mismatch bug; engine later crashes on `', '.join` (game.py:127-137) |
| `actions[2].type: override_narrative` + `text: \|` (:43-47) | verbatim | `.actions` | event_manager.py:121-122 (`.get("text","")`), returned :157, merged :67-68 | transient: becomes `narrative` at game.py:319; forces the :80-81 break and skips the LLM continuation |
| `actions[3].type: modify_prompt` + `instruction: "…"` (:48-49) | verbatim | `.actions` | event_manager.py:123-124 (`.get("instruction","")`) | appends into caller's list (game.py:284); unreachable for this event because the override short-circuits game.py:318-327 ⇒ dead write |
| *unknown keys* (any author extra, e.g. `priority`) | **dropped** at yaml_loader.py:21-27 (only the 5 keys above are read) | — | — | vanish silently; probe: `extra_key`/`priority` absent from the Event — verified (run: f4-probe1.py §P1) |
| *missing optional keys* | defaults applied: `name`→`""` (:23), `trigger`→`{}` (:24), `actions`→`[]` (:25), `options`→`{}` (:26) | — | — | `.get` defaults apply only to **missing** keys; a present-but-null YAML key (e.g. `trigger:` with no value) yields `None` and defeats the default — verified (run: f4-probe1.py §P1 null-trap) |

## To change this flow

- To fix the item grant (the flow's one broken mutation): edit **`text_adventure_tui_lib/event_manager.py:111`** — replace `action.get("item_id")` with `action_value` (already extracted at :104), matching the `value:` convention of `remove_item` (:113) and `inventory_has` (:203) and of all three live `add_item` uses (whispers :41-42, :95-96; clockwork :186-187). This single line repairs `read_journal_clue`/`rescue_elian` reachability and removes the `[None]` → `TypeError` crash at game.py:127-137.
- To add a new condition type (e.g. `time_of_day`): add one `elif` to the chain in **`text_adventure_tui_lib/event_manager.py:185-250`**, ending with an assignment to `met` — there is no registry and no `else`, so a typo'd/missed assignment silently evaluates False (initialiser at :184, appended at :252) and, under AND (default mode, :171), disables the whole event. Update `DEVELOPER_GUIDE.md:89-103` (the doc list currently matches the 12 implemented types exactly).
- To change pass semantics (chain more than one narrative per pass): edit **`text_adventure_tui_lib/event_manager.py:80-81`** — the `break` fires whenever any event in the pass produced an override, discarding every later event's evaluation that turn (e.g. `read_journal_clue` at dict position 8 after `find_elians_journal` at 7). Removing it means `game.py:67-68` (which keeps only the **last** override) and `game.py:318` decide which prose wins, and `added_choices`/injections from later events merge at :69-75.

## Unknowns

- Whether real Ollama choice labels ever contain contiguous trigger keywords
  like "search desk" — needs a live model.
- ~~Whether the installed 0.1.1 wheel/site-packages copy carries the same
  `add_item` bug~~ — **resolved post-trace by the orchestrator** (verified run:
  `unzip -p dist/text_adventure_tui-0.1.1-py3-none-any.whl
  text_adventure_tui_lib/event_manager.py`, lines ~192-199): the 0.1.1
  `add_item` appends `action_value`, i.e. it reads the **`value:`** key — the
  opposite convention from the repo's `action.get("item_id")`
  (`event_manager.py:111`). The rewrite changed the engine's expected key and
  updated only the dead legacy chapter copies
  (`Whispers_of_the_Salted_Crypt/chapter1_study.yaml:17-18` uses `item_id:`),
  never the live `events/*.yaml` (all five `add_item` uses are `value:`). So
  the release worked; the current tree is a half-migrated key convention —
  live story broken, dead copies correct.

- Whether any real LLM choice label produced in live play ever contains a contiguous `search desk`-style keyword (the whole keyword-trigger path depends on Ollama's label wording) — needs a live Ollama server; probes drove `EventManager` with hand-picked labels.
- Whether the once-retry-after-crash path (natural firing crashes ⇒ not marked ⇒ refires next pass) can actually repeat in a real session — the first crash already kills `game_loop` (no handler at game.py:276-377), so the retry is reachable only if a future caller adds exception handling — inferred (because of the no-handler read); needs a wrapper to demonstrate a live retry.
- Whether the installed wheel / site-packages shadow copy (`~/.local/…/text_adventure_tui_lib/`, 0.1.1) contains the same `event_manager.py` with the same `add_item` bug — needs `unzip -p dist/*.whl`; players of the installed package may see different behaviour than repo readers.

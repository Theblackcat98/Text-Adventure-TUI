# Text-Adventure-TUI: story content that is behaviour (CONF)

Prefix: CONF · Commit: 7f349d1 · Depth: deep
Scope (read fully, line counts from `wc -l`; both event files end without a trailing
newline, so their last physical lines are 269/283):
`text_adventure_tui_lib/events/general_events.yaml` (91),
`text_adventure_tui_lib/events/whispers_of_the_salted_crypt_story_events.yaml` (268+1),
`text_adventure_tui_lib/events/the_clockwork_heist_story_events.yaml` (282+1),
`text_adventure_tui_lib/story_parts/whispers_of_the_salted_crypt_story_arc.yaml` (46),
`text_adventure_tui_lib/story_parts/the_clockwork_heist_story_arc.yaml` (46),
`text_adventure_tui_lib/story_parts/Whispers_of_the_Salted_Crypt/game_setup.yaml` (29),
`…/chapter1_study.yaml` (83), `…/chapter2_coast.yaml` (50), `…/chapter3_crypt.yaml` (58),
`text_adventure_tui_lib/story_parts/01_intro.txt` (1), `clockwork_intro.txt` (6),
`whispers_intro.txt` (4), `idea.txt` (53).
Read for contract only: `event_manager.py` (281), `yaml_loader.py` (142), `game.py` (466),
`game_state_manager.py` (56), `story_manager.py` (120-263 of 263), `data_structures.py`,
doc claims at `README.md:49-106,225-232`, `DEVELOPER_GUIDE.md:66-121,320-386`.
Method: read + `grep -n` + the four inherited probes (`conf-xref.py`, `conf-typo-additem.py`,
`conf-typo2.py`, `conf-general.py`) plus six added probes (`conf-endings.py`,
`conf-checkpoints.py`, `conf-dup.py`, `conf-reach.py`, `conf-intro.py`, `conf-cascade.py`)
and one inline probe (output in `probe/out-conf-final.txt`), all run with
`PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI` from the repo root; probe
stdout is preserved as `probe/out-conf-*.txt`.
Limits: no Ollama server in this environment, so no end-to-end LLM play-through; every
claim is either a read-out of source/YAML or produced by driving `EventManager` /
`GameStateManager` directly. Which choice labels a real LLM would produce is `unknown`.

## Purpose

The YAML files under `events/` and `story_parts/` ARE the game logic: they define both
stories' state machines (flags, locations, items, beats, endings) and the reusable
ambient rules, and the Python engine is only a generic trigger/action interpreter
(verified (read: event_manager.py:163-258, 91-161)).

## Q1. Complete cross-reference — Whispers of the Salted Crypt

Every event in `text_adventure_tui_lib/events/whispers_of_the_salted_crypt_story_events.yaml`
(verified (read: file 1-269) and (run: `conf-xref.py` → `out-conf-xref.txt`)).
`once` = `options.once`; R = reads, W = writes.

| Event (lines) | once | Trigger conditions | Actions | Flags R | Flags W | Loc R→W | Items R→W |
|---|---|---|---|---|---|---|---|
| `story_start` (2-22) | no | MANUAL + `game_start` (6-7) | `set_flag` (9-10), `change_location` (11-12), `override_narrative` (13-20), `modify_prompt` (21-22) | — | `knows_elian_is_missing` | → elian_study | — |
| `find_elians_journal` (25-49) | yes (27-28) | loc=elian_study (32-33); keyword "search desk/examine desk/look at desk/investigate desk" (34-35); `flag_not_set has_journal` (36-37) | `set_flag` (39-40), `add_item` (41-42, **`value:`**), `override_narrative` (43-47), `modify_prompt` (48-49) | has_journal (not) | `has_journal` | elian_study | → elians_journal (**as None**, see Q3) |
| `read_journal_clue` (51-75) | yes (53-54) | keyword "read journal/open journal/examine journal/look at journal" (58-59); `inventory_has elians_journal` (60-61); `flag_not_set knows_about_bluffs` (62-63) | `set_flag` (65-66), `override_narrative` (67-73), `modify_prompt` (74-75) | elians_journal (inv), knows_about_bluffs (not) | `knows_about_bluffs` | — | elians_journal R |
| `find_hidden_key` (77-104) | yes (79-80) | loc=elian_study (84-85); keyword "search bookshelf/examine bookshelf/look at bookshelf/investigate books" (86-87); `flag_set knows_about_bluffs` (88-89); `flag_not_set has_key` (90-91) | `set_flag` (93-94), `add_item` (95-96, **`value:`**), `override_narrative` (97-102), `modify_prompt` (103-104) | knows_about_bluffs, has_key (not) | `has_key` | elian_study | → runic_key (**as None**) |
| `arrive_at_bluffs` (107-128) | yes (109-110) | keyword "go to bluffs/travel to bluffs/visit bluffs/saltstone bluffs/leave study" (114-115); `flag_set knows_about_bluffs` (116-117) | `change_location` (119-120), `override_narrative` (121-126), `modify_prompt` (127-128) | knows_about_bluffs | — | → saltstone_bluffs | — |
| `tide_recedes` (130-155) | yes (132-133) | loc=saltstone_bluffs (137-138); `turn_count_in_location >= 3` (139-141); `flag_not_set tide_is_low` (142-143) | `set_flag` (145-146), `override_narrative` (147-153), `modify_prompt` (154-155) | tide_is_low (not) | `tide_is_low` | saltstone_bluffs | — |
| `enter_the_crypt` (158-181) | yes (160-161) | loc=saltstone_bluffs (165-166); keyword "enter archway/go through archway/enter crypt/descend/climb down" (167-168); `flag_set tide_is_low` (169-170) | `change_location` (172-173), `override_narrative` (174-179), `modify_prompt` (180-181) | tide_is_low | — | saltstone_bluffs → crypt_antechamber | — |
| `rescue_elian` (183-217) | yes (185-186) | loc=crypt_antechamber (190-191); keyword "use key/insert key/unlock door/open door" (192-193); `inventory_has runic_key` (194-195) | `remove_item` (197-198, `value:`), `set_flag` (199-200), `override_narrative` (201-210), `present_choices` (211-217) | runic_key (inv) | `elian_is_found` | crypt_antechamber | runic_key R→W(remove) |
| `end_story_success_heroic` (220-243) | yes (222-223) | `player_action == "end_story_success_heroic"` (227-228) | `set_flag` (230-231), `override_narrative` (232-241), `end_game success` (242-243) | — | `heroic_ending` (+ engine: `game_ended`, `game_ended_success`, event_manager.py:152-153) | — | — |
| `end_story_success_cautious` (245-269) | yes (247-248) | `player_action == "end_story_success_cautious"` (252-253) | `set_flag` (255-256), `override_narrative` (257-267), `end_game success` (268-269) | — | `cautious_ending` (+ `game_ended`, `game_ended_success`) | — | — |

Plus 6 general events merged into every story (yaml_loader.py:52-56): see Q8/Q9 table.

**Set but never tested (inside the events file)** — verified (run: conf-xref.py):
`knows_elian_is_missing` (set 9-10), `heroic_ending` (set 230-231), `cautious_ending`
(set 255-256), `elian_is_found` (set 199-200; tested only by the arc's checkpoint
`flag_messages` at `whispers_…_story_arc.yaml:27`, not by any event).
**Tested but never set** — none statically (verified (run: conf-xref.py));
*dynamically* `knows_about_bluffs` / `tide_is_low` are never set in a real game because
the chain breaks at `add_item` (Q3), and `elian_is_found` is never set in practice.
Engine-added flags `game_ended`/`game_ended_success` are set by `end_game`
(event_manager.py:152-153) and tested by game.py:334,336 (verified (read)).

## Q1b. Complete cross-reference — The Clockwork Heist

`text_adventure_tui_lib/events/the_clockwork_heist_story_events.yaml`
(verified (read: file 1-283) and (run: conf-xref.py)).

| Event (lines) | once | Trigger conditions | Actions | Flags R | Flags W | Loc R→W | Items R→W |
|---|---|---|---|---|---|---|---|
| `story_start` (2-20) | no | MANUAL + `game_start` (6-7) | `set_flag` (9-10), `change_location` (11-12), `override_narrative` (13-18), `modify_prompt` (19-20) | — | `heist_started` | → thieves_den | — |
| `scout_museum` (23-47) | yes (25-26) | loc=thieves_den (30-31); keyword "scout/observe/watch/study museum/case the joint" (32-33); `flag_not_set museum_scouted` (34-35) | `set_flag` (37-38), `override_narrative` (39-45), `modify_prompt` (46-47) | museum_scouted (not) | `museum_scouted` | thieves_den | — |
| `enter_museum_stealth` (49-76) | yes (51-52) | keyword "sneak in/service entrance/stealth/quietly/slip in" (56-57); `flag_set museum_scouted` (58-59); `flag_not_set inside_museum` (60-61) — **no location condition** | `set_flag` ×2 (63-64, 65-66), `change_location` (67-68), `override_narrative` (69-74), `modify_prompt` (75-76) | museum_scouted, inside_museum (not) | `inside_museum`, `entered_stealthily` | → museum_service_hall | — |
| `enter_museum_bold` (78-107) | yes (80-81) | keyword "front door/bold/direct/main entrance/walk in" (85-86); `flag_not_set inside_museum` (87-88) — **no location condition** | `set_flag` ×2 (90-91, 92-93), `change_location` (94-95), `update_stat stealth -10` (96-98), `override_narrative` (99-105), `modify_prompt` (106-107) | inside_museum (not) | `inside_museum`, `entered_boldly` | → museum_main_hall | stealth −10 |
| `find_temporal_gear_hall` (110-136) | yes (112-113) | `flag_set inside_museum` (117-118); keyword "find gear/temporal gear/search/look for/locate" (119-120); `flag_not_set found_gear_location` (121-122) — **no location condition** | `set_flag` (124-125), `change_location` (126-127), `override_narrative` (128-134), `modify_prompt` (135-136) | inside_museum, found_gear_location (not) | `found_gear_location` | → chronos_exhibition_hall | — |
| `disable_security_lockpicks` (138-166) | yes (140-141) | loc=chronos_exhibition_hall (145-146); keyword "use lockpicks/pick lock/disable security/bypass" (147-148); `inventory_has lockpicks` (149-150); `flag_not_set security_disabled` (151-152) | `set_flag` (154-155), `remove_item` (156-157, `value:` — works, item came from arc), `override_narrative` (158-164), `modify_prompt` (165-166) | chronos_exhibition_hall, lockpicks (inv), security_disabled (not) | `security_disabled` | chronos_exhibition_hall | lockpicks R→W(remove) |
| `steal_temporal_gear` (168-197) | yes (170-171) | loc=chronos_exhibition_hall (175-176); keyword "take gear/steal gear/grab/temporal gear" (177-178); `flag_set security_disabled` (179-180); `flag_not_set has_temporal_gear` (181-182) | `set_flag` (184-185), `add_item` (186-187, **`value:`**), `override_narrative` (188-195), `modify_prompt` (196-197) | security_disabled, has_temporal_gear (not) | `has_temporal_gear` | chronos_exhibition_hall | → temporal_gear (**as None**) |
| `escape_with_smoke_bomb` (200-227) | yes (202-203) | `flag_set has_temporal_gear` (207-208); keyword "smoke bomb/use smoke/throw smoke/smoke" (209-210); `inventory_has smoke_bomb` (211-212) | `remove_item` (214-215, works), `set_flag` (216-217), `override_narrative` (218-225), `end_game success` (226-227) | has_temporal_gear, smoke_bomb (inv) | `escaped_successfully` (+ `game_ended*`) | — | smoke_bomb R→W(remove) |
| `escape_stealth_route` (229-254) | yes (231-232) | `flag_set has_temporal_gear` (236-237); `flag_set entered_stealthily` (238-239); keyword "sneak out/stealth/quietly/service entrance" (240-241) | `set_flag` (243-244), `override_narrative` (245-252), `end_game success` (253-254) | has_temporal_gear, entered_stealthily | `escaped_successfully` (+ `game_ended*`) | — | — |
| `desperate_escape` (256-283) | yes (258-259) | `flag_set has_temporal_gear` (263-264); keyword "run/dash/flee/escape quickly" (265-266); `flag_not_set escaped_successfully` (267-268) | `set_flag` (270-271), `update_stat health -20` (272-274), `override_narrative` (275-281), `end_game success` (282-283) | has_temporal_gear, escaped_successfully (not) | `barely_escaped` (+ `game_ended*`) | — | health −20 |

**Set but never tested** (run: conf-xref.py): `heist_started` (set 9-10),
`entered_boldly` (set 92-93), `barely_escaped` (set 270-271). `escaped_successfully`
is tested at 267-268 only. `has_temporal_gear` is also the arc checkpoint's
`flag_messages` flag (clockwork arc:27). **Tested but never set**: none.
Also dead: `stealth` stat is reduced by 10 (96-98) but no condition ever reads stealth
(the only `stat_check` in all YAML is health, general_events.yaml:9-12)
(verified (run: conf-cascade.py §4) and (read: type census in out-conf-typo2.txt)).

## Q2. The `flag_is_set` typo — proven, and the files are unreachable

All three occurrences of `flag_is_set` in the repo:
`story_parts/Whispers_of_the_Salted_Crypt/chapter1_study.yaml:67`,
`chapter2_coast.yaml:10`, `chapter3_crypt.yaml:12`
(verified (run: grep, out-conf-typo2.txt §"exact line numbers")).

- The engine's condition dispatch has branches for `flag_set`/`flag_not_set`
  (event_manager.py:187-190) and **no** `flag_is_set` branch; an unmatched condition
  type falls through with `met = False` (event_manager.py:184, no else).
- Runtime proof (verified (run: conf-typo2.py)): with `knows_about_bluffs=True` set,
  the isolated shipped condition `flag_is_set(knows_about_bluffs)` evaluates **False**
  while the same condition spelled `flag_set` evaluates **True**; the full
  `find_hidden_key` trigger is False as shipped and True with the spelling fixed.
  Net effect: any event gated by `flag_is_set` is permanently dead, silently.

These files are unreachable from the shipped UI, for two independent reasons
(verified (run: conf-reach.py §A) and (read: yaml_loader.py:38-45, 96-106)):
1. Both stories have `*_story_arc.yaml` files, so `_load_story_old_format` is never
   called (yaml_loader.py:41-45); discovery only ever yields the two arcs
   (story_manager glob, conf-reach §A).
2. Even the old-format path would look for `story_parts/<story_id>/` — i.e.
   `story_parts/whispers_of_the_salted_crypt/` (yaml_loader.py:100) — but the
   directory is named `Whispers_of_the_Salted_Crypt/` (capitalised display name).
   Its only reference anywhere is build metadata
   (`text_adventure_tui.egg-info/SOURCES.txt:25-28`, verified (run: conf-dup.py grep)).
If both copies were ever concatenated anyway, the legacy definitions would silently
shadow all 8 shipped ids because `EventManager.__init__` keeps the LAST duplicate id
(event_manager.py:8; verified (run: conf-reach.py §B: 18 dicts → 10 events, survivors
from the legacy dir)).

## Q3. The `add_item` `value:` defect — every use, every casualty

The engine reads `action.get("item_id")` for `add_item` (event_manager.py:111) but
reads `action.get("value")` for `remove_item` (113) and `condition.get("value")` for
`inventory_has` (203). `GameStateManager.add_item(None)` appends the literal `None`
because `None not in []` (game_state_manager.py:27-29).

**All 5 `add_item` uses in shipped YAML write `value:`** (verified (read) each):

| Event | add_item line | Written instead | Downstream `inventory_has` that can never fire | Beat killed |
|---|---|---|---|---|
| whispers `find_elians_journal` | whispers…yaml:41-42 | `value: "elians_journal"` | `read_journal_clue` condition (60-61) | the journal can never be "read" → `knows_about_bluffs` (65-66) never set |
| whispers `find_hidden_key` | whispers…yaml:95-96 | `value: "runic_key"` | `rescue_elian` condition (194-195) | the rescue, both endings, and the arc's `elian_is_found` ending message are unreachable |
| clockwork `steal_temporal_gear` | clockwork…yaml:186-187 | `value: "temporal_gear"` | none (no condition tests temporal_gear) | none — flag `has_temporal_gear` (184-185) is still set, so the story is playable |
| legacy `chapter1_study.yaml` `find_elians_journal` | chapter1:17-18 | correctly `item_id:` (dead file) | its own `inventory_has` uses `item_id:` (chapter1:38-39) → engine reads `value:` → tests `None` | n/a (file dead) |
| legacy `chapter1_study.yaml` `find_hidden_key` | chapter1:74-75 | correctly `item_id:` (dead file) | `chapter3_crypt.yaml:35-36` tests `item_id:` → `None` | n/a (file dead) |

Runtime proof (verified (run: conf-typo-additem.py PROBE 2)): driving `EventManager`
with the real whispers YAML, keyword "search desk" fires `find_elians_journal` and
`gsm.get_inventory()` returns **`[None]`**; same for `find_hidden_key` and for
clockwork `steal_temporal_gear` (`[None]`).

Cascade consequences (verified (run: conf-cascade.py §1-3)):
- Whispers is chain-broken at the first beat: after "Search desk", flags =
  `{has_journal, knows_elian_is_missing}`, inventory = `[None]`;
  `read_journal_clue` (needs `inventory_has elians_journal`) → False,
  `find_hidden_key`/`arrive_at_bluffs`/`enter_the_crypt` (need `knows_about_bluffs`)
  → False, `rescue_elian` → False. A full 10-turn scripted walk through all intended
  labels triggers only `story_start` + `find_elians_journal` (verified (run:
  conf-reach.py §C)).
- Worse than unreachability: `None` in inventory makes the next turn crash.
  `get_llm_options` builds its prompt with `', '.join(inventory)` at game.py:130,
  which raises `TypeError: sequence item N: expected str instance, NoneType found`
  (verified (run: conf-cascade.py §3)); that f-string is evaluated *before* the
  `try:` at game.py:139, and neither `game_loop` (233-377), the `game_loop` call site
  (435) nor `__main__` (465-466) has an except → the process dies with a traceback on
  the turn after the player finds the journal or the key. In real play (Ollama up),
  Whispers is unplayable past the first successful "search desk" turn.

## Q4. Same story, two copies — precise drift

Shipped: `events/whispers_of_the_salted_crypt_story_events.yaml` (10 events).
Legacy: `story_parts/Whispers_of_the_Salted_Crypt/{game_setup,chapter1_study,
chapter2_coast,chapter3_crypt}.yaml` (8 events). Shared ids: 8; shipped-only:
`end_story_success_heroic`, `end_story_success_cautious`; legacy-only: none
(verified (run: conf-dup.py)). Per-event drift:

| Event id | Trigger drift (shipped vs legacy) | Action drift | Other |
|---|---|---|---|
| `story_start` | identical (MANUAL+game_start) | identical | prose identical |
| `find_elians_journal` | keyword (34-35) vs `player_intent: search_desk` (chapter1:10-11) | shipped `add_item value:` vs legacy `add_item item_id:` + `name:`/`description:` (chapter1:17-20) | prose identical |
| `read_journal_clue` | keyword (58-59) vs `player_intent: read_journal` (chapter1:36-37) | legacy adds `add_choice` "Travel to the Saltstone Bluffs." → `trigger:go_to_bluffs` (chapter1:52-54); shipped drops it | prose identical |
| `find_hidden_key` | keyword + `flag_set` (86-89) vs `player_intent: search_bookshelf` + **`flag_is_set` typo** (chapter1:65-68) | legacy drops `modify_prompt` (file ends at the override text) | prose identical |
| `arrive_at_bluffs` | keyword list incl. "leave study" (114-115) vs `player_action: go_to_bluffs` (chapter2:8-9) | identical | prose identical |
| `tide_recedes` | identical shape (legacy adds a `location:` key inside the condition, chapter2:34, which the engine ignores) | identical | prose identical |
| `enter_the_crypt` | keyword (167-168) vs `player_action: enter_archway` (chapter3:10-11) + `flag_is_set` typo (chapter3:12) | legacy drops `modify_prompt` | prose: legacy is missing a trailing blank line |
| `rescue_elian` | keyword (192-193) vs `player_action: use_key` (chapter3:33-34); `inventory_has value:` (194-195) vs `item_id:` (chapter3:35-36) | identical incl. `present_choices` | prose identical |

Vocabulary comparison (verified (run: conf-dup.py §flags/locations/items)): flag names
and location names are **identical** across copies; the shipped copy adds
`heroic_ending`/`cautious_ending` (endings exist only shipped). Items: same two names,
but the copies are broken in **opposite directions** — shipped writes items with the
wrong action key (`value:` → inventory gets None) while legacy checks items with the
wrong condition key (`item_id:` → engine compares `None` against inventory,
event_manager.py:203; verified (run: conf-dup.py "items tested legacy = [None]").
Ironic corollary: the legacy `inventory_has` would evaluate True against the shipped
bug's `[None]` inventory.) Neither copy is "correct": each matches the engine on one
of the two keys and not the other. Meaning is *approximately* equivalent (same flags,
locations, beats) but the legacy copy is strictly weaker: no endings, dead
`flag_is_set` gates, and `player_intent` conditions that depend on LLM classification
exact matches (game.py:115 normalises to lowercase_with_underscores; legacy intents
like `search_desk` match game.py:106's example list, verified (read)).

## Q5. The endings route — traced, and why it is dead

Content: `rescue_elian` ends with `present_choices` (whispers:211-217) offering
choices whose `action:` values are `end_story_success_heroic` / `end_story_success_cautious`;
the ending events trigger on `player_action` equality with those same ids
(227-228, 252-253).

Exact route of a player selection:
1. `present_choices` is turned into `added_choices` dicts at event_manager.py:139-147.
2. But `rescue_elian` fires during the **post-choice** check
   (`check_and_trigger_events` at game.py:313-315, because its trigger needs the
   player's chosen text, 192-193). `game.py` reads `added_choices` only from the
   **pre-choice** result (game.py:294, result of the check at 285-287). The post-choice
   result's `added_choices` are never read. Verified (run: conf-endings.py Step 1-3):
   the pre-choice `added_choices` is `[]`; the post-choice result *does* contain the
   two ending choices, and no line of game.py reads them.
3. Had a choice been rendered: `get_player_choice` numbers them after the 4 LLM labels
   (game.py:174, 187); an added choice returns its `action` string as `player_choice`
   (game.py:192-197, since it doesn't start with `trigger:`), which is then passed as
   `player_input_text` to the post-choice check (game.py:309-314), where
   `player_action` (event_manager.py:200-201) exact-matches lowercased input against
   the id → the ending fires. The `trigger:` prefix branch (game.py:193-195) that
   routes to `execute_event_actions` is used by the legacy `add_choice`
   (chapter1:52-54) only.
4. Either way the ending's custom prose is clobbered: the `end_game` action runs after
   `override_narrative` in the same action list and overwrites the return value with
   `action.get("message", "The story ends here.")` (event_manager.py:148-154; none of
   the 5 endings supply `message:`). Verified (run: conf-final.txt: firing heroic
   yields override text `"The story ends here."`, flags `game_ended`,
   `game_ended_success`, `heroic_ending`).
5. `game.py:334-344` then prints the success banner and leaves the loop.

If the player types those words as free text: **nothing reaches the events**.
`get_player_choice` accepts only a number in range (187) or a slash command (183-185);
anything else prints `"Invalid choice."` and re-prompts forever (199). Typed
`end_story_success_heroic`, `End Story Success Heroic`, `trigger:end_story_success_heroic`
all loop (verified (run: conf-endings.py Step 4)). There is no free-text input path in
the loop at all: the only strings ever passed as `player_input_text` are LLM labels
selected by number (189-190) and added-choice action strings (192-197).

`once: true` on the endings (222-223, 247-248): through the check path it is honoured
— recorded after firing (event_manager.py:77-78), skipped thereafter (51-55).
Through the only live path, `/force_event` (game.py:212-213), the surviving
`execute_event_actions` (second definition, event_manager.py:260-281, which shadows
the first at 18-36) **records** the id (278-279) but never *consults* it, so repeated
`/force_event end_story_success_heroic` re-runs the ending every time
(verified (run: conf-endings.py Step 6)). The once marking is therefore decorative
for these events.

## Q6. `initial_story_part` and the orphan text files

- Whispers arc declares `01_intro.txt` (whispers arc:3); the file exists
  (`story_parts/01_intro.txt`, 223 bytes). Clockwork arc declares
  `clockwork_intro.txt` (clockwork arc:3); exists (857 bytes).
  Verified (run: conf-intro.py §A/C).
- **Both intros are displayed for zero turns**: `game_loop` reads the file
  (game.py:264-267) and then immediately overwrites `narrative` with the
  `story_start` `override_narrative` (game.py:272-274; both `story_start` events have
  one — whispers:13-20, clockwork:13-18). A missing file falls back to
  `"The story begins..."` (game.py:268-269). Verified (run: conf-intro.py §A/B).
- `whispers_intro.txt` (4 paragraphs, 887 bytes) is referenced **nowhere** in the repo
  (verified (run: grep over *.py/*.yaml/*.md/*.txt/*.in — only `01_intro` hits).
  It was evidently written for the Whispers story and orphaned when the arc pointed at
  the generic `01_intro.txt`. Its content overlaps the shipped `story_start` prose
  (same scene: Elian missing three days, the study).
- `01_intro.txt`, pasted verbatim (verified (read)):
  > You find yourself in a dimly lit room. A single flickering candle on a rickety wooden table is the only source of light. The air is damp and smells of old parchment and something else... something metallic. What do you do?

  It describes neither story (a "dimly lit room", not Elian's study or the thieves'
  den) and is doubly dead (overwritten by `story_start`, see above).
- `idea.txt` (53 lines) is an unedited LLM play-transcript of a *different* game —
  star-gates, a hovering crystalline object, "> You:" prompt lines
  (verified (read: idea.txt:1-53)). Referenced nowhere (verified (run: grep));
  commit history: added in 0bcac60 "story idea" (verified (run: git log --follow)).
  Pure scratch that ships in the package.

## Q7. Checkpoints vs estimates vs the loop

Arc data (verified (read) and (run: conf-checkpoints.py §B)):
whispers: `total_turns_estimate: 25` (arc:4), checkpoint turn 15 `prompt_injection`
(arc:21-22), turn 25 `force_end_game` + `flag_messages` on `elian_is_found` (arc:23-29).
clockwork: estimate 15 (arc:4), turn 10 injection (arc:21-22), turn 15
`force_end_game` + `flag_messages` on `has_temporal_gear` (arc:23-29).

Against game.py:347-377 (verified (read) and (run: conf-checkpoints.py §D/E)):
- The loop increments `turn_count` then compares `checkpoint["turn"] == current_turn`
  with **exact equality** (game.py:347-353). Probe: turn_count 9/11/14/16 match
  nothing; 10 and 15 match. Any skipped turn (save/resume edge, future changes)
  silently drops the checkpoint forever.
- `prompt_injection` checkpoints (turn 15 whispers, turn 10 clockwork) are **dead
  writes**: the injection is appended to `llm_instructions` at game.py:354-355, but
  that list is re-created fresh at game.py:284 on the next iteration and was already
  consumed by the continuation call at game.py:322-323 in the current one. The LLM
  never sees it. Same for the `force_end_game` checkpoint's injection (arc:25/arc:23).
  (The identical dead-write pattern affects `modify_prompt` from `story_start`:
  game.py:272 passes a throwaway `[]` and reads only `override_narrative` at 273-274,
  so whispers:21-22 and clockwork:19-20 guidance never reaches the LLM either.)
- `force_end_game` (game.py:356-377) works and bypasses the `game_ended` flag
  entirely (`return` at 377). A real ending beats it: `game_ended` breaks the loop at
  game.py:334-344 *before* the checkpoint block, so a story that reached `end_game`
  never runs its turn-N checkpoint (verified (run: conf-checkpoints.py §F)).
- `flag_messages` flag actually set? Whispers: `elian_is_found` is set by exactly one
  event action — whispers…yaml:199-200 (`rescue_elian`) — but that event is
  unreachable (Q3), so in practice the turn-25 message is always the
  `message_if_not_set` failure text (probe drove it: "Despite your best efforts…",
  conf-checkpoints §D). Clockwork: `has_temporal_gear` is set at clockwork…yaml:184-185
  and *is* reachable (probe: flags after "Take gear." include `has_temporal_gear`,
  conf-cascade §2), so the victory message selection works.
- Estimates are honest: 25/15 checkpoint == `total_turns_estimate` (arc:4 both), and
  `total_turns_estimate` is display-only (menu text, game.py:410); the real clock is
  the checkpoints.

## Q8. General events — false positives and once-global scope

`general_events.yaml` is merged into every story ahead of the story events
(yaml_loader.py:52-56), so its 6 events are always active.

| Event (lines) | Trigger | Action | Actual behaviour |
|---|---|---|---|
| `low_health_warning` (4-18) | `stat_check health <= 25` (9-12) | pre-inject + prompt | **Unreachable in both stories**: health starts 100 (arcs:9), the only health mutation is −20 (clockwork:272-274) → floor 80 (verified (run: conf-cascade §4)) |
| `inventory_full_warning` (20-30) | keywords take/pick up/grab/get (25-26) — **no inventory condition at all** | post-inject "Your hands are full…" (28-30) | Fires with an **empty** inventory and with an 11-item inventory alike (verified (run: conf-general §A/A2)). Substring matching (event_manager.py:194-197) makes "Examine the **tar-get**…" a hit (probe-verified); "Take the brass key." hits. Player sees the panel text after every matching turn, forever (not `once`) |
| `first_time_in_location` (33-45) | `turn_count_in_location == 1` (40-42), `once: true` (35-36) | `modify_prompt` "detailed description" (44-45) | Fires on the pre-choice check of the 2nd turn in a location, then **never again in any location**: `once` is recorded per event id (event_manager.py:77-78) and consulted globally (51-55). Probe over 5 `change_location`s: fired only in the first (verified (run: conf-general §B)). So a player gets the "detailed description" treatment exactly once per game |
| `long_time_in_location` (48-59) | `turn_count_in_location >= 5` (53-55), **not once** | pre-inject "You've been here for a while…" (57-59) | Repeats **every turn** from the 5th in a location (probe: fired at turns 5,6,7,8 — verified (run: conf-general §C)) |
| `help_command` (62-78) | keywords help / `?` / commands / "what can i do" (67-68) | `override_narrative` help screen with `•` bullets (70-78; the bullets are the encoding sweep item documented in load.md) | See Q9 |
| `debug_info` (81-91) | keywords debug/status/info (86-87) | post-inject "Debug info displayed in console." (89-90) | The message is false — nothing is displayed; the real `/debug` only prints when `DEBUG_MODE_ENABLED` (game.py:48-50, 210-211) |

## Q9. `help_command` / `debug_info` input paths — can the player ever type them?

No. `game.py:181` lowercases input, but the choice loop accepts **only** a digit in
range or a slash command (game.py:183-187); any typed word prints "Invalid choice."
(199) and never reaches `check_and_trigger_events`. The pre-choice event check passes
`""` as input (game.py:285-287), and `player_action_keyword` requires truthy input
(event_manager.py:193), so general events can never fire pre-choice. The only carrier
is the **LLM's choice label** passed post-choice (game.py:312-314): probe shows
"Ask the librarian for help." and even "Where do I go?" (contains `?`) trigger
`help_command`'s `override_narrative`, and "Gather more information." (contains
"info") triggers `debug_info` (verified (run: conf-general §D)). Consequence: the
"help system" is not player-callable; instead it *hijacks the turn* whenever an LLM
label happens to contain a keyword — the help panel replaces that turn's story
continuation (game.py:318-319). `/help` is not a command: `handle_command` implements
only `/save`, `/debug`, `/force_event`, `/quit` (game.py:208-215) and silently ignores
`/help`.

## Q10. Location and item name map (shipped content)

Locations (set = `change_location` action or arc `starting_location` consumed at
yaml_loader.py:82 / game.py:258):

| Name | Referenced in conditions | Set where | Verdict |
|---|---|---|---|
| `elian_study` | whispers 33, 85 | whispers 12 (story_start), arc:2 | OK |
| `saltstone_bluffs` | whispers 138, 166 | whispers 120 | OK |
| `crypt_antechamber` | whispers 191 | whispers 173 | OK |
| `thieves_den` | clockwork 31 | clockwork 12, arc:2 | OK |
| `museum_service_hall` | never | clockwork 68 | write-only destination (no event is gated on it — harmless) |
| `museum_main_hall` | never | clockwork 95 | write-only destination |
| `chronos_exhibition_hall` | clockwork 146, 176 | clockwork 127 | OK |
| `start` | never (only in loader defaults / tool template, yaml_loader.py:132, story_manager.py:160) | — | template default |

No location is referenced-but-never-set. Note the reverse hazard: three clockwork
events have **no** location condition (`enter_museum_stealth` 49-76,
`enter_museum_bold` 78-107, `find_temporal_gear_hall` 110-136), so their keywords can
teleport the player from anywhere.

Items (`inventory_has` reads `value:`, event_manager.py:203; `add_item` reads
`item_id:`, 111):

| Name | Tested by (`inventory_has`) | Granted by (`add_item`) | Verdict |
|---|---|---|---|
| `elians_journal` | whispers 61 | whispers 42 — wrong key → `None` | **never granted**; `read_journal_clue` dead |
| `runic_key` | whispers 195 | whispers 96 — wrong key → `None`; `remove_item` at 198 is a no-op on `[None]` | **never granted**; `rescue_elian` dead |
| `lockpicks` | clockwork 150 | arc:7 initial inventory | works; consumed at 157 |
| `smoke_bomb` | clockwork 212 | arc:7 initial inventory | works; consumed at 215 |
| `temporal_gear` | never tested | clockwork 187 — wrong key → `None` | granted as `None`; poisons `', '.join` (Q3) |

Clockwork's `add_item` defect (Q11): exactly one use, `steal_temporal_gear`
clockwork:186-187, `value: "temporal_gear"` → inventory `[..., None]`
(verified (run: conf-typo-additem PROBE 2, conf-cascade §2)). Unlike Whispers, no
condition depends on it, so all three escape endings remain reachable; the defect's
only effect is the `TypeError` crash risk if the player keeps playing after the theft
(game.py:130, outside the `try:` at 139; verified (run: conf-cascade §3)).

## Anatomy (content-layer form)

### Public surface — the schema contract an author codes against
Triggers (event_manager.py:185-250): `location`, `flag_set`, `flag_not_set`,
`player_action_keyword` (substring, case-insensitive, needs non-empty input),
`player_intent` (exact), `player_action` (exact, lowercased both sides),
`inventory_has`/`inventory_not_has` (`value:` key), `game_start` (turn_count==0),
`turn_count_in_location`, `turn_count_global`, `stat_check`. Modes: AND/OR/MANUAL
(173-174, 254-257). Actions (102-154): `set_flag`, `clear_flag`, `add_item`
(**`item_id:` key**), `remove_item` (`value:`), `change_location`, `update_stat`
(`stat`+`change_by`), `override_narrative` (`text`), `modify_prompt` (`instruction`),
`inject_narrative` (`text`+`position`), `add_choice` / `present_choices`
(`label`+`action`; `trigger:` prefix special-cased at game.py:193-195), `end_game`
(`success`, `message`). Options: only `once` is ever read (52, 77, 278) —
`priority` (DEVELOPER_GUIDE.md:74) is silently ignored (verified (read)).

### Key data structures (the event vocabulary actually used)
Census over all YAML (verified (run: conf-typo2.txt census)): conditions —
`player_action_keyword` ×18, `flag_not_set` ×15, `location` ×13, `flag_set` ×10,
`inventory_has` ×6, `turn_count_in_location` ×4, `game_start` ×3, `player_intent` ×3
(all legacy), `player_action` ×5, `stat_check` ×1, `flag_is_set` ×3 (all legacy, dead);
actions — `override_narrative` ×29, `set_flag` ×26, `modify_prompt` ×20,
`change_location` ×10, `end_game` ×5, `remove_item` ×4, `inject_narrative` ×4,
`add_item` ×5, `update_stat` ×2, `present_choices` ×2, `add_choice` ×1.
`turn_count_global` is documented (DEVELOPER_GUIDE.md:92, 377-385) and implemented
(event_manager.py:222-235) but used by zero shipped events.

### Invariants (what a story author must respect)
| Rule | Enforced where | Merely assumed by content |
|---|---|---|
| `add_item` needs `item_id:`; `value:` silently stores `None` | event_manager.py:111 (no validation) | **violated by all 3 shipped uses** (whispers 42, 96; clockwork 187) |
| `inventory_has` needs `value:` | event_manager.py:203 | **violated by legacy** chapter1:38-39, chapter3:35-36 |
| `remove_item` needs `value:` | event_manager.py:113 | legacy chapter3:38-39 uses `item_id:` (dead file) |
| unknown condition type ⇒ False; unknown action ⇒ ignored, no error | event_manager.py:184 (no else), 102-154 | `flag_is_set` ×3 |
| duplicate id ⇒ last loaded wins | event_manager.py:8 | would matter if the legacy dir were ever concatenated |
| `once` is per event id, global across locations | event_manager.py:51-55, 77-78 | `first_time_in_location` (general:35-36) assumes per-location |
| MANUAL events never auto-trigger | event_manager.py:173-174 | `story_start` must be forced by exact id at game.py:272 |
| choices only render from the *pre-choice* check | game.py:294 | `rescue_elian`'s `present_choices` fires post-choice ⇒ never renders |
| `end_game` overwrites any prior `override_narrative` unless `message:` given | event_manager.py:148-154 | all 5 ending events assume their prose shows |
| checkpoint `turn` matches by `==` after increment; `prompt_injection` is appended to a list already consumed | game.py:347-355 | both arcs' turn-15/10 injections assume they reach the LLM |
| `player_action_keyword` is substring match | event_manager.py:194-197 | `get` inside "target", `?` inside any question label |

### Dependencies out (engine lines that consume each field)
`options.once` → event_manager.py:52,77,278 · `trigger.mode` → 171-174, 254-257 ·
`trigger.conditions[].type/value/keywords/stat/operator` → 180-250 ·
`actions[].type/value/item_id/stat/change_by/text/instruction/position/label/action/choices/success/message`
→ 102-154 · arc fields → yaml_loader.py:66-91, game.py:264,352, main_menu 402-413 ·
`initial_inventory`/`initial_player_stats` → yaml_loader.py:66-69.

### Dependencies in (what references this content)
`load_story_and_player` concatenates `general_events.yaml` + `<story>_story_events.yaml`
(yaml_loader.py:48-63); discovery is `*_story_arc.yaml` glob (conf-reach §A);
`game_loop` forces `story_start` by name (game.py:272) and drives the two
check/consume rounds per turn (game.py:285-287, 313-315). The dead
`Whispers_of_the_Salted_Crypt/` directory is referenced only by egg-info SOURCES.txt
(conf-dup grep). `whispers_intro.txt` and `idea.txt` are referenced by nothing.

### Side effects
Content itself has none, but content *causes*: all persistent state changes via the
action dispatch (flags/locations/inventory/stats, event_manager.py:106-120); a
process-fatal `TypeError` via `None` in inventory (game.py:130); `SystemExit` via
`/quit` (game.py:214-215); save files only via `/save` (game.py:218-230).

### Error and edge behaviour
| Situation | What happens | Location |
|---|---|---|
| `add_item value:` | `None` appended, next prompt build raises `TypeError` uncaught | event_manager.py:111, gsm:27-29, game.py:130 |
| `flag_is_set` | event permanently dead, silent | event_manager.py:184 |
| `/force_event <typo>` | silent empty dict (the loud DEBUG banner lives in the *dead* first definition) | event_manager.py:268-275 vs dead 24-30 |
| missing intro file | narrative = "The story begins..." | game.py:268-269 |
| story arc missing | falls back to old-format dir scan; `ValueError` if empty | yaml_loader.py:43-45, 108-109 |
| LLM returns 0 or >4 choices | `ValueError` → generic fallback labels | game.py:156-165 |
| conditions empty / MANUAL | trigger can never fire | event_manager.py:173-177 |

### Lifecycle and concurrency
Not applicable: the YAML is static data re-read from disk on every `game_loop` entry
(game.py:239, 254); `EventManager` state (`triggered_event_ids`) lives and dies with
one playthrough and is saved/loaded wholesale (event_manager.py:12-16, game.py:227).
No locking, no threads.

### Configuration (per-story knobs)
Arc keys consumed: `title`, `starting_location`, `initial_story_part`,
`total_turns_estimate` (display only, game.py:410), `initial_inventory`,
`initial_player_stats`, `checkpoints`, `tags`, `difficulty`, `content_warnings`,
`author`, `version` (yaml_loader.py:82-91; menu rendering game.py:409-413).
Unenforced: nothing validates that `flag_messages` flags exist, that checkpoint turns
are unique/increasing, or that `initial_story_part` exists until first play
(game.py:265-269 swallows it).

### Extension points
A new story needs zero Python: `<id>_story_arc.yaml` + `events/<id>_story_events.yaml`
(with a MANUAL `story_start`) + the intro file — exactly what
`story_tool.py create` / `StoryManager.create_story_template` generates
(story_manager.py:155-256; verified (run: conf-intro §E, validation passes)). Gotcha
inherited from the template: its checkpoint tests flag `success`
(story_manager.py:175) and its generated events never set that flag
(story_manager.py:237-244 set only `looked_around`), so every generated story ends at
turn 20 with the failure message until the author adds a `set_flag success` — verified
(read) + (run: conf-intro §E arc listing).

### Tests
| Test file | What it actually asserts | Coverage notes |
|---|---|---|
| `tests/test_new_engine.py:15-42` | old-format load of a synthetic `game_setup.yaml` written in the test (ids/stats/inventory round-trip) | does **not** load any shipped YAML |
| `tests/test_new_engine.py:45-68` | `GameStateManager` add/remove/flag/stat mechanics on synthetic state | no YAML |
| `tests/test_new_engine.py:71-92` | one synthetic `location` event fires `set_flag` via the check path | no YAML |
| `tests/test_game_engine.py:15+` | same pattern, synthetic events | no YAML |
| `tests/test_game_basics.py` | `assert True` | nothing |

**No test loads `general_events.yaml`, either story events file, or either arc**
(verified (run: grep over tests/ for `whispers|clockwork|general_events|story_parts`
→ no hits). Every defect in this report is test-invisible.

### Surprises
- The story's second event breaks the process, not just the plot: `add_item value:`
  → inventory `[None]` → `TypeError` at game.py:130 outside the `try:` — Whispers
  hard-crashes the turn after the first scripted success. — whispers…yaml:41-42,
  game.py:130,139 — verified (run).
- The help screen is an LLM-label landmine, not a command: any generated choice
  containing `?`/`help`/`info`/`status`/`get`/`take` silently replaces or pollutes the
  turn via substring matching. — general_events.yaml:25-26, 67-68, 86-87;
  event_manager.py:194-197 — verified (run).
- Every ending's hand-written prose (338-586 chars each) is discarded and replaced by
  "The story ends here." because `end_game` runs after `override_narrative` without a
  `message:`. — event_manager.py:148-154; whispers:232-243, 257-269; clockwork:226-227,
  253-254, 282-283 — verified (run).
- The legacy chapter files are the *only* YAML using the engine's real `item_id:` key
  for `add_item` — the shipped files regressed the key while replacing
  `player_intent` with keywords. — chapter1:17-18,74-75 vs whispers:41-42,95-96 —
  verified (read).
- `event_manager.py` defines `execute_event_actions` twice; the loud "not found"
  DEBUG version (18-36) is dead, the silent one (260-281) wins, so `/force_event`
  typos fail silently and `once` is not honoured there. — verified (run: conf-endings
  §7).
- All `modify_prompt` guidance from `story_start` and all checkpoint
  `prompt_injection`s are written into lists nobody reads. — game.py:272-274,
  284, 322-323, 354-355 — verified (read).
- The arc files' `flag_messages` are checked by `for … break` over the list; only the
  first entry can ever decide the ending message unless its flag is set — fine with
  one entry each, fragile if extended. — game.py:360-369 — verified (read).

### Docs vs code
| Doc claim | Doc location | Code reality | Verdict |
|---|---|---|---|
| `priority` option on events | DEVELOPER_GUIDE.md:74 | never read; only `once` is | false (silent) |
| per-choice `condition:` in `present_choices` | DEVELOPER_GUIDE.md:363-365 | choices reduced to label/action; condition ignored | false (silent) |
| `turn_count_global` trigger | DEVELOPER_GUIDE.md:92, 377-385 | implemented but used by no shipped event | true but unused |
| General events give health warnings, location descriptions, help system, debug info, time-based events | README.md:225-231 | health warning unreachable; location description once per *game*; help not player-callable (hijacks `?` labels); debug message is false; time-based repeats every turn ≥5 | mostly false |
| `01_intro.txt` is "the default initial segment loaded by the game" | docs/architecture.md:28,44; docs/customization.md:56-58 | loaded then immediately overwritten by `story_start` override (game.py:272-274) | misleading |
| arc structure / event structure samples | README.md:53-106 | matches loader/engine fields | true |
| `player_action` = "Exact action match" | DEVELOPER_GUIDE.md:103 | exact, both sides lowercased | true (event_manager.py:200-201) |

### Unknowns
- Which choice labels a real Ollama/`phi4` model produces — and therefore how often
  keyword events (`?`, `get`, `search`, `take`…) fire in practice, and whether the
  player is ever offered a "search desk"-style label at the right moment — needs a
  live Ollama run (probes drive `EventManager` with hand-picked labels).
- `get_player_intent` (game.py:97-120) classification quality: irrelevant to shipped
  YAML (no `player_intent` conditions shipped) but decisive for the legacy files'
  design — needs a live model.
- Whether `story_tool create`'s `success`-flag gap was intended as an author exercise
  or an oversight — needs author intent (the generated arc + events are reproducible;
  verified (run)).
- Whether the `Whispers_of_the_Salted_Crypt/` directory and `idea.txt`/
  `whispers_intro.txt` are kept deliberately as reference material — git history shows
  `idea.txt` came in as "story idea" (0bcac60); needs author intent.

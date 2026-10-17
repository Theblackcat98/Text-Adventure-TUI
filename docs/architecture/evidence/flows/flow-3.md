# Text-Adventure-TUI: flow — FLOW-3, one turn of the game loop

Prefix: FLOW-3 · Sections touched: ENTRY, EVT, DATA, CONF
Question it answers: What happens in ONE turn of the game loop, in exact order — from `console.rule(Turn N)` to the next `console.rule`, including every LLM call, every event pass, and every counter update?

## Trigger

Entering `game_loop`'s `while True` at `text_adventure_tui_lib/game.py:276`. Reached from the main menu (new game: `game.py:435`, after the `story_start` bootstrap at `game.py:272-274`; resume: `game.py:451`). The loop runs until `break` (`game.py:344`, game_ended), `return` (`game.py:377`, checkpoint force-end), `SystemExit` (`/quit`, `game.py:215`), or an uncaught exception. All line numbers below are `game.py` unless prefixed otherwise — verified (read: game.py:276-377).

## Hop-by-hop trace

| # | Hop | Location | State read | State written | External effect |
|---|-----|----------|-----------|---------------|-----------------|
| 1 | Banner `Turn {N}` — N is the **pre-increment** count (first turn says `Turn 0`) | game.py:277; DATA `game_state_manager.py:52-53` | `turn_count` | — | console line — verified (run: f3-normal, one `Turn 0` banner per iteration, none after interrupt) |
| 2 | **LLM CALL #1 — `get_llm_options(narrative, gsm)`**. Prompt interpolates: situation = `narrative` (previous turn's continuation or intro), location, health, inventory (`game.py:127-137`; the f-string is built **outside** the `try:` at :139). Sent with `temperature 0.7` (:143) and `format="json"` (:144). Response `.strip()` (:146), ` ```json ` fence cleanup (:149), `json.loads` (:151), defaults `narrative_summary`=old narrative / `choices`=[] (:153-154), `ValueError` if 0 or >4 choices (:156-157) | game.py:280, 122-165 | `narrative`, gsm stats/inventory/location | **overwrites `narrative`** with `narrative_summary`; sets `choices` | ollama round-trip — verified (run: f3-normal — `format=='json'`, temps recorded; situation line = `CONT1` on turn 2, not `SUMM1`) |
| 3 | `display_story(narrative)` — shows the **summary**, which is then never used as context again | game.py:281, 60-68 | `narrative` | — | Story panel — verified (run: f3-normal — `SUMM1` shown; turn-2 prompt carries `CONT1`, `SUMM1` absent) |
| 4 | `llm_instructions = []` — **fresh list, only creation site** (after call #1 has already been sent: structurally impossible for instructions to reach the choices prompt) | game.py:284 | — | new list | — verified (read: game.py:284; run: f3-normal — `Important context` in 0 of 4 options prompts) |
| 5 | **PRE-CHOICE event pass** — `check_and_trigger_events(gsm, "", llm_instructions)`: `player_input_text=""`, `player_intent=""`. Fires on state-only conditions; `player_action_keyword` needs non-empty input (evt:193), `player_intent`/`player_action` compare `""` (fires only for an empty-string `value`, evt:198-201). `modify_prompt` appends into the **same** list (evt:123-124). An override result `break`s the pass (evt:80-81), skipping later events | game.py:285-287; EVT `event_manager.py:38-89,163-258` | flags, location, inventory, stats, `turn_count`, `turns_in_location`, `triggered_event_ids` | flags/items/stats/location via actions; `triggered_event_ids` (once, evt:77-78); appends into `llm_instructions` | console `DEBUG: Event … triggered!` (ungated, evt:60-62) — verified (run: f3-emptyinput 28-row matrix; f3-normal — game_start fires twice at turn 0, non-once location events fire in BOTH passes) |
| 6 | Pre-injections displayed — AFTER the summary despite the name "pre": "pre" means before the *choice*, not before the narrative | game.py:290-291 | pass result | — | Story panels — verified (read: game.py:281 vs :290-291; run: f3-normal order `SUMM1 → PRETEXT`) |
| 7 | `added_choices = pre-pass result` (**the only read of added_choices in the loop**); `get_player_choice` renders `choices + added labels` numbered 1..n and loops: `/`-commands → `handle_command` + `continue`; digit in range → label or event action; `trigger:` prefix → returns `("EVENT_TRIGGERED", id)`; non-`trigger:` action → the action **string** becomes the choice; everything else (all player free text) → `Invalid choice.` and re-list. Only digits and slash commands are accepted: typed text never reaches any trigger — the only "natural language" is LLM-authored labels and event-authored actions | game.py:294-297, 168-199, 202-215 | `choices`, `added_choices`, stdin | — | console menu; reads a line; slash commands may save/mutate — verified (run: f3-normal — "do a backflip" rejected, in no prompt; f3-choiceaction — `pet_the_cat` action string echoed and matched by `player_action`) |
| 8 | **EVENT_TRIGGERED branch** — `execute_event_actions(id, gsm, llm_instructions)` (the **live**, second definition, evt:260-281; marks `once` **before** running, :278-279). `narrative = event_results.get("override_narrative", narrative)` (:305) — **footgun**: the key is always present and `None` unless the event has an `override_narrative` action (evt:97,157,269-275), so the default never applies and **`narrative` becomes `None`**. `continue` → skips hops 9-14: no intent call, no continuation, **no `increment_turn`** | game.py:300-306 | `llm_instructions`, events dict | flags/items/etc.; `narrative` = override or **`None`** | event actions; no LLM — verified (run: f3-eventtriggered — single options call, banner `Turn 0` twice; f3-choiceaction — next turn's prompt situation is literally `None`, for missing id AND for found event without override) |
| 9 | Echo `> You chose: …` (skipped on the EVENT path) | game.py:309 | `player_choice` | — | console line — verified (run: f3-eventtriggered — no echo between pick and next banner) |
| 10 | **LLM CALL #2 — `get_player_intent`**, ALWAYS made on this path. temperature 0.2 (:113), output lowercased/underscored (:115); failure → `"unknown_intent"` (:118-120) | game.py:312, 97-120 | `player_choice` | `player_intent` local | ollama round-trip — verified (run: f3-normal — 1 intent call per normal turn; f3-errors E — graceful on exception) |
| 11 | **POST-CHOICE event pass** — same function, now `player_input_text=player_choice` (the label/action string), `player_intent` from call #2. `modify_prompt` appends land HERE (evt:124). Its `added_choices` and `injected_narratives_pre` are **dropped** (loop reads only `override_narrative` at :318 and `injected_narratives_post` at :330) | game.py:313-315 | + `player_intent` | same as hop 5 | same as hop 5 — verified (run: f3-override A/C — post-pass added choice never rendered; post-pass position:"pre" injection never displayed) |
| 12a | **Override branch** — truthiness test: `narrative = override`; continuation skipped (call #3 NOT made; instructions collected this turn die) | game.py:318-319 | pass result | `narrative` | — verified (run: f3-override B — 2 calls only; override text itself never displayed in its own turn) |
| 12b | **Continuation branch** — **LLM CALL #3** `get_llm_story_continuation(narrative, choice, llm_instructions)`: temperature 0.5 (:89), instructions joined into the prompt (:82-83) — **the only consumer of `llm_instructions`**. `narrative = outcome`; outcome displayed | game.py:322-327, 72-94 | `narrative`, `player_choice`, `llm_instructions` | `narrative` = outcome | ollama round-trip — verified (run: f3-normal — PRE-INSTR (pre pass) precedes POST-INSTR (post pass) in the same prompt; per-turn reset proven) |
| 13 | Post-injections displayed (post-pass result only) | game.py:330-331 | pass result | — | Story panels — verified (run: f3-override A — post-pass `pre` injection dropped) |
| 14 | **Game-end check** — `flags["game_ended"]` (set only by `end_game` actions, evt:148-154) → success/failure banner, `input()`, `break`. **Before** the increments: a game-ending turn is never counted | game.py:334-344 | flags | — | console banners; reads a line — verified (run: f3-counters-checkpoint C — no `Turn 1`, epilogue/message never displayed, one banner `Turn 0`) |
| 15 | **Counter increments** — `increment_turn()` (+1, gsm:55-56) then `increment_turns_in_location()` (+1, gsm:49-50). `turns_in_location` is reset to 0 only by an actual location change (`set_current_location`, gsm:44-47), so a no-move turn increments it | game.py:347-348 | counters | `turn_count`+1, `turns_in_location`+1 (or 0→1 after a move this turn) | — verified (run: f3-normal — `RESTLESS-2` (>=2) first fires in the iteration bannered `Turn 2`; f3-counters-checkpoint A — same) |
| 16 | **Checkpoint scan** — `current_turn = get_turn_count()` (now ≥1) ; for each `story.checkpoints` with `checkpoint["turn"] == current_turn`: `prompt_injection` appended to `llm_instructions` (:355) — **dead write on both paths** (force-end returns now; otherwise `:284` recreates the list before any consumer). `force_end_game` → flag_messages scan (first entry whose flag matches set/not-set wins, :360-369), message displayed, banner, `input()`, `return` | game.py:351-377 | `story.checkpoints`, flags, `turn_count` | appends to doomed list | console; reads a line — verified (run: f3-counters-checkpoint A — `CKPT-INJ`/`CKPT4-INJ` in 0 prompts, `LOST-MSG` shown, clean return after 4 full turns; B — `WON-MSG` when flag set; D — `turn: 0` never fires) |

## Diagram

```text
                        ┌──────────────────────────────────────────────────────────┐
                        │ while True (game.py:276)                                 │
                        └──────────────────────────────────────────────────────────┘
                                          │
        ┌─────────────────────────────────▼──────────────────────────────────────┐
        │ 1. console.rule("Turn N")          game.py:277   N = turn_count (gsm:52)│
        │ 2. LLM#1 get_llm_options           game.py:280   narrative ← summary   │
        │     prompt: situation/location/health/inventory  game.py:127-137        │
        │     format="json", temp 0.7        game.py:143-144                      │
        │ 3. display_story(summary)          game.py:281                          │
        │ 4. llm_instructions = []           game.py:284   (only creation site)   │
        │ 5. PRE pass  check_and_trigger_events(game.py:285) input="" intent=""   │
        │     event_manager.py:38-89 · modify_prompt→append (evt:124)             │
        │     override ⇒ break (evt:80-81) — result DISCARDED by game.py          │
        │ 6. display pre-injections          game.py:290-291                      │
        │ 7. get_player_choice               game.py:294-297, 168-199             │
        └───────────┬────────────────────────────────────────────────────────────┘
             digit  │        digit on added choice
   ┌────────────────▼──────┐   ┌──────────────────────────────────────────────┐
   │ label (LLM choice)    │   │ action "trigger:<id>" ⇒ ("EVENT_TRIGGERED",id)│
   │ or non-trigger action │   │ game.py:193-195                               │
   └───────────┬───────────┘   └──────────────┬───────────────────────────────┘
               │                              ▼
               │                 ┌────────────────────────────────────────────┐
               │                 │ 8. EVENT branch  game.py:300-306            │
               │                 │    execute_event_actions (live evt:260-281; │
               │                 │    once marked BEFORE actions evt:278-279)  │
               │                 │    narrative ← .get("override_narrative",   │
               │                 │       narrative)  ⇒ None unless override!   │
               │                 │    continue ⇒ NO intent/continuation/       │
               │                 │    NO increment_turn (counter frozen)       │
               │                 └──────────────┬──────────────────────────────┘
               │                                │ (back to top)
               ▼                                │
   ┌───────────────────────────────────────────│──────────────────────────────┐
   │ 9.  echo "> You chose"      game.py:309   │                              │
   │ 10. LLM#2 get_player_intent game.py:312   temp 0.2  (always)             │
   │ 11. POST pass check_and_trigger_events    game.py:313-315                │
   │       input=label, intent=keyword; modify_prompt appends land HERE       │
   │       (added_choices + injected_pre of THIS pass are dropped)            │
   │ 12. override?  game.py:318-319            ├─ yes: narrative ← override,  │
   │       (truthiness test)                   │       NO LLM#3, 2 calls/turn │
   │     else LLM#3 get_llm_story_continuation ◄┘  game.py:322-327, temp 0.5,  │
   │       ONLY consumer of llm_instructions (game.py:82-83, :323);           │
   │       narrative ← outcome; display outcome                               │
   │ 13. display post-injections game.py:330-331                              │
   │ 14. game_ended?  game.py:334-344 ── yes ─► banners, input(), BREAK       │
   │       (flags set only by end_game action, evt:148-154; message/epilogue  │
   │        never displayed; ending turn never counted)                       │
   │ 15. increment_turn + increment_turns_in_location   game.py:347-348       │
   │       (location change zeroed it earlier: gsm:44-47)                     │
   │ 16. checkpoints: story.checkpoints[turn == turn_count]  game.py:351-377  │
   │       prompt_injection → append (DEAD: list recreated next turn :284)    │
   │       force_end_game → flag_messages (:360-369), display, input(),       │
   │       RETURN (game.py:377) — back to menu                                │
   └──────────────────────────────────────────────────────────────────────────┘
```

## Per-turn LLM-call ledger

| Turn shape | Calls | Sequence (in order) | Evidence |
|---|---|---|---|
| Normal (label chosen, no override) | **3** | options (0.7/json) → intent (0.2) → continuation (0.5) | verified (run: f3-normal — `["options","intent","continuation"] ×3`) |
| Post-choice override | **2** | options → intent (continuation skipped at :318) | verified (run: f3-override B — `["options","intent"]`) |
| EVENT_TRIGGERED (`trigger:` choice) | **1** | options only (`continue` at :306 precedes :312) | verified (run: f3-eventtriggered — single options call, frozen counter) |
| Game-ending turn (any of the three shapes above) | same as shape | end check (:334) / force-end (:356) precede increments, but all calls of that shape already ran | verified (run: f3-counters-checkpoint C — 3 calls then banner, no `Turn 1`) |

Instruction consumers: options and intent prompts can never contain `llm_instructions` (list created at :284 after :280; different signatures). The continuation prompt is the only consumer; it receives pre-pass appends **then** post-pass appends of the same turn, in that order — verified (run: f3-normal, f3-override A). On override turns, EVENT turns, and at checkpoint time (:355 vs :284), instructions are collected and then silently destroyed — verified (run: f3-override A for the surviving-instruction contrast; f3-counters-checkpoint A for checkpoint injections in 0/24 prompts).

## Decision branches

| Condition | Location | Branch taken | Consequence |
|---|---|---|---|
| choice is `/…` | game.py:183-185 | command dispatch, `continue` | `/save`/`/debug`/`/force_event`/`/quit`; menu re-listed — verified (run: f3-normal, 6 menus) |
| digit, index < len(choices) | game.py:189-190 | return (label, None) | normal path, 3 LLM calls |
| digit on added choice, action `trigger:`-prefixed | game.py:193-195 | return ("EVENT_TRIGGERED", id) | hop 8; 1 call; counter frozen; `narrative` risk of `None` |
| digit on added choice, other action | game.py:196-197 | return (action string, None) | action text treated as the choice — verified (run: f3-choiceaction) |
| anything else typed | game.py:199 | `Invalid choice.`, loop | free text never becomes input — verified (run: f3-normal) |
| pre-pass produces override | evt:80-81 + game.py (never read) | break pass; **override discarded** | event ordered later skipped that pass — verified (run: f3-override A/C) |
| post-pass produces override | game.py:318-319 | narrative ← override; skip LLM#3 | 2 calls; text shown only as next turn's LLM input — verified (run: f3-override B) |
| `game_ended` flag | game.py:334 | banners + `input()` + `break` | turn not counted; message text never displayed — verified (run: f3-counters-checkpoint C) |
| checkpoint `turn == turn_count` (after increment) | game.py:353 | injection append (dead) / force_end | force_end: `input()` + `return`; fires at end of the iteration bannered N-1 — verified (run: f3-counters-checkpoint A/D) |
| `once` event | evt:51-55, 77-78, 278-279 | skip if already triggered; mark after natural firing, **before** forced firing | `trigger:` path consumes the single firing — verified (read + EVT probes) |

## Error branches

| Failure | Location | Surfaced as | Recovery |
|---|---|---|---|
| ollama down/raises during call #1 | game.py:161-163 | **`UnboundLocalError: raw_json_str`** escapes `game_loop` (bound only at :146; the `except` prints it at :163); 4-choice fallback at :165 NOT reached; process dies | none — verified (run: f3-errors A, `ConnectionError` injected) |
| >4 / 0 choices, or unparseable JSON | game.py:149-157 → :161-165 | error line + (debug-gated) raw response; fallback `(current_narrative, ["Look around.","Check inventory.","Wait.","Leave."])` | turn continues normally — verified (run: f3-errors B/C/D) |
| intent call raises | game.py:118-120 | error line; `"unknown_intent"` | turn continues (3 calls) — verified (run: f3-errors E) |
| continuation call raises | game.py:92-94 | error line; `"The path forward is hazy..."` **becomes `narrative`** (next turn's LLM context) | turn continues — verified (run: f3-errors F) |
| `KeyboardInterrupt`/EOF at choice `Prompt.ask` | game.py:181 | propagates out of `game_loop`/`main_menu` (no handler anywhere), after call #1 was already spent | process exit — verified (run: f3-errors G; EOF per ENTRY section probe) |
| `KeyboardInterrupt` at the bare `input()` (either ending) | game.py:343, :376 | propagates; crash after the banner | process exit — verified (run: f3-errors H) |
| `trigger:` id not found, or event without override action | game.py:305 + evt:269-275/:157 | silent; `narrative` becomes `None` → next turn's prompt says situation `'None'` | none (silent corruption) — verified (run: f3-choiceaction, both cases) |
| raising action mid-event (e.g. `update_stat` missing `change_by`) | evt:102-154 (no try/except) | remaining actions skipped; exception kills the loop | none (per EVT section probes) |

## State mutations (one normal turn)

- `turn_count` += 1 (`game.py:347` → gsm:55-56) — observable in the next banner and in prompt situation lines; saved by `/save` (game.py:226).
- `turns_in_location` += 1 (:348 → gsm:49-50) — reset to 0 only by `change_location` to a *different* location (gsm:44-47) — verified (run: f3-normal `turn_count_in_location >= 2` timing).
- `narrative` (local): intro → **summary** (call #1, :280) → **outcome** (call #3, :326) [or override, :319; or `None`, :305]. Only the final value of the iteration survives into the next one — verified (run: f3-normal chain `CONT1` → prompt → `CONT2`).
- `llm_instructions` (local): created empty (:284), grown by `modify_prompt` in pre pass then post pass, consumed only by call #3, destroyed at next :284 — verified (run: f3-normal counts).
- Event-authored mutations (flags, inventory, stats, location, `triggered_event_ids`) — as in FLOW-4; on this flow they can happen up to **three times per turn** (pre pass, post pass, forced execution), so a non-`once` location event fires twice per turn — verified (run: f3-normal — 2 `triggered!` lines per turn per location event).

## To change this flow

- **Let event instructions steer the choices prompt** (they structurally cannot today): move `llm_instructions = []` (game.py:284) above the `get_llm_options` call (:280), add an `instructions` parameter to `get_llm_options` (game.py:122), and join it into the prompt near :131. Also fix the three dead-consumer paths first (:305's `None`, :318's skip, :355's checkpoint append) or instructions will still vanish on those shapes.
- **Make an Ollama outage survivable**: bind `raw_json_str = ""` before the `try:` in `get_llm_options` (game.py:139-146) or guard the debug print at :163 — the fallback at :165 already handles parse/count failures (proven by f3-errors B/C/D) and would then also cover connection errors.
- **Fix the frozen/None EVENT branch**: in `execute_event_actions`' not-found return (event_manager.py:269-275) and `_perform_actions` (evt:156-161), drop the `override_narrative` key when no override ran (or use `event_results.get("override_narrative") is not None` at game.py:305 like the truthiness test at :318) so `narrative` is never set to `None`; and decide whether `EVENT_TRIGGERED` turns should call `increment_turn()` (:300-306) — today they freeze the counter, which also starves `game_start`/`turn_count_global` events.
- **Re-time checkpoints**: to make `prompt_injection` reach the LLM, evaluate checkpoints at the TOP of the iteration (before :280) or append into a list created before the call; to make `checkpoint["turn"] N` line up with the banner that says `Turn N`, scan before incrementing (:347 vs :351-353).

## Unknowns

- Which exception type a real downed Ollama raises through `ollama==0.2.1` (probe injected `ConnectionError`; any exception triggers the same ULE path) — needs a live Ollama server.
- Real `player_intent` keyword strings from `phi4:latest` and therefore whether any shipped `player_intent`-conditioned event can fire in live play (all intent routing here was driven by a stub returning `search_desk`) — needs a live server + model.
- Whether `format="json"` is honoured by the default model and what real per-turn latency of 3 sequential round-trips feels like — needs a live server.
- Whether `Text(None)` at game.py:63 renders "None" or misbehaves on other rich versions (observed no crash and a `'None'` situation line under rich in this environment; panel content not asserted) — needs a display-level check on the target rich version.
- behaviour of `choices` numbering when the LLM returns duplicated/empty labels (empty strings would render but remain selectable) — untested; needs a stub returning pathological labels.

## Probe index (this flow)

All under `/tmp/opencode/cdd-text-adventure-tui/flows/`, run from the repo root with `PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI:<flows>` (stale site-packages copy shadowed; `ollama_client` stubbed with a recording fake driving the real `game_loop`; story injected by monkeypatching `load_story_and_player` so no repo file is touched):

| Probe | Covers | Result |
|---|---|---|
| `f3-common.py` | harness: FakeOllama/FakePrompt/FakeInput, call classification by prompt shape | — |
| `f3-normal.py` | 3 normal turns: order, temps, format, prompt contents, overwrite chain, instruction lifecycle, free-text rejection, command branch, both-pass firing, `game_start` double fire, counter timing | all checks passed |
| `f3-eventtriggered.py` | EVENT branch: 1 call, frozen counter, no echo, live def silence, dead `TRIG-INSTR`, override → next prompt | all checks passed |
| `f3-override.py` | run A once-pre-override discarded + post-pass `pre` injection dropped; run B non-once re-fire applies; run C dict-order shadowing | all checks passed |
| `f3-counters-checkpoint.py` | checkpoint timing/deadness, flag_messages set/unset, `turn: 0`, game_ended break path, epilogue clobber never shown | all checks passed |
| `f3-emptyinput.py` | 28-row condition matrix at empty input/intent + label-matching in post pass | all checks passed |
| `f3-errors.py` | ULE crash, >4/0/non-JSON fallbacks, intent/continuation graceful strings, KeyboardInterrupt ×2 | all checks passed |
| `f3-choiceaction.py` | non-trigger action string routing, `trigger:` unknown id, `narrative=None` poisoning (missing id AND no-override event) | all checks passed |

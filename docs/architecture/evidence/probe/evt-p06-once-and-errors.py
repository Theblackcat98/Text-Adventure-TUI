"""Probe: once-consumption, /force_event, exception mid-action-list, re-entrancy,
present_choices key handling, end_game, result-dict identity."""
import inspect
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

console = Console(quiet=True)
story = Story(id="t", title="t")


def mk(events):
    gs = GameState(current_story=story, player=Player(stats={"health": 50}),
                   flags={}, turn_count=0, current_location="start", turns_in_location=0)
    return EventManager(events, console), GameStateManager(gs), gs


def ev(id_, actions, options=None, trigger=None):
    return Event(id=id_, name="", trigger=trigger or {"mode": "MANUAL"},
                 actions=actions, options=options or {})


print("### 1) once consumed by execute_event_actions (event_manager.py:277-279)")
evs = [ev("once_ev", [{"type": "set_flag", "value": "fired"}], {"once": True})]
em, gsm, gs = mk(evs)
em.execute_event_actions("once_ev", gsm, [])
print("  after forced run  -> triggered_event_ids =", em.triggered_event_ids,
      " flags =", gs.flags)
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  natural trigger   -> override =", r["override_narrative"],
      " (event can never fire on its own again)")

print("\n### 2) same event forced TWICE (no idempotency guard)")
em2, gsm2, gs2 = mk(evs)
em2.execute_event_actions("once_ev", gsm2, [])
em2.execute_event_actions("once_ev", gsm2, [])
print("  flags after two forced runs =", gs2.flags)

print("\n### 3) non-once event: forced run leaves triggered_event_ids empty")
evs3 = [ev("loop_ev", [{"type": "inject_narrative", "text": "tick"}], {},
           {"mode": "AND", "conditions": [{"type": "player_action", "value": "go"}]})]
em3, gsm3, gs3 = mk(evs3)
em3.execute_event_actions("loop_ev", gsm3, [])
print("  triggered_event_ids =", em3.triggered_event_ids,
      " natural trigger still fires:",
      em3.check_and_trigger_events(gsm3, "go", [], "")["injected_narratives_post"])

print("\n### 4) exception mid action-list")
bad = [ev("boom", [{"type": "set_flag", "value": "a"},
                   {"type": "update_stat", "stat": "health"},
                   {"type": "set_flag", "value": "c"}])]
em4, gsm4, gs4 = mk(bad)
try:
    em4.execute_event_actions("boom", gsm4, [])
except Exception as e:
    print("  RAISES", type(e).__name__, ":", e)
print("  flags after the raise =", gs4.flags, " -> 'c' never ran; no try/except")

print("\n### 4b) change_by present but non-numeric (YAML 'ten')")
em5, gsm5, gs5 = mk([ev("b2", [{"type": "update_stat", "stat": "health",
                                "change_by": "ten"}])])
try:
    em5.execute_event_actions("b2", gsm5, [])
except Exception as e:
    print("  RAISES", type(e).__name__, ":", e)

print("\n### 4c) stat key absent entirely")
em6, gsm6, gs6 = mk([ev("b3", [{"type": "update_stat", "change_by": 5}])])
try:
    em6.execute_event_actions("b3", gsm6, [])
except Exception as e:
    print("  RAISES", type(e).__name__, ":", e)
print("  stats dict now =", gs.player.stats)

print("\n### 4d) well-formed update_stat")
em7, gsm7, gs7 = mk([ev("ok", [{"type": "update_stat", "stat": "health",
                                "change_by": -20}])])
em7.execute_event_actions("ok", gsm7, [])
print("  health =", gs.player.stats)

print("\n### 5) present_choices: text: and condition: are dropped")
pc = [ev("pc", [{"type": "present_choices", "text": "What do you do?",
                 "choices": [
                     {"label": "Use the ancient key", "action": "unlock_door",
                      "condition": {"type": "inventory_has", "value": "ancient_key"}},
                     {"label": "Pick the lock", "action": "pick_lock"}]}]),
      ev("pc2", [{"type": "add_choice", "label": "L", "action": "A",
                  "text": "ignored"}])]
em8, gsm8, gs8 = mk(pc)
r = em8.execute_event_actions("pc", gsm8, [])
print("  keys returned  :", sorted(r.keys()))
print("  added_choices  :", r["added_choices"])
print("  override_narr. :", r["override_narrative"], "<- the `text:` key is discarded")
print("  add_choice     :", em8.execute_event_actions("pc2", gsm8, [])["added_choices"])

print("\n### 6) end_game: default message wins over an earlier override_narrative")
eg = [ev("eg", [{"type": "override_narrative", "text": "NARRATIVE FROM EVENT"},
                {"type": "end_game", "success": True}])]
em9, gsm9, gs9 = mk(eg)
r = em9.execute_event_actions("eg", gsm9, [])
print("  override_narrative ->", repr(r["override_narrative"]), " flags ->", gs9.flags)
eg2 = [ev("eg2", [{"type": "end_game", "success": False, "message": "You drowned."}])]
em10, gsm10, gs10 = mk(eg2)
r = em10.execute_event_actions("eg2", gsm10, [])
print("  explicit message   ->", repr(r["override_narrative"]), gs10.flags)

print("\n### 7) modified_prompt_instructions identity")
lst = ["x"]
evs7 = [ev("m", [{"type": "modify_prompt", "instruction": "note"}], {},
           {"mode": "AND", "conditions": [{"type": "player_intent", "value": "i"}]})]
em11, gsm11, gs11 = mk(evs7)
r = em11.check_and_trigger_events(gsm11, "txt", lst, "i")
print("  returned object IS the caller's list:", r["modified_prompt_instructions"] is lst)
print("  list after the call =", lst)
em12, _, _ = mk([])
print("  forced unknown event returns keys  :",
      sorted(em12.execute_event_actions("nope", gsm11, []).keys()))
print("  (that dict has modified_prompt_instructions; _perform_actions' does not)")

print("\n### 8) re-entrancy of _perform_actions")
src = inspect.getsource(EventManager._perform_actions)
print("  mentions check_and_trigger_events:",
      "check_and_trigger_events" in src)
print("  mentions execute_event_actions    :", "execute_event_actions" in src)
print("  mentions _perform_actions         :", "_perform_actions" in src)
print("  has try/except                    :", "try" in src)

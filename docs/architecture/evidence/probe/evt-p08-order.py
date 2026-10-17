"""Probe: multi-event ordering, break-on-override, flag-before-condition chain,
duplicate-id collision, MANUAL/game_start deadness."""
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

console = Console(quiet=True)


def ev(id_, conds, actions, options=None, mode="AND"):
    return Event(id=id_, name="", trigger={"mode": mode, "conditions": conds},
                 actions=actions, options=options or {})


def mk(events, loc="start", turn=0, til=0, flags=None):
    story = Story(id="t", title="t")
    gs = GameState(current_story=story, player=Player(), flags=dict(flags or {}),
                   turn_count=turn, current_location=loc, turns_in_location=til)
    return EventManager(events, console), GameStateManager(gs), gs


print("### A) event A sets flag, event B tests it - only works if A comes first")
A = ev("A_set_flag", [{"type": "location", "value": "start"}],
       [{"type": "set_flag", "value": "knows_about_bluffs"},
        {"type": "add_item", "item_id": "runic_key"}])
B = ev("B_test_flag", [{"type": "flag_set", "value": "knows_about_bluffs"},
                       {"type": "inventory_has", "value": "runic_key"}],
       [{"type": "override_narrative", "text": "B FIRED"}])
em, gsm, gs = mk([A, B])
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  order [A, B] -> override:", r["override_narrative"], " flags:", gs.flags)
em, gsm, gs = mk([B, A])
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  order [B, A] -> override:", r["override_narrative"], " flags:", gs.flags)

print("\n### B) non-override events all fire in one pass (break only on override)")
chain = [ev("f1", [{"type": "location", "value": "start"}],
            [{"type": "set_flag", "value": "a"}]),
         ev("f2", [{"type": "flag_set", "value": "a"}],
            [{"type": "set_flag", "value": "b"}]),
         ev("f3", [{"type": "flag_set", "value": "b"}],
            [{"type": "set_flag", "value": "c"}]),
         ev("f4", [{"type": "flag_set", "value": "c"}],
            [{"type": "inject_narrative", "text": "pre", "position": "pre"},
             {"type": "inject_narrative", "text": "post"}])]
em, gsm, gs = mk(chain)
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  flags:", sorted(gs.flags), " pre:", r["injected_narratives_pre"],
      " post:", r["injected_narratives_post"])

print("\n### C) an override_narrative mid-list stops everything after it")
mid = [ev("m1", [{"type": "location", "value": "start"}],
         [{"type": "set_flag", "value": "a"}]),
       ev("m2", [{"type": "location", "value": "start"}],
         [{"type": "override_narrative", "text": "STOP"}]),
       ev("m3", [{"type": "location", "value": "start"}],
         [{"type": "set_flag", "value": "never"}])]
em, gsm, gs = mk(mid)
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  override:", r["override_narrative"], " flags:", sorted(gs.flags),
      " -> m3 never evaluated")

print("\n### C2) a SECOND override in the same pass overwrites the first")
two = [ev("o1", [{"type": "location", "value": "start"}],
          [{"type": "override_narrative", "text": "FIRST"}]),
       ev("o2", [{"type": "location", "value": "start"}],
          [{"type": "override_narrative", "text": "SECOND"}]),
       ev("o3", [{"type": "location", "value": "start"}],
          [{"type": "set_flag", "value": "never"}])]
em, gsm, gs = mk(two)
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  override:", r["override_narrative"], " flags:", sorted(gs.flags))
print("  NOTE: the loop breaks after the FIRST override, so SECOND wins only")
print("        because event_manager.py:68 overwrites before the break at :81")

print("\n### D) duplicate id: last one wins, position of FIRST insertion kept")
dup = [ev("dup", [{"type": "location", "value": "start"}],
          [{"type": "override_narrative", "text": "FROM GENERAL"}]),
       ev("other", [{"type": "location", "value": "start"}],
          [{"type": "set_flag", "value": "o"}]),
       ev("dup", [{"type": "location", "value": "start"}],
          [{"type": "override_narrative", "text": "FROM STORY"}])]
em, gsm, gs = mk(dup)
print("  dict keys in order:", list(em.events.keys()))
r = em.check_and_trigger_events(gsm, "x", [], "")
print("  override:", r["override_narrative"],
      " -> the story copy survives; the general copy is unreachable")
print("  'other' still fired:", "o" in gs.flags)

print("\n### E) MANUAL and empty-conditions are permanently dead")
manual = [ev("man", [{"type": "game_start"}], [{"type": "set_flag", "value": "m"}],
             mode="MANUAL")]
em, gsm, gs = mk(manual)
print("  MANUAL event via check_and_trigger_events ->",
      em.check_and_trigger_events(gsm, "x", [], "")["override_narrative"], gs.flags)
nocond = [ev("nc", [], [{"type": "set_flag", "value": "n"}])]
em, gsm, gs = mk(nocond)
print("  event with no conditions ->",
      em.check_and_trigger_events(gsm, "x", [], "")["override_narrative"], gs.flags)
gs_start = [ev("gs", [{"type": "game_start"}], [{"type": "set_flag", "value": "g"}])]
em, gsm, gs = mk(gs_start, turn=0)
print("  game_start event at turn_count==0 via the pass ->",
      em.check_and_trigger_events(gsm, "x", [], "")["override_narrative"], gs.flags)
em, gsm, gs = mk(gs_start, turn=1)
print("  same event at turn_count==1 ->",
      em.check_and_trigger_events(gsm, "x", [], "")["override_narrative"], gs.flags)
print("  (game.py:272 forces story_start BEFORE the loop, but turn_count is still 0,")
print("   so a second game_start event WOULD also fire in the first pre-choice pass)")
em, gsm, gs = mk(gs_start, turn=0)
em.check_and_trigger_events(gsm, "", [], "")
em.check_and_trigger_events(gsm, "x", [], "")
print("  at turn 0 the pass runs twice (game.py:285 and game.py:313): flags =", gs.flags)

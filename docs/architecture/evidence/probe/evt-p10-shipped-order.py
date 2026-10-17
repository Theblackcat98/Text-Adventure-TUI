"""Probe: is the multi-event pass order-dependent? Shipped YAML evidence."""
import copy
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)
SP = Path("text_adventure_tui_lib/story_parts")


def build(events, loc="start", turn=0, til=0, flags=None, inv=None):
    story = Story_ = None
    from text_adventure_tui_lib.data_structures import Story, Player
    story = Story(id="t", title="t")
    gs = GameState(current_story=story, player=Player(inventory=list(inv or [])),
                   flags=dict(flags or {}), turn_count=turn,
                   current_location=loc, turns_in_location=til)
    return EventManager(events, console), GameStateManager(gs), gs


story, player = load_story_and_player("whispers_of_the_salted_crypt", SP)
RAW = story.events

print("### 1) enter_the_crypt (whispers:158) -> rescue_elian (whispers:183)")
print("    enter_the_crypt sets location=crypt_antechamber (yaml:172-173);")
print("    rescue_elian tests location==crypt_antechamber (yaml:190-191).")
em, gsm, gs = build(RAW, loc="saltstone_bluffs", flags={"tide_is_low": True},
                    inv=["runic_key"], til=3)
r = em.check_and_trigger_events(gsm, "enter archway", [], "go_to")
print("    one pass -> override:", str(r["override_narrative"])[:44])
print("    location now:", gsm.get_current_location(),
      "| rescue_elian evaluated?",
      "rescue_elian" in em.triggered_event_ids)
print("    -> its location condition was TRUE after :115 but the break at :80-81")
print("       stopped the loop before rescue_elian was reached.")

print("\n### 2) same pair, input that matches ONLY rescue_elian")
em, gsm, gs = build(RAW, loc="crypt_antechamber", flags={"tide_is_low": True},
                    inv=["runic_key"], til=3)
r = em.check_and_trigger_events(gsm, "use key", [], "use_item")
print("    override:", str(r["override_narrative"])[:44],
      "| inv:", gs.player.inventory,
      "| triggered:", sorted(em.triggered_event_ids))

print("\n### 3) arrive_at_bluffs (yaml:119-120) -> tide_recedes (yaml:137-141)")
em, gsm, gs = build(RAW, loc="elian_study", flags={"knows_about_bluffs": True},
                    til=9)
print("    before: turns_in_location =", gsm.game_state.turns_in_location)
r = em.check_and_trigger_events(gsm, "go to bluffs", [], "go_to")
print("    after one pass: loc =", gsm.get_current_location(),
      " turns_in_location =", gsm.game_state.turns_in_location)
print("    tide_is_low set?", gsm.get_flags().get("tide_is_low"),
      "-> location matched (location was changed by event A mid-pass), but")
print("       change_location reset turns_in_location to 0 (gsm:44-47), so")
print("       tide_recedes' '>= 3' failed. That is the ONLY thing stopping it.")

print("\n### 4) same, but tide_recedes evaluated with turns_in_location already 0")
em, gsm, gs = build(RAW, loc="elian_study", flags={"knows_about_bluffs": True},
                    til=9)
tr = [e for e in RAW if e.id == "tide_recedes"][0]
ab = [e for e in RAW if e.id == "arrive_at_bluffs"][0]
e2 = copy.deepcopy(tr)
e2.trigger["conditions"] = [{"type": "location", "value": "saltstone_bluffs"},
                             {"type": "turn_count_in_location",
                              "value": 0, "operator": ">="},
                             {"type": "flag_not_set", "value": "tide_is_low"}]
em, gsm, gs = build([ab, e2], flags={"knows_about_bluffs": True}, til=9)
r = em.check_and_trigger_events(gsm, "go to bluffs", [], "go_to")
print("    override:", str(r["override_narrative"])[:44],
      "| tide_is_low =", gsm.get_flags().get("tide_is_low"))
print("    -> PROOF that event A's change_location satisfies event B's `location`")
print("       condition inside the SAME pass; only the turn counter blocked it.")

print("\n### 5) read_journal_clue (yaml:60-61) needs inventory_has elians_journal")
fixed = copy.deepcopy(RAW)
for e in fixed:
    for a in e.actions:
        if a.get("type") == "add_item" and "value" in a and "item_id" not in a:
            a["item_id"] = a.pop("value")
em, gsm, gs = build(fixed, loc="elian_study", til=0)
r = em.check_and_trigger_events(gsm, "search desk and then read journal", [], "i")
print("    with the add_item key fixed, ONE input fires both events:")
print("    override:", str(r["override_narrative"])[:52])
print("    flags:", sorted(gs.flags), " inv:", gs.player.inventory)
print("    -> event A (:39-42) must run before event B (:60-61) in the dict order")
print("       for `inventory_has` to be satisfied in the same pass.")

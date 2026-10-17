"""Probe: same-pass propagation when the earlier event does NOT produce an override."""
import copy
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)
story, player = load_story_and_player(
    "whispers_of_the_salted_crypt", Path("text_adventure_tui_lib/story_parts"))
RAW = story.events


def build(events, loc="start", turn=0, til=0, flags=None, inv=None):
    s = Story(id="t", title="t")
    gs = GameState(current_story=s, player=Player(inventory=list(inv or [])),
                   flags=dict(flags or {}), turn_count=turn,
                   current_location=loc, turns_in_location=til)
    return EventManager(events, console), GameStateManager(gs), gs


def strip_override(ev):
    e = copy.deepcopy(ev)
    e.actions = [a for a in e.actions if a.get("type") != "override_narrative"]
    return e


print("### 4b) arrive_at_bluffs with its override_narrative removed")
ab = strip_override([e for e in RAW if e.id == "arrive_at_bluffs"][0])
tr = copy.deepcopy([e for e in RAW if e.id == "tide_recedes"][0])
tr.trigger["conditions"] = [{"type": "location", "value": "saltstone_bluffs"},
                            {"type": "turn_count_in_location", "value": 0,
                             "operator": ">="},
                            {"type": "flag_not_set", "value": "tide_is_low"}]
em, gsm, gs = build([ab, tr], flags={"knows_about_bluffs": True}, til=9)
r = em.check_and_trigger_events(gsm, "go to bluffs", [], "go_to")
print("    loc:", gsm.get_current_location(), " tide_is_low:", gsm.get_flags().get("tide_is_low"))
print("    -> event A's change_location satisfied event B's `location` condition")
print("       inside the SAME pass. Reversing the list must break it.")
em, gsm, gs = build([tr, ab], flags={"knows_about_bluffs": True}, til=9)
r = em.check_and_trigger_events(gsm, "go to bluffs", [], "go_to")
print("    reversed order -> loc:", gsm.get_current_location(),
      " tide_is_low:", gsm.get_flags().get("tide_is_low"), "  <- B never saw A's move")

print("\n### 5b) find_elians_journal with its override removed; add_item key fixed")
fixed = copy.deepcopy(RAW)
for e in fixed:
    for a in e.actions:
        if a.get("type") == "add_item" and "value" in a and "item_id" not in a:
            a["item_id"] = a.pop("value")
fj = strip_override([e for e in fixed if e.id == "find_elians_journal"][0])
rj = copy.deepcopy([e for e in fixed if e.id == "read_journal_clue"][0])
rj.actions = [a for a in rj.actions if a.get("type") != "override_narrative"]
em, gsm, gs = build([fj, rj], loc="elian_study")
r = em.check_and_trigger_events(gsm, "search desk and then read journal", [], "i")
print("    order [find, read] -> flags:", sorted(gs.flags), " inv:", gs.player.inventory)
em, gsm, gs = build([rj, fj], loc="elian_study")
r = em.check_and_trigger_events(gsm, "search desk and then read journal", [], "i")
print("    order [read, find] -> flags:", sorted(gs.flags), " inv:", gs.player.inventory)
print("    -> the ONLY difference is dict insertion order (event_manager.py:8).")

print("\n### 5c) the real shipped file, nothing patched")
fj2 = copy.deepcopy([e for e in RAW if e.id == "find_elians_journal"][0])
rj2 = copy.deepcopy([e for e in RAW if e.id == "read_journal_clue"][0])
em, gsm, gs = build([fj2, rj2], loc="elian_study")
r = em.check_and_trigger_events(gsm, "search desk and then read journal", [], "i")
print("    flags:", sorted(gs.flags), " inv:", gs.player.inventory)
print("    -> read_journal_clue fails at `inventory_has` (yaml:60-61) because")
print("       find_elians_journal's add_item wrote `value:` (yaml:41-42) while")
print("       event_manager.py:111 reads `item_id`, so inventory holds None.")

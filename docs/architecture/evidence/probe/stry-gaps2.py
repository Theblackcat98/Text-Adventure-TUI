"""STRY probe: enumerate exactly what validate_story does NOT check."""
import shutil
import tempfile
from pathlib import Path

import yaml

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
tmp = Path(tempfile.mkdtemp(prefix="stry-gaps2-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP, EP = tmp / "story_parts", tmp / "events"
shutil.copytree(REPO / "text_adventure_tui_lib/story_parts", SP)
shutil.copytree(REPO / "text_adventure_tui_lib/events", EP)

from text_adventure_tui_lib.story_manager import StoryManager

BASE_ID = "the_clockwork_heist"
arc_p = SP / f"{BASE_ID}_story_arc.yaml"
ev_p = EP / f"{BASE_ID}_story_events.yaml"
arc0 = yaml.safe_load(arc_p.read_text())
ev0 = yaml.safe_load(ev_p.read_text())


def run(label, mutate):
    arc_p.write_text(yaml.dump(arc0, sort_keys=False))
    ev_p.write_text(yaml.dump(ev0, sort_keys=False))
    shutil.copy(REPO / "text_adventure_tui_lib/story_parts/01_intro.txt", SP / "01_intro.txt")
    arc = yaml.safe_load(arc_p.read_text())
    ev = yaml.safe_load(ev_p.read_text())
    mutate(arc, ev)
    if arc is not None:
        arc_p.write_text(yaml.dump(arc, sort_keys=False))
    if ev is not None:
        ev_p.write_text(yaml.dump(ev, sort_keys=False))
    m = StoryManager(SP, EP)
    r = m.validate_story(BASE_ID)
    status = "CAUGHT " if not r.is_valid else "MISSED "
    print(f"{status} {label}")
    if not r.is_valid:
        print(f"          errors: {r.errors}")
    if r.warnings:
        print(f"          warnings: {r.warnings}")


run("baseline (unmodified)", lambda a, e: None)
run("unknown trigger condition type 'weather'",
    lambda a, e: e[1]["trigger"].__setitem__("conditions", [{"type": "weather", "value": "rain"}]))
run("trigger mode 'MAYBE'",
    lambda a, e: e[1]["trigger"].__setitem__("mode", "MAYBE"))
run("unknown action type 'teleport_player'",
    lambda a, e: e[1]["actions"].append({"type": "teleport_player", "value": "x"}))
run("add_item uses `value:` (shipped form) -> add_item(None)",
    lambda a, e: e[1]["actions"].append({"type": "add_item", "value": "torch"}))
run("add_item uses `item_id:`",
    lambda a, e: e[1]["actions"].append({"type": "add_item", "item_id": "torch"}))
run("change_location to nonexistent location 'atlantis'",
    lambda a, e: e[1]["actions"].append({"type": "change_location", "value": "atlantis"}))
run("arc starting_location: 'nowhere_at_all'",
    lambda a, e: a.__setitem__("starting_location", "nowhere_at_all"))
run("turn_count_in_location operator '~=' (unsupported)",
    lambda a, e: e[1]["trigger"].__setitem__("conditions",
        [{"type": "turn_count_in_location", "operator": "~=", "value": 2}]))
run("stat_check on undefined stat 'luck'",
    lambda a, e: e[1]["trigger"].__setitem__("conditions",
        [{"type": "stat_check", "stat": "luck", "operator": ">=", "value": 5}]))
run("flag_set on flag never set by any action ('ghost_flag')",
    lambda a, e: e[1]["trigger"].__setitem__("conditions",
        [{"type": "flag_set", "value": "ghost_flag"}]))
run("inventory_has 'unicorn_horn' not in initial_inventory",
    lambda a, e: e[1]["trigger"].__setitem__("conditions",
        [{"type": "inventory_has", "value": "unicorn_horn"}]))
run("add_choice action 'trigger:no_such_event'",
    lambda a, e: e[1]["actions"].append(
        {"type": "add_choice", "label": "Go", "action": "trigger:no_such_event"}))
run("present_choices action 'no_such_event' (bare id)",
    lambda a, e: e[1]["actions"].append({"type": "present_choices",
        "choices": [{"label": "Go", "action": "no_such_event"}]}))
run("checkpoint flag_messages flag 'success' never set",
    lambda a, e: a.__setitem__("checkpoints", [
        {"turn": 3, "force_end_game": True, "prompt_injection": "x",
         "flag_messages": [{"flag": "success", "message_if_set": "YAY",
                            "message_if_not_set": "NAH"}]}]))
run("checkpoint at turn 999 (total_turns_estimate 15)",
    lambda a, e: a.__setitem__("checkpoints", [{"turn": 999, "force_end_game": True}]))
run("arc initial_story_part: 'does_not_exist.txt'",
    lambda a, e: a.__setitem__("initial_story_part", "does_not_exist.txt"))
run("arc initial_story_part OMITTED (fallback 01_intro.txt)",
    lambda a, e: a.pop("initial_story_part", None))
def rm_intro(a, e):
    a.pop("initial_story_part", None)
    (SP / "01_intro.txt").unlink()
run("initial_story_part OMITTED + 01_intro.txt deleted", rm_intro)
run("arc missing 'title'", lambda a, e: a.pop("title", None))
run("arc missing 'starting_location'", lambda a, e: a.pop("starting_location", None))
def dict_events(a, e):
    ev_p.write_text("id: x\n")
run("events file is a dict not a list", dict_events)
run("duplicate event ids (story_start twice)", lambda a, e: e.append(dict(e[0])))
run("events list contains a bare string", lambda a, e: e.append("not a dict"))
run("player_action_keyword with keywords: []",
    lambda a, e: e[1]["trigger"].__setitem__("conditions",
        [{"type": "player_action_keyword", "keywords": []}]))

print()
print("tmpdir:", tmp)

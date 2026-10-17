"""STRY probe: fix the dict-events case, and show RUNTIME effect of the missed gaps."""
import shutil, tempfile
from pathlib import Path
import yaml
from rich.console import Console

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
tmp = Path(tempfile.mkdtemp(prefix="stry-gaps3-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP, EP = tmp / "story_parts", tmp / "events"
shutil.copytree(REPO / "text_adventure_tui_lib/story_parts", SP)
shutil.copytree(REPO / "text_adventure_tui_lib/events", EP)
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager

BASE_ID = "the_clockwork_heist"
arc_p, ev_p = SP/f"{BASE_ID}_story_arc.yaml", EP/f"{BASE_ID}_story_events.yaml"
arc0, ev0 = yaml.safe_load(arc_p.read_text()), yaml.safe_load(ev_p.read_text())

print("=== 1. events file is a DICT not a list (fixed probe) ===")
ev_p.write_text("id: x\n")
r = StoryManager(SP, EP).validate_story(BASE_ID)
print("  is_valid:", r.is_valid, "errors:", r.errors, "warnings:", r.warnings)
ev_p.write_text(yaml.dump(ev0, sort_keys=False))

print()
print("=== 2. SHIPPED add_item actions: runtime effect (event_manager.py:111 reads item_id) ===")
for sid, evfile in [("the_clockwork_heist", "steal_temporal_gear"),
                    ("whispers_of_the_salted_crypt", "find_elians_journal")]:
    story, player = load_story_and_player(sid, SP)
    ev = next(e for e in story.events if e.id == evfile)
    add = [a for a in ev.actions if a.get("type") == "add_item"]
    gsm = GameStateManager(GameState(current_story=story, player=player,
                                     current_location=story.starting_location))
    em = EventManager(story.events, Console(quiet=True))
    print(f"  {sid}/{evfile}: yaml action = {add}")
    em.execute_event_actions(evfile, gsm, [])
    print(f"      inventory AFTER = {gsm.get_inventory()}")

print()
print("=== 3. present_choices -> bare event id: game.py:193 only routes on 'trigger:' prefix ===")
story, _ = load_story_and_player("whispers_of_the_salted_crypt", SP)
for e in story.events:
    for a in e.actions:
        if a.get("type") == "present_choices":
            for c in a.get("choices", []):
                print(f"  event {e.id}: choice '{c.get('label')}' -> action '{c.get('action')}'"
                      f"  startswith('trigger:')={str(c.get('action')).startswith('trigger:')}")

print()
print("=== 4. cross-check: do those ids exist as events? ===")
ids = {e.id for e in story.events}
print("  event ids:", sorted(ids))
for cand in ["end_story_success_heroic", "end_story_success_cautious"]:
    print(f"  {cand} in ids? {cand in ids}")
# what happens when player types the bare label instead of a number
print()
print("=== 5. event ids referenced nowhere: are all reachable from story_start? ===")
import collections
refs = set()
for e in story.events:
    for a in e.actions:
        act = a.get("action")
        if isinstance(act, str) and act.startswith("trigger:"):
            refs.add(act.split(":", 1)[1])
print("  trigger:-prefixed refs:", sorted(refs))
print("  dangling trigger: refs:", sorted(r for r in refs if r not in ids))
print("  events never referenced by any trigger: action and not referenced:",
      sorted(i for i in ids if i != "story_start" and i not in refs))

print()
print("=== 6. locations: every change_location value vs starting_location ===")
locs = set()
for e in story.events:
    for a in e.actions:
        if a.get("type") == "change_location":
            locs.add(a.get("value"))
print("  arc starting_location:", story.starting_location)
print("  locations set by change_location:", sorted(x for x in locs if x))
print("  'start' set by any change_location?", "start" in locs)

print()
print("=== 7. stat_check stats vs arc initial_player_stats ===")
stats = set()
for e in story.events:
    for c in e.trigger.get("conditions", []):
        if c.get("type") == "stat_check":
            stats.add(c.get("stat"))
        if c.get("type") == "update_stat":
            pass
print("  stats checked:", sorted(stats), "| arc stats:", sorted(player.stats))
print()
print("tmpdir:", tmp)

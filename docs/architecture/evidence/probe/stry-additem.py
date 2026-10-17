"""STRY probe 3b: isolate the add_item value/item_id mismatch."""
import yaml
from rich.console import Console
from text_adventure_tui_lib.data_structures import GameState, Player, Story, Event
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager

def run(label, actions, initial):
    ev = Event(id="e", name="e", trigger={}, actions=actions)
    st = Story(id="s", title="s", events=[ev])
    gs = GameState(current_story=st, player=Player(stats={}, inventory=list(initial)),
                   current_location="start")
    gsm = GameStateManager(gs)
    em = EventManager([ev], Console(quiet=True))
    em.execute_event_actions("e", gsm, [])
    print(f"  {label:34s} initial={list(initial)!r:22s} -> {gsm.get_inventory()!r}")

print("add_item semantics (event_manager.py:110-111 reads action['item_id']):")
run("{type: add_item, value: X}", [{"type": "add_item", "value": "X"}], [])
run("{type: add_item, item_id: X}", [{"type": "add_item", "item_id": "X"}], [])
run("{type: add_item, value: X}", [{"type": "add_item", "value": "X"}], ["pre"])

print("\nupdate_stat semantics (event_manager.py:116-120 reads stat/change_by):")
ev = Event(id="e", name="e", trigger={},
           actions=[{"type": "update_stat", "value": -10}])
st = Story(id="s", title="s", events=[ev])
gs = GameState(current_story=st, player=Player(stats={"health": 100}, inventory=[]))
gsm = GameStateManager(gs); em = EventManager([ev], Console(quiet=True))
try:
    em.execute_event_actions("e", gsm, [])
except Exception as e:
    print("  RAISED", type(e).__name__, e)
print("  {type: update_stat, value: -10} ->", gsm.get_stats())

print("\nWhat the SHIPPED events YAML actually writes for add_item:")
import glob, pathlib
for f in sorted(glob.glob("text_adventure_tui_lib/events/*.yaml")):
    txt = pathlib.Path(f).read_text()
    for i, line in enumerate(txt.splitlines(), 1):
        if "add_item" in line or "remove_item" in line:
            print(f"  {pathlib.Path(f).name}:{i}: {line.strip()}")

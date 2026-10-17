"""Probe: add_item reads item_id, shipped YAML writes value. What lands in inventory?"""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

console = Console()
story = Story(id="t", title="t")


def run(actions, label):
    ev = Event(id="probe", name="p", trigger={"mode": "MANUAL"}, actions=actions, options={})
    em = EventManager([ev], console)
    gs = GameState(current_story=story, player=Player(), flags={}, turn_count=0,
                   current_location="start", turns_in_location=0)
    gsm = GameStateManager(gs)
    res = em.execute_event_actions("probe", gsm, [])
    print(f"{label}\n  inventory -> {gs.player.inventory!r}")


# Exactly as written in whispers...yaml:41-42 (value:) and :95-96
run([{"type": "add_item", "value": "elians_journal"},
     {"type": "add_item", "value": "runic_key"}], "A) shipped YAML shape (value:)")
# As written in chapter1_study.yaml:17-18 (item_id:)
run([{"type": "add_item", "item_id": "elians_journal"}], "B) old-format YAML shape (item_id:)")
# remove_item shape
run([{"type": "add_item", "item_id": "runic_key"},
     {"type": "remove_item", "value": "runic_key"}], "C) add item_id then remove value")

# Which inventory_has conditions in the Whispers story can never fire?
import yaml
p = Path("text_adventure_tui_lib/events/whispers_of_the_salted_crypt_story_events.yaml")
data = yaml.safe_load(p.read_text())
need = []
for e in data:
    for c in e["trigger"].get("conditions", []) or []:
        if c.get("type") in ("inventory_has", "inventory_not_has"):
            need.append((e["id"], c.get("type"), c.get("value")))
print("\ninventory conditions in whispers story:")
for n in need:
    print("  ", n)

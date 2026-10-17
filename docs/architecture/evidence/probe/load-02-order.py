"""LOAD-2: EventManager dict order for both shipped stories + id-collision."""
from pathlib import Path
from rich.console import Console
import yaml

from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.event_manager import EventManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"
console = Console(quiet=True)

for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    story, _ = load_story_and_player(sid, STORIES)
    em = EventManager(story.events, console)
    print(f"== {sid} ==")
    print("  Story.events list order (index: id):")
    print("   ", ", ".join(f"{i}:{e.id}" for i, e in enumerate(story.events)))
    print("  EventManager.events dict key order:")
    print("   ", list(em.events.keys()))
    print(f"  len(list)={len(story.events)}  len(dict)={len(em.events)}")
    gen = yaml.safe_load((REPO / "text_adventure_tui_lib/events/general_events.yaml").read_text())
    gen_ids = [e["id"] for e in gen]
    print(f"  first {len(gen_ids)} keys == general_events.yaml order: {list(em.events.keys())[:len(gen_ids)] == gen_ids}")
    sef = REPO / f"text_adventure_tui_lib/events/{sid}_story_events.yaml"
    se_ids = [e["id"] for e in yaml.safe_load(sef.read_text())]
    print(f"  rest keys == {sef.name} order: {list(em.events.keys())[len(gen_ids):] == se_ids}")
    print(f"  story_start present: {'story_start' in em.events}")
    print()

print("== id collision: story event reuses a general_events.yaml id ==")
gen = yaml.safe_load((REPO / "text_adventure_tui_lib/events/general_events.yaml").read_text())
dup = dict(gen[0])
dup["name"] = "STORY COPY WINS"
dup["actions"] = [{"type": "set_flag", "value": "collision"}]
from text_adventure_tui_lib.data_structures import Event
def mk(d):
    return Event(id=d["id"], name=d.get("name",""), trigger=d.get("trigger",{}),
                 actions=d.get("actions",[]), options=d.get("options",{}))
evs = [mk(dup)] + [mk(d) for d in gen]
em = EventManager(evs, console)
print("  input list ids :", [e.id for e in evs])
print("  dict ids       :", list(em.events.keys()))
print("  len list/dict  :", len(evs), len(em.events))
print("  winner name    :", em.events["low_health_warning"].name)
print("  -> dict comprehension keeps LAST; the general_events entry is silently discarded")

"""Probe DATA-3: what a malformed YAML event does at load time, and whether
any validation runs before yaml_loader._create_events_from_data."""
import tempfile
from pathlib import Path

from text_adventure_tui_lib.yaml_loader import (
    _create_events_from_data,
    load_story_and_player,
)
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console

print("1. direct call with a dict that has no 'id'")
try:
    _create_events_from_data([{"name": "no id"}])
except Exception as e:
    print(f"   -> {type(e).__name__}: {e}")

print("\n2. event whose 'trigger' is a string, 'actions' is a dict, options missing")
ev = _create_events_from_data([
    {"id": "bad", "trigger": "just-a-string", "actions": {"a": 1}}
])
print("   Event.trigger =", repr(ev[0].trigger), "(no coercion, no error)")
print("   Event.actions =", repr(ev[0].actions), "(dict, not list)")
print("   Event.name    =", repr(ev[0].name), "(defaulted)")
print("   Event.options =", repr(ev[0].options), "(defaulted)")

print("\n3. does EventManager crash on such an event?")
em = EventManager(ev, Console(quiet=True))
print("   events index:", list(em.events.keys()))
gsm_dummy = None
try:
    em.check_and_trigger_events(gsm_dummy, "", [])
except Exception as e:
    print(f"   -> check_and_trigger_events raises {type(e).__name__}: {e}")

print("\n4. full load_story_and_player with a story arc + a broken event file")
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    (tmp / "broken_story_arc.yaml").write_text(
        'title: "Broken"\nstarting_location: start\n'
        'initial_player_stats: {health: 100}\n'
        'initial_inventory: ["a rusty key"]\n'
    )
    evdir = tmp / "events"
    evdir.mkdir()
    (evdir / "general_events.yaml").write_text(
        '- id: ok_event\n  trigger: {mode: AND, conditions: []}\n'
        '  actions: []\n'
        '- name: missing_id\n  actions: []\n'
    )
    try:
        story, player = load_story_and_player("broken", tmp)
        print("   loaded OK:", story.id)
    except Exception as e:
        print(f"   -> {type(e).__name__}: {e}")
    print("   NOTE: no partial story is returned; load is all-or-nothing.")

print("\n5. StoryManager.validate_story on the same broken story")
from text_adventure_tui_lib.story_manager import StoryManager
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    (tmp / "broken_story_arc.yaml").write_text(
        'title: "Broken"\nstarting_location: start\n'
    )
    evdir = tmp / "events"
    evdir.mkdir()
    (evdir / "broken_story_events.yaml").write_text(
        '- id: story_start\n  actions: []\n'
        '- name: missing_id\n  actions: []\n'
    )
    sm = StoryManager(tmp, evdir)
    res = sm.validate_story("broken")
    print("   is_valid:", res.is_valid)
    for e in res.errors:
        print("   error:", e)
    for w in res.warnings:
        print("   warning:", w)

print("\n6. validate_story is never called by the game entry point")
import subprocess
out = subprocess.run(
    ["grep", "-rn", "validate_story",
     "/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib",
     "/home/nick/Documents/Projects/Text-Adventure-TUI/story_tool.py"],
    capture_output=True, text=True).stdout
print(out)

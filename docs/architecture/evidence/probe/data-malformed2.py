"""Probe DATA-3b: correct directory layout for load_story_and_player.
yaml_loader.py:48 uses stories_path.parent / "events", so stories_path must be
<root>/story_parts for the events dir to be found."""
import tempfile
from pathlib import Path

from text_adventure_tui_lib.yaml_loader import load_story_and_player

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sp = root / "story_parts"
    sp.mkdir()
    (sp / "broken_story_arc.yaml").write_text(
        'title: "Broken"\nstarting_location: start\n'
        'initial_player_stats: {health: 100}\n'
        'initial_inventory: ["a rusty key"]\n'
    )
    evdir = root / "events"
    evdir.mkdir()
    (evdir / "general_events.yaml").write_text(
        '- id: ok_event\n  trigger: {mode: AND, conditions: []}\n  actions: []\n'
    )
    (evdir / "broken_story_events.yaml").write_text(
        '- id: story_start\n  name: Start\n  trigger: {mode: MANUAL}\n  actions: []\n'
        '- name: missing_id\n  actions: []\n'
    )
    try:
        story, player = load_story_and_player("broken", sp)
        print("loaded OK:", story.id)
    except Exception as e:
        print(f"-> {type(e).__name__}: {e}   (raised at yaml_loader.py:22 via :73)")

print()
print("same content, but the bad event has a trigger whose 'conditions' is a")
print("mapping instead of a list (silently wrong, no exception at load):")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sp = root / "story_parts"
    sp.mkdir()
    (sp / "s_story_arc.yaml").write_text('title: "S"\nstarting_location: start\n')
    evdir = root / "events"
    evdir.mkdir()
    (evdir / "general_events.yaml").write_text('')
    (evdir / "s_story_events.yaml").write_text(
        '- id: story_start\n  name: Start\n  trigger: {mode: MANUAL}\n  actions: []\n'
        '- id: weird\n  name: W\n  trigger:\n    mode: AND\n    conditions:\n'
        '      k: v\n  actions: "a plain string"\n'
    )
    story, player = load_story_and_player("s", sp)
    ev = [e for e in story.events if e.id == "weird"][0]
    print("   loaded OK, ids:", [e.id for e in story.events])
    print("   Event.trigger =", ev.trigger, type(ev.trigger).__name__)
    print("   Event.actions =", repr(ev.actions), type(ev.actions).__name__)
    print("   -> no error until EventManager._evaluate_trigger iterates "
          "conditions (event_manager.py:180)")
    from text_adventure_tui_lib.event_manager import EventManager
    from text_adventure_tui_lib.data_structures import GameState, Player, Story
    from rich.console import Console
    gsm = GameStateManagerStub = None
    gs = GameState(current_story=story, player=Player())
    from text_adventure_tui_lib.game_state_manager import GameStateManager
    gsm = GameStateManager(gs)
    em = EventManager(story.events, Console(quiet=True))
    try:
        em.check_and_trigger_events(gsm, "", [])
        print("   check_and_trigger_events: no exception")
    except Exception as e:
        print(f"   check_and_trigger_events -> {type(e).__name__}: {e}")

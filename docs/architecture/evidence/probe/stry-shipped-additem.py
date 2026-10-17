"""STRY probe 3c: does the add_item bug break the SHIPPED stories?"""
from rich.console import Console
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from pathlib import Path

SP = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib/story_parts")
console = Console(quiet=True)

for sid, ev_ids in (("whispers_of_the_salted_crypt",
                     ["search_elians_study", "find_elians_journal", "use_runic_key"]),
                    ("the_clockwork_heist", ["disable_security", "steal_temporal_gear"])):
    story, player = load_story_and_player(sid, SP)
    gs = GameState(current_story=story, player=player,
                   current_location=story.starting_location)
    gsm = GameStateManager(gs)
    em = EventManager(story.events, console)
    print(f"--- {sid}")
    print("   initial inventory:", gsm.get_inventory())
    print("   event ids:", [e.id for e in story.events])
    for eid in ev_ids:
        if eid in em.events:
            em.execute_event_actions(eid, gsm, [])
            print(f"   after forcing '{eid}': inventory={gsm.get_inventory()} flags={gsm.get_flags()}")
    # can any inventory_has condition ever fire?
    print("   inventory_has conditions that could still be met:")
    for e in story.events:
        for c in (e.trigger or {}).get("conditions", []) or []:
            if isinstance(c, dict) and c.get("type", "").startswith("inventory"):
                v = c.get("value")
                print(f"     {e.id}: {c.get('type')} {v!r} -> currently "
                      f"{'MET' if v in gsm.get_inventory() else 'NEVER MET'}")

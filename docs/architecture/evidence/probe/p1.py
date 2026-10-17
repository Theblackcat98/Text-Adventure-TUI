from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.event_manager import EventManager

sp = Path("text_adventure_tui_lib/story_parts")
story, player = load_story_and_player("whispers_of_the_salted_crypt", sp)
print("events loaded:", len(story.events))
print("event ids order:", [e.id for e in story.events])
gs = GameState(current_story=story, player=player, current_location=story.starting_location)
gsm = GameStateManager(gs)
em = EventManager(story.events, Console(quiet=True))
r = em.check_and_trigger_events(gsm, "search desk", [])
print("flags:", gs.flags)
print("inventory:", player.inventory)
print("injected_pre:", r["injected_narratives_pre"][:1])
print("injected_post count:", len(r["injected_narratives_post"]))
print("added_choices:", r["added_choices"])
print("modified_prompt_instructions key present:", "modified_prompt_instructions" in r)

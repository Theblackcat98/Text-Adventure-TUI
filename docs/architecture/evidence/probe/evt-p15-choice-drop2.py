"""Probe: with inventory seeded, do rescue_elian's choices ever reach the menu?"""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)
story, player = load_story_and_player(
    "whispers_of_the_salted_crypt", Path("text_adventure_tui_lib/story_parts"))
gs = GameState(current_story=story, player=player, flags={"tide_is_low": True},
               turn_count=6, current_location="crypt_antechamber", turns_in_location=3)
gs.player.inventory.append("runic_key")   # work around the add_item bug
gsm = GameStateManager(gs)
em = EventManager(story.events, console)

pre = em.check_and_trigger_events(gsm, "", [], "")
print("PASS 1 (game.py:285 pre-choice)  added_choices:", pre["added_choices"])
post = em.check_and_trigger_events(gsm, "use key", [], "use_item")
print("PASS 2 (game.py:313 post-choice) added_choices:", post["added_choices"])
print("  rescue_elian once-triggered now?", "rescue_elian" in em.triggered_event_ids)
print("  location after remove_item:", gsm.get_current_location(), "inv:", gs.player.inventory)

gsm.increment_turn(); gsm.increment_turns_in_location()
pre2 = em.check_and_trigger_events(gsm, "", [], "")
print("PASS 3 (next turn pre-choice)   added_choices:", pre2["added_choices"], "<- what the menu shows")
print()
print("VERDICT: game.py:294 binds added_choices from the PASS-1 result only.")
print("          rescue_elian fires in PASS 2 (post-choice), whose added_choices")
print("          is never read. Marked once-triggered at :78, so PASS 3 skips it")
print("          at :51-55. The two ending choices are unreachable by menu.")

"""Probe: are rescue_elian's present_choices ever rendered? Trace game.py:294 vs :313."""
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
               turn_count=6, current_location="saltstone_bluffs", turns_in_location=3)
gsm = GameStateManager(gs)
em = EventManager(story.events, console)

# Turn A: pre-choice pass (game.py:285, input "")
pre = em.check_and_trigger_events(gsm, "", [], "")
print("PASS 1 (game.py:285 pre-choice, input='')  -> added_choices:",
      pre["added_choices"])

# Turn A: post-choice pass (game.py:313, input = the player's chosen LLM text)
post = em.check_and_trigger_events(gsm, "use the runic key on the stone door", [], "use_item")
print("PASS 2 (game.py:313 post-choice)          -> added_choices:",
      post["added_choices"])
print("  rescue_elian marked once-triggered?      ",
      "rescue_elian" in em.triggered_event_ids)

# Turn B: pre-choice pass again. rescue_elian is now skipped by :51-55.
gsm.increment_turn(); gsm.increment_turns_in_location()
pre2 = em.check_and_trigger_events(gsm, "", [], "")
print("PASS 3 (next turn, game.py:285)            -> added_choices:",
      pre2["added_choices"])
print("\n=> game.py reads added_choices ONLY at :294 (pre-choice pass).")
print("   The :313 result's added_choices is bound to event_results but the only")
print("   keys read afterwards are override_narrative (:318) and")
print("   injected_narratives_post (:330).")
print("   Final reachable choice set:", pre2["added_choices"], "<- empty")

# Can the player type the action string instead?
print("\nget_player_choice (game.py:187-199) accepts ONLY a digit or a '/'-command;")
print("anything else hits 'Invalid choice.' and re-prompts.")
print("So player_action 'end_story_success_heroic' can never match typed input.")

"""STRY probe 7: present_choices / add_choice routing as the game actually does it."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

SP = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib/story_parts")
story, player = load_story_and_player("whispers_of_the_salted_crypt", SP)
gs = GameState(current_story=story, player=player, current_location=story.starting_location)
gsm = GameStateManager(gs)
em = EventManager(story.events, Console(quiet=True))

ev = em.events["rescue_elian"]
print("rescue_elian actions:", [a.get("type") for a in ev.actions])
out = em.execute_event_actions("rescue_elian", gsm, [])
print("added_choices (engine view):", out["added_choices"])
print("engine read the action's 'text:' key? ->",
      out["override_narrative"] is not None, "(present_choices drops 'text:', see event_manager.py:139-147)")

# game.py:193 -- only 'trigger:<id>' routes to execute_event_actions
for ch in out["added_choices"]:
    a = ch["action"]
    routed = a.split(":", 1)[1] if a.startswith("trigger:") else None
    print(f"  choice {ch['label'][:34]!r:38s} action={a!r:28s} "
          f"-> game.py:193 routes to event: {routed}")
    print(f"      as free text it is compared by event_manager.py:200-201 "
          f"player_action == {a!r} -> "
          f"{em._evaluate_trigger(em.events[a].trigger, gsm, a, '') if a in em.events else 'no such event'}")

print("\n-- and the missing-event case: action 'trigger:no_such_event' --")
em.execute_event_actions("rescue_elian", gsm, [])
print("  game.py:301 execute_event_actions('no_such_event', ...) ->",
      em.execute_event_actions("no_such_event", gsm, []))
print("  game.py:305 narrative = event_results.get('override_narrative', narrative)"
      " -> narrative becomes None; next turn get_llm_options() is called with narrative=None")

print("\n-- is there any turn cap besides checkpoints? --")
import subprocess
print(subprocess.run(["grep", "-n", "turn_count\\|total_turns", "text_adventure_tui_lib/game.py"],
                     capture_output=True, text=True).stdout)

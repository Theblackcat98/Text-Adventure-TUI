"""Probe DATA-10: (a) prove the saved Story copy is discarded, by mutating the
in-memory Story before saving; (b) run the real general_events.yaml triggers
through a simulated turn loop."""
import json
from pathlib import Path

from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from rich.console import Console

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
sp = LIB / "story_parts"

print("=== (a) in-memory Story mutated AFTER load, then saved ===")
story, player = load_story_and_player("the_clockwork_heist", sp)
story.title = "MUTATED IN MEMORY"
story.checkpoints = [{"turn": 999, "force_end_game": True}]
story.total_turns_estimate = 9999
gs = GameState(current_story=story, player=player, turn_count=3,
               current_location="hall")
gsm = GameStateManager(gs)
saved = json.loads(json.dumps(
    {"game_state": gsm.game_state, "event_manager_state": {}},
    default=lambda o: o.__dict__))
sc = saved["game_state"]["current_story"]
print("  saved title          :", sc["title"])
print("  saved checkpoints    :", sc["checkpoints"])
print("  saved turns_estimate :", sc["total_turns_estimate"])
print("  game.py:451 reads ONLY ['game_state']['current_story']['id'] ->",
      sc["id"])

story2, player2 = load_story_and_player("the_clockwork_heist", sp)
print("  on resume the story is rebuilt from disk:")
print("   title          :", story2.title)
print("   checkpoints    :", story2.checkpoints)
print("   turns_estimate :", story2.total_turns_estimate)
print("  -> the mutated values above are in the save file and are never read")

print("\n=== (b) real general_events.yaml triggers over a simulated turn loop ===")
story3, player3 = load_story_and_player("the_clockwork_heist", sp)
gs3 = GameState(current_story=story3, player=player3,
                current_location=story3.starting_location)
gsm3 = GameStateManager(gs3)
em = EventManager(story3.events, Console(quiet=True))
em.execute_event_actions("story_start", gsm3, [])   # game.py:272
print("  after story_start: turn_count=%d til=%d loc=%s"
      % (gsm3.get_turn_count(), gs3.turns_in_location, gsm3.get_current_location()))
fired = {}
for turn in range(1, 10):
    # game.py:285 pre-choice sweep
    em.check_and_trigger_events(gsm3, "", [])
    til = gs3.turns_in_location
    if til == 1:
        fired.setdefault("first_time_in_location (==1)", []).append(turn)
    if til >= 5:
        fired.setdefault("long_time_in_location (>=5)", []).append(turn)
    # game.py:346-348
    gsm3.increment_turn()
    gsm3.increment_turns_in_location()
for k, v in fired.items():
    print(f"  {k:32} fires on turns {v}")
print("  (first_time_in_location has options.once:true at "
      "general_events.yaml:35-36, so it fires once; the counter still equals 1 "
      "on every later turn)")
print("  triggered_event_ids after the loop:", sorted(em.triggered_event_ids))

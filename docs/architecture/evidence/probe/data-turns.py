"""Probe DATA-2: turns_in_location interaction between set_current_location
(game_state_manager.py:44-47) and increment_turn/increment_turns_in_location
(game.py:347-348)."""
from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.game_state_manager import GameStateManager


def new_manager(starting_location="start"):
    story = Story(id="t", title="T", starting_location=starting_location)
    gs = GameState(current_story=story, player=Player(),
                   current_location=story.starting_location)
    return GameStateManager(gs)


print("case A: fresh game, never change location, N increments")
gsm = new_manager()
for n in range(1, 9):
    gsm.increment_turn()
    gsm.increment_turns_in_location()
    print(f"  after {n} turn(s): turn_count={gsm.get_turn_count()} "
          f"turns_in_location={gsm.game_state.turns_in_location} "
          f"loc={gsm.get_current_location()}")

print("\ncase B: change location mid-stream")
gsm = new_manager()
gsm.increment_turn(); gsm.increment_turns_in_location()
gsm.increment_turn(); gsm.increment_turns_in_location()
print(f"  2 turns at 'start'  -> til={gsm.game_state.turns_in_location}")
gsm.set_current_location("vault")
print(f"  immediately after set_current_location('vault') -> "
      f"til={gsm.game_state.turns_in_location} "
      f"(reset to 0? {gsm.game_state.turns_in_location == 0})")
gsm.increment_turn(); gsm.increment_turns_in_location()
print(f"  1 turn in 'vault'    -> til={gsm.game_state.turns_in_location}")

print("\ncase C: set_current_location to the SAME location (no reset)")
gsm = new_manager()
gsm.increment_turns_in_location()
gsm.increment_turns_in_location()
gsm.increment_turns_in_location()
print(f"  before: til={gsm.game_state.turns_in_location}")
gsm.set_current_location(gsm.get_current_location())
print(f"  after set_current_location('start'): "
      f"til={gsm.game_state.turns_in_location} "
      f"(NOT reset -> {gsm.game_state.turns_in_location == 3})")

print("\ncase D: which turn_count_in_location values are actually observable")
gsm = new_manager()
observed = []
for n in range(1, 8):
    observed.append((f"turn {n} pre-choice ", gsm.game_state.turns_in_location))
    observed.append((f"turn {n} post-choice", gsm.game_state.turns_in_location))
    gsm.increment_turn(); gsm.increment_turns_in_location()
for k, v in observed:
    print(f"  {k:24} til={v}")

print("\ncase E: first-turn behaviour with the real story_start flow")
gsm = new_manager()
print("  after GameState construction:  til =", gsm.game_state.turns_in_location)
gsm.set_current_location("start")
print("  after story_start change_location('start'): til =",
      gsm.game_state.turns_in_location, "(loc unchanged -> no reset)")
gsm.increment_turn(); gsm.increment_turns_in_location()
print("  after turn 1:                 til =", gsm.game_state.turns_in_location)

print("\ncase F: effect on general_events.yaml:40-42 (== 1) and :53-55 (>= 5)")
gsm = new_manager()
fired_first, fired_long = [], []
for turn in range(1, 9):
    til = gsm.game_state.turns_in_location
    if til == 1:
        fired_first.append(turn)
    if til >= 5:
        fired_long.append(turn)
    gsm.increment_turn(); gsm.increment_turns_in_location()
print("  turns where til==1  (first_time_in_location, ONCE per id):", fired_first)
print("  turns where til>=5  (long_time_in_location):", fired_long)

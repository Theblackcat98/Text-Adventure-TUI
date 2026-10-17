"""Probe: drive the real Whispers story through EventManager turn by turn."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)
story, player = load_story_and_player(
    "whispers_of_the_salted_crypt", Path("text_adventure_tui_lib/story_parts")
)
gs = GameState(current_story=story, player=player, flags={}, turn_count=0,
               current_location=story.starting_location, turns_in_location=0)
gsm = GameStateManager(gs)
em = EventManager(story.events, console)

print("== evaluation order of EventManager.events dict (insertion order) ==")
for i, (eid, ev) in enumerate(em.events.items(), 1):
    print(f"  {i:2d}. {eid}")
print("\nduplicate ids collapsed? n_events_in_yaml =",
      len(story.events), " len(dict) =", len(em.events))

print("\n== game.py:272 story_start forced ==")
r = em.execute_event_actions("story_start", gsm, [])
print("  location:", gsm.get_current_location(), " flags:", gsm.get_flags(),
      " inventory:", gsm.get_inventory())

print("\n== simulate 10 turns with descriptive choices ==")
choices = ["search desk", "read journal", "search bookshelf",
           "go to bluffs", "wait here", "enter archway",
           "use key", "use key", "use key", "use key"]
for t, ch in enumerate(choices):
    instr = []
    # pre-choice pass, as game.py:285 does (empty input)
    pre = em.check_and_trigger_events(gsm, "", instr, "")
    # choice pass, as game.py:313 does
    post = em.check_and_trigger_events(gsm, ch, instr, "unknown_intent")
    fired = [x for x in post.get("override_narrative") or []]
    print(f"  turn {t}: chose {ch!r} -> override={str(post.get('override_narrative'))[:48]!r} "
          f"choices={len(post.get('added_choices', []))} "
          f"loc={gsm.get_current_location()} inv={gs.player.inventory} "
          f"flags={sorted(gsm.get_flags())}")
    gsm.increment_turn()
    gsm.increment_turns_in_location()

print("\n== which story events were EVER marked triggered (once) ==")
print(" ", sorted(em.triggered_event_ids))

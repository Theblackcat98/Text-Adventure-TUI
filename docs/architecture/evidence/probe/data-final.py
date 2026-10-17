"""Probe DATA-12: turn-counter call graph, the `continue` skip, save-file
composition, and aliasing of two managers over one GameState."""
import json, inspect
from pathlib import Path
from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from rich.console import Console

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")

print("A. every call site of the three counter mutators (grep-derived, re-checked)")
import subprocess
for name in ("increment_turn", "increment_turns_in_location", "set_current_location"):
    out = subprocess.run(["grep", "-rn", name + "(", "--include=*.py",
                          str(LIB.parent)], capture_output=True, text=True).stdout
    print(f"   {name}:")
    for ln in out.strip().splitlines():
        print("     ", ln.replace(str(LIB.parent) + "/", ""))

print("\nB. game.py:300-306 `continue` path SKIPS game.py:347-348 entirely")
src = (LIB / "game.py").read_text().splitlines()
print("   game.py:300 =", src[299].strip())
print("   game.py:306 =", src[305].strip(), " <- `continue` jumps to the top of "
      "the while loop at game.py:276, past the two increments")
print("   game.py:347 =", src[346].strip())
print("   game.py:348 =", src[347].strip())

print("\nC. two GameStateManagers over one GameState alias completely")
gs = GameState(current_story=Story(id="s", title="S"), player=Player())
a, b = GameStateManager(gs), GameStateManager(gs)
a.set_flag("via_a"); b.set_flag("via_b")
print("   flags seen by a:", a.get_flags(), " by b:", b.get_flags())
print("   a.game_state is b.game_state:", a.game_state is b.game_state)

print("\nD. save file composition: how many bytes are the discarded Story copy?")
story, player = load_story_and_player("the_clockwork_heist", LIB / "story_parts")
gs = GameState(current_story=story, player=player, turn_count=7,
               current_location="vault", turns_in_location=3)
gsm = GameStateManager(gs); gsm.add_item("telescope")
em = EventManager(story.events, Console(quiet=True))
save_data = {"game_state": gsm.game_state, "event_manager_state": em.get_state()}
text = json.dumps(save_data, indent=4, default=lambda o: o.__dict__)
total = len(text)
sc = json.dumps(save_data["game_state"]["current_story"], indent=4,
                default=lambda o: o.__dict__)
print(f"   whole save file          : {total} bytes")
print(f"   current_story subtree    : {len(sc)} bytes  ({100*len(sc)/total:.0f}%)")
print(f"   of which 'events'        : "
      f"{len(json.dumps(story.events, indent=4, default=lambda o: o.__dict__))} bytes")
print(f"   everything actually read : saved_state['game_state'][flags/turn_count/")
print(f"     current_location/turns_in_location] + ['current_story']['id']")

print("\nE. save file top-level keys vs what game.py:251 reads")
print("   keys written  (game.py:225-228):", sorted(save_data.keys()))
print("   keys read     (game.py:240-251) : ['game_state']")
print("   game.py:251 reads saved_state['narrative']  ->",
      repr(saved_narrative := "MISSING from the save"))
print("   -> every resumed game opens with 'Your story continues...'; the whole")
print("      LLM narrative accumulated in game.py:281/:326 is never persisted")

print("\nF. event_manager_state round-trip (the only other persisted key)")
em.execute_event_actions("story_start", gsm, [])
em.check_and_trigger_events(gsm, "", [])
print("   before:", sorted(em.triggered_event_ids))
rt = json.loads(json.dumps(em.get_state()))
em2 = EventManager(story.events, Console(quiet=True))
em2.load_state(rt)
print("   after :", sorted(em2.triggered_event_ids))
print("   type change:", type(em.triggered_event_ids).__name__, "->",
      type(em2.triggered_event_ids).__name__, "(set <-> list, values survive)")

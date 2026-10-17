"""Probe: what the player actually sees on the ending turn (game.py:318 vs :334)."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)
story, player = load_story_and_player(
    "whispers_of_the_salted_crypt", Path("text_adventure_tui_lib/story_parts"))
gs = GameState(current_story=story, player=player, flags={}, turn_count=7,
               current_location="crypt_antechamber", turns_in_location=1)
gsm = GameStateManager(gs)
em = EventManager(story.events, console)

r = em.check_and_trigger_events(gsm, "end_story_success_heroic", [], "unknown_intent")
print("override_narrative :", repr(r["override_narrative"]))
print("game_ended flags   :", {k: v for k, v in gs.flags.items() if k.startswith('game_ended')})
print()
print("game.py:318-319  narrative = event_results['override_narrative']  ->",
      repr(r["override_narrative"]))
print("game.py:330-331  injected_narratives_post =", r["injected_narratives_post"])
print("game.py:334      game_ended -> True  (banner printed at :337)")
print("game.py:344      break  ->  loop exits BEFORE line 280/281 display_story(narrative)")
print()
print("=> the ending prose (and the default 'The story ends here.') is assigned")
print("   to `narrative` and then never printed. Player sees only the banner.")
print()
print("clockwork bare `end_game` with no success key (events/...clockwork...:282):")
import copy
e2 = copy.deepcopy([e for e in story.events if e.id == "end_story_success_heroic"][0])
e2.actions = [a for a in e2.actions if a["type"] != "override_narrative"] + [
    {"type": "end_game"}]
gs2 = GameState(current_story=story, player=player, flags={}, turn_count=0,
                current_location="start", turns_in_location=0)
gsm2 = GameStateManager(gs2)
em2 = EventManager([e2], console)
r2 = em2.check_and_trigger_events(gsm2, "x", [], "")
print("   bare end_game -> override:", repr(r2["override_narrative"]),
      " flags:", {k: v for k, v in gs2.flags.items() if k.startswith('game_ended')})
print("   default success=True at event_manager.py:150 -> reported as SUCCESS")

"""ENTRY probe 01: the three LLM helpers called BEFORE main_menu() runs."""
import traceback
from pathlib import Path

import text_adventure_tui_lib.game as game
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Player, Story

print("game module file            :", game.__file__)
print("ollama_client at import time:", repr(game.ollama_client))

story = Story(id="probe", title="Probe", events=[])
gsm = GameStateManager(GameState(current_story=story, player=Player()))

print("\n--- helpers called with ollama_client still None ---")
for label, fn in [
    ("get_llm_story_continuation (derefs at game.py:86)",
     lambda: game.get_llm_story_continuation("n", "c", [])),
    ("get_player_intent (derefs at game.py:110)",
     lambda: game.get_player_intent("look around", gsm)),
    ("get_llm_options (derefs at game.py:140)",
     lambda: game.get_llm_options("n", gsm)),
]:
    print(f"\n### {label}")
    try:
        print("   RETURNED:", repr(fn()))
    except Exception as exc:
        tb = traceback.extract_tb(exc.__trace__)
        last = tb[-1]
        print(f"   RAISED {type(exc).__name__}: {exc}")
        print(f"   innermost frame: {Path(last.filename).name}:{last.lineno} -> {last.line}")
        print(f"   caught by the module's own except? "
              f"{'NO' if isinstance(exc, AttributeError) else 'YES'}")

print("\n--- same three, but ollama_client is a non-client object ---")
game.ollama_client = object()
print("   get_player_intent           ->", repr(game.get_player_intent("look", gsm)))
print("   get_llm_options             ->", repr(game.get_llm_options("n", gsm)))
print("   get_llm_story_continuation  ->", repr(game.get_llm_story_continuation("n", "c", [])))

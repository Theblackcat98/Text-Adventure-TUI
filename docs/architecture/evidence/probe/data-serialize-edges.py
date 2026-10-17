"""Probe DATA-6: clean isolation of json default=lambda o: o.__dict__ edges."""
import json, datetime, sys
from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.game_state_manager import GameStateManager

def dump(state):
    return json.dumps({"game_state": state}, default=lambda o: o.__dict__)

print("A. set inside player.stats")
gs = GameState(current_story=Story(id="s", title="S"),
               player=Player(stats={"st": {1, 2}}))
try:
    dump(gs); print("   no error (unexpected)")
except Exception as e:
    print(f"   -> {type(e).__name__}: {e}")

print("\nB. datetime inside player.stats")
gs2 = GameState(current_story=Story(id="s", title="S"),
                player=Player(stats={"dt": datetime.datetime(2025, 1, 1)}))
try:
    dump(gs2); print("   no error")
except Exception as e:
    print(f"   -> {type(e).__name__}: {e}")

print("\nC. tuple inside player.stats (silent type change)")
gs3 = GameState(current_story=Story(id="s", title="S"),
                player=Player(stats={"tup": (1, 2)}))
txt = dump(gs3)
reloaded = json.loads(txt)
print("   JSON text contains:", txt[:120].replace("\n", " "))
print("   reloaded type:", type(reloaded["game_state"]["player"]["stats"]["tup"]).__name__)

print("\nD. non-bool inside flags (Dict[str, bool] annotation)")
gs4 = GameState(current_story=Story(id="s", title="S"), player=Player())
gs4.flags["note"] = "a string"
print("   flags:", gs4.flags)
print("   game.py:243 restores flags verbatim from JSON -> string survives:",
      json.loads(dump(gs4))["game_state"]["flags"])

print("\nE. cycle -> RecursionError")
gs5 = GameState(current_story=Story(id="s", title="S"), player=Player())
gs5.player = gs5          # player -> self
old = sys.getrecursionlimit()
sys.setrecursionlimit(300)
try:
    dump(gs5)
    print("   no error")
except Exception as e:
    print(f"   -> {type(e).__name__}: {str(e)[:70]}")
finally:
    sys.setrecursionlimit(old)

print("\nF. new attributes can be attached to a dataclass instance "
      "(no __slots__, no validation)")
gs6 = GameState(current_story=Story(id="s", title="S"), player=Player())
gs6.not_a_declared_field = 123
print("   declared fields:", [f for f in GameState.__dataclass_fields__])
print("   instance __dict__ now:", sorted(gs6.__dict__))
print("   json dump includes it:", "not_a_declared_field" in dump(gs6))
print("   on reload game.py:240-247 constructs GameState(...) with 6 kwargs; "
      "the extra key is dropped")

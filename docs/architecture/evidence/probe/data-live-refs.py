"""Probe DATA-5: get_flags/get_inventory/get_stats return LIVE objects, and
what that means for json.dump(..., default=lambda o: o.__dict__) at game.py:229."""
import json
import datetime
from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.game_state_manager import GameStateManager

gs = GameState(current_story=Story(id="s", title="S"), player=Player())
gsm = GameStateManager(gs)

print("1. identity checks")
print("   get_flags() is game_state.flags   :", gsm.get_flags() is gs.flags)
print("   get_inventory() is player.inventory:", gsm.get_inventory() is gs.player.inventory)
print("   get_stats() is player.stats       :", gsm.get_stats() is gs.player.stats)
print("   get_player() is game_state.player :", gsm.get_player() is gs.player)
print("   get_story() is current_story      :", gsm.get_story() is gs.current_story)

print("\n2. bypass set_flag/add_item/update_stat entirely")
gsm.get_flags()["sneaky"] = True
gsm.get_inventory().append("ghost_item")
gsm.get_stats()["ghost"] = 99
print("   flags    :", gs.flags)
print("   inventory:", gs.player.inventory)
print("   stats    :", gs.player.stats)
print("   -> no event_manager action was needed; add_item's dedupe guard "
      "(game_state_manager.py:28) is bypassed too:")
gsm.get_inventory().append("ghost_item")
print("   inventory after 2nd append:", gs.player.inventory,
      "(duplicate allowed)")
gsm.get_inventory().append(None)   # add_item(None) would also have worked
print("   inventory after append(None):", gs.player.inventory)

print("\n3. default=lambda o: o.__dict__ returns the LIVE dict, not a copy")
print("   gs.__dict__ is gs.__dict__           :", gs.__dict__ is gs.__dict__)
print("   gs.__dict__['flags'] is gs.flags     :", gs.__dict__["flags"] is gs.flags)
gsm.get_flags()["added_after_dump_setup"] = True
print("   a flag set after save_data was built but before json.dumps still "
      "appears in the file (proves by-reference capture):")
save_data = {"game_state": gsm.game_state}
gsm.set_flag("set_after_dict_capture")
out = json.dumps(save_data, default=lambda o: o.__dict__)
print("   'set_after_dict_capture' in dumped JSON:",
      "set_after_dict_capture" in out)

print("\n4. tuple / set / datetime behaviour under default=lambda o: o.__dict__")
gsm.update_stat("tup", (1, 2))
gsm.update_stat("st", {1, 2})
try:
    gsm.update_stat("dt", datetime.datetime(2025, 1, 1))
    json.dumps({"game_state": gsm.game_state}, default=lambda o: o.__dict__)
except Exception as e:
    print("   datetime in stats ->", type(e).__name__, e)
try:
    json.dumps({"game_state": gsm.game_state}, default=lambda o: o.__dict__)
except Exception as e:
    print("   set in stats ->", type(e).__name__, e)
print("   tuple in stats ->", json.dumps(gs.player.stats["tup"]),
      "(silently becomes a list on reload: type change, not an error)")
print("   set in stats ->", gs.player.stats["st"], "(was json.dumps fine?)")

print("\n5. cycles blow the stack (no cycle detection in the default hook)")
gs.turns_in_location = 1
gs.stats_ref = gs            # new attribute -> GameState has no fixed schema
try:
    json.dumps({"g": gs}, default=lambda o: o.__dict__)
except Exception as e:
    print("   self-referential GameState ->", type(e).__name__)

print("\n6. dataclass instances nested arbitrarily deep are flattened by __dict__")
from text_adventure_tui_lib.data_structures import Event
ev = Event(id="e", name="E", trigger={"a": 1}, actions=[{"b": 2}])
print("   Event ->", json.dumps(ev, default=lambda o: o.__dict__))
print("   -> no __qualname__/type tag is written, so the class identity is lost")

print("\n7. deletion asymmetry: clear_flag deletes the key, get_flags().clear() "
      "leaves the same key absent — equivalent; but a dataclass field can never "
      "be removed this way")
gsm.set_flag("x")
gsm.clear_flag("x")
print("   flags after clear_flag('x'):", gs.flags)
print("   GameState dataclass fields still:", sorted(gs.__dict__))

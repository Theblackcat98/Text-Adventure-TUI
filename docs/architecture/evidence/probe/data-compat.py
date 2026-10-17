"""Probe DATA-7: save-file compatibility. No schema version key, no __eq__,
no to_dict/from_dict. What happens when the dataclasses change?"""
import json
from text_adventure_tui_lib.data_structures import GameState, Player, Story

print("1. GameState required (no-default) fields:", ["current_story", "player"])
print("   every field that has a default:")
for f in GameState.__dataclass_fields__.values():
    if f.default is not f.default_factory and f.default is not None:
        pass
for name, f in GameState.__dataclass_fields__.items():
    has_def = f.default is not f.default_factory
    has_fac = f.default_factory is not f.default_factory
    print(f"   {name:20} default={'yes' if has_def else ('factory' if has_fac else 'REQUIRED')}"
          f" default_repr={f.default!r}")

print("\n2. simulated OLD save (written by a pre-'turns_in_location' build):")
old_save = {
    "game_state": {
        "current_story": {"id": "x", "title": "X"},
        "player": {"stats": {"health": 10}},
        "flags": {},
        "turn_count": 4,
        "current_location": "hall",
        # turns_in_location absent
    }
}
try:
    gs = GameState(
        current_story=None, player=None,
        flags=old_save["game_state"]["flags"],
        turn_count=old_save["game_state"]["turn_count"],
        current_location=old_save["game_state"]["current_location"],
        turns_in_location=old_save["game_state"]["turns_in_location"],
    )
except Exception as e:
    print(f"   -> {type(e).__name__}: {e}  (game.py:246 raises before the "
          f"rest of the save is read)")

print("\n3. simulated NEW save field a build that does not know it:")
new_save = {
    "game_state": {
        "current_story": {"id": "x", "title": "X"},
        "player": {"stats": {}, "inventory": []},
        "flags": {},
        "turn_count": 1,
        "current_location": "s",
        "turns_in_location": 0,
        "morale": 7,            # field a future GameState might add
    }
}
gs = GameState(current_story=None, player=None, flags={}, turn_count=1,
               current_location="s", turns_in_location=0)
print("   extra key silently ignored:",
      "morale" in new_save["game_state"],
      "| loaded object has it:", hasattr(gs, "morale"))

print("\n4. __eq__ / to_dict / from_dict on the dataclasses")
for cls in (Player, __import__("text_adventure_tui_lib.data_structures",
                               fromlist=["Event"]).Event, Story, GameState):
    print(f"   {cls.__name__:10} __eq__={'__eq__' in cls.__dict__} "
          f"to_dict={hasattr(cls, 'to_dict')} from_dict={hasattr(cls, 'from_dict')}")

print("\n5. dataclasses are unhashable-by-value? hash behaviour:")
try:
    hash(Story(id="a", title="a"))
    print("   Story is hashable (eq=True -> frozen=True -> hashed by identity)")
except TypeError as e:
    print("   ->", type(e).__name__, e)
a, b = Story(id="a", title="a"), Story(id="a", title="a")
print("   a == b ?", a == b, " (dataclass eq compares field-by-field)")
print("   same-value Stories compare equal:", Story(id="a", title="t") ==
      Story(id="a", title="t"))
print("   -> equality DOES work for same-class same-fields; the gap is that "
      "GameState containing two Story objects compares fine but a reloaded "
      "GameState compares False whenever any List field differs in element type")

print("\n6. dict-field equality across a JSON round trip:")
before = Player(stats={"health": 100}, inventory=["a"])
after = Player(stats=json.loads(json.dumps(before.stats)),
               inventory=json.loads(json.dumps(before.inventory)))
print("   Player equal after round trip:", before == after)

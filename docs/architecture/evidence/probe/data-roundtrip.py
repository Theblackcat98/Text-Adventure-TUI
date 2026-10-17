"""Probe DATA-1: exact JSON round-trip of GameState at game.py:218-230 and :237-251."""
import json
from pathlib import Path

from text_adventure_tui_lib.data_structures import GameState, Player
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
stories_path = LIB / "story_parts"

story, player = load_story_and_player("the_clockwork_heist", stories_path)
print("loaded story id:", story.id, "| events:", len(story.events),
      "| checkpoints:", len(story.checkpoints))

gs = GameState(
    current_story=story,
    player=player,
    flags={"a": True, "b": True},
    turn_count=7,
    current_location="vault",
    turns_in_location=3,
)
gsm = GameStateManager(gs)
gsm.update_stat("stealth", 42)
gsm.add_item("telescope")

save_data = {
    "game_state": gsm.game_state,
    "event_manager_state": {"triggered_event_ids": ["example_event"]},
}
text = json.dumps(save_data, indent=2, default=lambda o: o.__dict__)
saved_state = json.loads(text)

print("\n=== top-level keys of save file ===")
print(sorted(saved_state.keys()))
print("\n=== game_state keys written ===")
print(sorted(saved_state["game_state"].keys()))
print("\n=== current_story keys written ===")
print(sorted(saved_state["game_state"]["current_story"].keys()))
print("serialized bytes of save file:", len(text))
print("serialized events inside save:",
      len(saved_state["game_state"]["current_story"]["events"]))

story2, player2 = load_story_and_player("the_clockwork_heist", stories_path)
gs2 = GameState(
    current_story=story2,
    player=player2,
    flags=saved_state["game_state"]["flags"],
    turn_count=saved_state["game_state"]["turn_count"],
    current_location=saved_state["game_state"]["current_location"],
    turns_in_location=saved_state["game_state"]["turns_in_location"],
)

print("\n=== per-field survival ===")
rows = [
    ("flags", gs.flags, gs2.flags),
    ("turn_count", gs.turn_count, gs2.turn_count),
    ("current_location", gs.current_location, gs2.current_location),
    ("turns_in_location", gs.turns_in_location, gs2.turns_in_location),
    ("player.stats", gs.player.stats, gs2.player.stats),
    ("player.inventory", gs.player.inventory, gs2.player.inventory),
    ("current_story.id", gs.current_story.id, gs2.current_story.id),
    ("current_story.checkpoints", gs.current_story.checkpoints,
     gs2.current_story.checkpoints),
]
for name, a, b in rows:
    print(f"{name:28} before={a!r:45} after={b!r:45} "
          f"{'SAME' if a == b else 'LOST'}")

print("\nis the reloaded story object the same object as the saved one?",
      gs2.current_story is gs.current_story)
print("saved story dict identity preserved through JSON?",
      saved_state["game_state"]["current_story"] is not gs.current_story)


def walk_types(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            walk_types(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk_types(v, acc)
    else:
        acc[type(obj).__name__] = acc.get(type(obj).__name__, 0) + 1
    return acc


print("\n=== JSON scalar types present in the save ===")
print(walk_types(saved_state, {}))

print("\n=== schema/version key search in the save ===")
print("'version' at game_state top level:",
      "version" in saved_state["game_state"])
print("save file keys:", list(saved_state.keys()))
print("game_state.current_story.version (story's own version):",
      saved_state["game_state"]["current_story"]["version"])

print("\n=== resume path uses only saved_state['game_state']['current_story']['id'] ===")
print("story id read back on resume (game.py:451):",
      saved_state["game_state"]["current_story"]["id"])
print("\n=== what happens if 'narrative' is absent ===")
print("game.py:251 fallback:", repr(saved_state.get("narrative", "Your story continues...")))

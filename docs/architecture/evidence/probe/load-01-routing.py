"""LOAD-1: which story id routes to which loader branch, and what the
old-format branch produces for story.id / title / starting_location."""
from pathlib import Path

from text_adventure_tui_lib.yaml_loader import load_story_and_player, _load_story_old_format
from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"
EVENTS = REPO / "text_adventure_tui_lib/events"

print("== discover_stories() (story_manager.py:47 glob '*_story_arc.yaml') ==")
sm = StoryManager(STORIES, EVENTS)
ids = [s.id for s in sm.discover_stories()]
print("  ids:", ids)

print("\n== branch selection per id (yaml_loader.py:41-45) ==")
for sid in ids:
    arc = STORIES / f"{sid}_story_arc.yaml"
    branch = "NEW (arc file exists)" if arc.exists() else "OLD (_load_story_old_format)"
    print(f"  {sid:36s} arc={arc.exists()!s:5s} -> {branch}")
    story, player = load_story_and_player(sid, STORIES)
    print(f"     story.id={story.id!r}")
    print(f"     story.title={story.title!r}")
    print(f"     starting_location={story.starting_location!r}")
    print(f"     initial_story_part={story.initial_story_part!r}")
    print(f"     total_turns={story.total_turns_estimate!r} author={story.author!r}")
    print(f"     player.stats={player.stats} player.inventory={player.inventory}")
    print(f"     SAVE NAME -> {story.id}_20261012_101112.json")
    print(f"     n_events={len(story.events)}")

print("\n== old-format candidate: does any id reach it? ==")
for cand in ("Whispers_of_the_Salted_Crypt", "whispers_of_the_salted_crypt"):
    arc = STORIES / f"{cand}_story_arc.yaml"
    d = STORIES / cand
    print(f"  {cand}: arc exists={arc.exists()}  story_parts/{cand} exists={d.exists()} isdir={d.is_dir()}")
    print(f"     discover_stories ever emits it? {cand in ids}")

print("\n== force the old branch on story id 'Whispers_of_the_Salted_Crypt' ==")
story, player = _load_story_old_format("Whispers_of_the_Salted_Crypt", STORIES)
print(f"  story.id={story.id!r}")
print(f"  story.title={story.title!r}   (falls back to setup_info['name'])")
print(f"  starting_location={story.starting_location!r}  initial_story_part={story.initial_story_part!r}")
print(f"  player.stats={player.stats}  player.inventory={player.inventory}")
print(f"  SAVE NAME -> {story.id}_20261012_101112.json")
print(f"  event ids in order: {[e.id for e in story.events]}")

print("\n== the 4 files under story_parts/Whispers_of_the_Salted_Crypt/ ==")
for f in sorted((STORIES / "Whispers_of_the_Salted_Crypt").glob("*.yaml")):
    print("   ", f.name, "reached by old-format glob '*.yaml' -> True")

print("\n== which files carry initial_player_stats / initial_inventory? ==")
for f in sorted((STORIES / "Whispers_of_the_Salted_Crypt").glob("*.yaml")):
    t = f.read_text()
    print(f"    {f.name}: initial_player_stats={'initial_player_stats' in t} "
          f"initial_inventory={'initial_inventory' in t}")

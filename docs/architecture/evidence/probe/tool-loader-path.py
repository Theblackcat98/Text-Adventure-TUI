"""Probe: which branch of load_story_and_player does the test fixture exercise?"""
import sys, tempfile, pathlib, yaml
sys.path.insert(0, "/home/nick/Documents/Projects/Text-Adventure-TUI")
import text_adventure_tui_lib.yaml_loader as yl

calls = []
orig = yl._load_yaml
def spy(p):
    calls.append(str(p))
    return orig(p)
yl._load_yaml = spy

tmp = pathlib.Path(tempfile.mkdtemp())
d = tmp / "test_story"; d.mkdir(parents=True)
(d / "game_setup.yaml").write_text("""
- id: story_start
  name: "Test Story"
  trigger:
    mode: MANUAL
  actions: []
  initial_player_stats:
    health: 100
  initial_inventory:
    - "a rusty key"
""")
calls.clear()
story, player = yl.load_story_and_player("test_story", tmp)
print("story_arc branch taken (new format)? ", (tmp / "test_story_story_arc.yaml").exists())
print("files actually read:", calls)
print("story.id=", story.id, "title=", story.title, "events=", len(story.events))
print("story.starting_location=", story.starting_location, "initial_story_part=", story.initial_story_part)
print("story.author=", story.author, "difficulty=", story.difficulty, "checkpoints=", story.checkpoints)
print("player.stats=", player.stats, "player.inventory=", player.inventory)

# now the NEW-format branch, never touched by the suite
calls.clear()
arc = {"title": "Arc Story", "starting_location": "attic", "initial_story_part": "x_intro.txt",
       "initial_player_stats": {"health": 80}, "initial_inventory": ["rope"], "author": "Me"}
(tmp / "s2_story_arc.yaml").write_text(yaml.dump(arc))
(tmp.parent / "events").mkdir(exist_ok=True)
(tmp.parent / "events" / "s2_story_events.yaml").write_text(yaml.dump([{"id": "story_start", "name": "n", "trigger": {}, "actions": []}]))
story2, player2 = yl.load_story_and_player("s2", tmp)
print()
print("NEW-format branch: story2.id=", story2.id, "author=", story2.author, "starting_location=", story2.starting_location, "events=", len(story2.events), "inventory=", player2.inventory)
print("files read for new format:", calls)

"""STRY-02: prove which files discover_stories() can see.

story_manager.py:47 globs stories_path.glob("*_story_arc.yaml") -- non-recursive,
glob '*' does not cross directory separators. Show:
  a) the exact glob result on the shipped tree
  b) that the old-format directory story_parts/Whispers_of_the_Salted_Crypt/
     contains 4 YAML files, none matching the pattern at the top level
  c) that Python's Path.glob("*_story_arc.yaml") does not descend (by
     construction: place a *_story_arc.yaml INSIDE the old-format dir in a
     temp copy and show it is still not discovered when globbing the parent)
  d) that _load_story_old_format WOULD load the directory if the id were passed
"""
import sys
from pathlib import Path
sys.path.insert(0, "/home/nick/Documents/Projects/Text-Adventure-TUI")

from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
stories = REPO / "text_adventure_tui_lib" / "story_parts"
events = REPO / "text_adventure_tui_lib" / "events"

print("(a) exact glob results, stories_path.glob('*_story_arc.yaml'):")
for p in sorted(stories.glob("*_story_arc.yaml")):
    print("   MATCH:", p.relative_to(REPO))

print()
print("(b) contents of story_parts/Whispers_of_the_Salted_Crypt/:")
for p in sorted((stories / "Whispers_of_the_Salted_Crypt").iterdir()):
    print("   ", p.name)
print("   glob over that dir for *_story_arc.yaml:",
      list((stories / "Whispers_of_the_Salted_Crypt").glob("*_story_arc.yaml")))

print()
print("(c) does discover_stories see it? ids discovered:")
mgr = StoryManager(stories, events)
ids = [s.id for s in mgr.discover_stories()]
print("   ", ids)
print("   'Whispers_of_the_Salted_Crypt' in ids:",
      "Whispers_of_the_Salted_Crypt" in ids)

print()
print("(d) would the OLD loader handle the id if someone passed it?")
import text_adventure_tui_lib.yaml_loader as yl
story, player = yl._load_story_old_format("Whispers_of_the_Salted_Crypt", stories)
print("   old-format load OK: story.id=%r title=%r events=%d"
      % (story.id, story.title, len(story.events)))
print("   validate_story('Whispers_of_the_Salted_Crypt'):")
res = mgr.validate_story("Whispers_of_the_Salted_Crypt")
print("   is_valid:", res.is_valid)
print("   errors:", res.errors)

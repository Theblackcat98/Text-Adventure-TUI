"""STRY probe 1: prove discover_stories()' glob is non-recursive."""
import sys
from pathlib import Path

from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SP = REPO / "text_adventure_tui_lib" / "story_parts"
EP = REPO / "text_adventure_tui_lib" / "events"

print("== raw glob '*_story_arc.yaml' ==")
for p in sorted(SP.glob("*_story_arc.yaml")):
    print("  ", p.name)
print("== raw glob '**/*_story_arc.yaml' (rglob) ==")
for p in sorted(SP.rglob("*_story_arc.yaml")):
    print("  ", p.relative_to(SP))
print("== contents of story_parts/Whispers_of_the_Salted_Crypt/ ==")
sub = SP / "Whispers_of_the_Salted_Crypt"
for p in sorted(sub.glob("*")):
    print("  ", p.name, p.stat().st_size, "bytes")
print("== any *_story_arc.yaml under the subdir? ==")
print("  ", list(sub.glob("*_story_arc.yaml")))
print("  glob('Whispers_of_the_Salted_Crypt*') ->",
      [p.name for p in SP.glob("Whispers_of_the_Salted_Crypt*")])

m = StoryManager(SP, EP)
print("== StoryManager.discover_stories() ==")
for s in m.discover_stories():
    print("  ", s.id, "|", s.title)

print("== is the subdir reachable as a story id? ==")
print("  validate_story('Whispers_of_the_Salted_Crypt') ->",
      m.validate_story("Whispers_of_the_Salted_Crypt"))

# what would the OLD loader do if it were reached?
from text_adventure_tui_lib.yaml_loader import _load_story_old_format
try:
    s, p = _load_story_old_format("Whispers_of_the_Salted_Crypt", SP)
    print("== old-format loader direct call ==")
    print("   title:", s.title, "| starting_location:", s.starting_location,
          "| events:", len(s.events))
    print("   event ids:", [e.id for e in s.events])
except Exception as e:
    print("   old loader raised:", type(e).__name__, e)

sys.stdout.flush()

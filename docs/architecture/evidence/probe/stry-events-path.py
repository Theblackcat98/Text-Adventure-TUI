"""STRY probe 2: does validate_story honour self.events_path for the load check?"""
from pathlib import Path
import text_adventure_tui_lib.story_manager as sm
from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SP = REPO / "text_adventure_tui_lib" / "story_parts"
EP = REPO / "text_adventure_tui_lib" / "events"

real = StoryManager(SP, EP)
bogus = StoryManager(SP, Path("/definitely/not/here/events"))
empty = StoryManager(SP, Path("/tmp/opencode/cdd-text-adventure-tui/probe/empty_events"))

for sid in ("the_clockwork_heist", "whispers_of_the_salted_crypt"):
    a = real.validate_story(sid)
    b = bogus.validate_story(sid)
    c = empty.validate_story(sid)
    print(f"--- {sid}")
    print("  real   :", a)
    print("  bogus  :", b)
    print("  empty  :", c)
    print("  bogus == real ?", a == b, "| empty == real ?", a == c)

# instrument the loader to see which directory it actually touches
calls = []
orig = sm.load_story_and_player


def spy(story_name, stories_path):
    calls.append(stories_path)
    return orig(story_name, stories_path)


sm.load_story_and_player = spy
b2 = StoryManager(SP, Path("/definitely/not/here/events"))
r = b2.validate_story("the_clockwork_heist")
print("=== loader called with:", calls, "-> result", r)
print("=== yaml_loader.py:48 computes stories_path.parent/'events' ==",
      SP.parent / "events")
print("=== is that the same as the REAL events dir?", (SP.parent / "events") == EP)
print("=== is it the same as the bogus events_path passed in?",
      (SP.parent / "events") == Path("/definitely/not/here/events"))
sm.load_story_and_player = orig

# And: story_tool --events-path is only consulted for the existence check at :103
print("=== events file existence check uses self.events_path: bogus => warning?",
      "Story events file not found" in str(bogus.validate_story("the_clockwork_heist").warnings))

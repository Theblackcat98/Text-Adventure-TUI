import sys, io, contextlib
from pathlib import Path
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib import yaml_loader

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SP = REPO/"text_adventure_tui_lib/story_parts"
EP = REPO/"text_adventure_tui_lib/events"

print("=== A. real events_path ===")
m_real = StoryManager(SP, EP)
r = m_real.validate_story("the_clockwork_heist")
print("valid:", r.is_valid, "errors:", r.errors, "warnings:", r.warnings)

print()
print("=== B. BOGUS events_path (/nonexistent/events) ===")
m_bogus = StoryManager(SP, Path("/nonexistent/events"))
print("m_bogus.events_path =", m_bogus.events_path)
r2 = m_bogus.validate_story("the_clockwork_heist")
print("valid:", r2.is_valid, "errors:", r2.errors, "warnings:", r2.warnings)
print("IDENTICAL RESULT:", r == r2)

print()
print("=== C. bogus events_path for a story whose events file we delete from EP ===")
# prove that validate_story reads events from stories_path.parent/'events', not self.events_path
import yaml_loader as yl
orig = yl.load_story_and_player
seen = {}
def spy(story_name, stories_path):
    seen['called_with'] = (story_name, str(stories_path))
    return orig(story_name, stories_path)
import text_adventure_tui_lib.story_manager as sm
sm.load_story_and_player = spy
m_bogus.validate_story("whispers_of_the_salted_crypt")
print("load_story_and_player called with:", seen)
sm.load_story_and_player = orig

print()
print("=== D. events_path arg never used in loader ===")
import inspect
src = inspect.getsource(yl.load_story_and_player)
print("'events_path' assignment in load_story_and_player:", [l.strip() for l in src.splitlines() if 'events_path' in l])

print()
print("=== E. old format loader reachability ===")
import inspect
srcs = inspect.getsource(sm) + inspect.getsource(yl)
print("callers of _load_story_old_format:", [l.strip() for l in inspect.getsource(yl).splitlines() if '_load_story_old_format' in l])
# prove no UI caller passes a directory name
print("discover_stories ids:", [s.id for s in m_real.discover_stories()])

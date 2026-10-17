import inspect
from pathlib import Path
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib import yaml_loader as yl
import text_adventure_tui_lib.story_manager as sm

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SP = REPO/"text_adventure_tui_lib/story_parts"
EP = REPO/"text_adventure_tui_lib/events"

print("=== C. spy: what does validate_story pass to load_story_and_player? ===")
orig = sm.load_story_and_player
seen = []
def spy(story_name, stories_path):
    seen.append((story_name, str(stories_path)))
    return orig(story_name, stories_path)
sm.load_story_and_player = spy
m_bogus = StoryManager(SP, Path("/nonexistent/events"))
r = m_bogus.validate_story("the_clockwork_heist")
print("load_story_and_player called with:", seen)
print("valid:", r.is_valid, "errors:", r.errors, "warnings:", r.warnings)
sm.load_story_and_player = orig

print()
print("=== D. 'events_path' lines inside load_story_and_player ===")
src = inspect.getsource(yl.load_story_and_player)
for i,l in enumerate(src.splitlines(), start=32):
    if 'events_path' in l or 'stories_path' in l:
        print(f"  yaml_loader.py:{i}: {l.strip()}")

print()
print("=== E. events_path only used at lines 103/248 in story_manager ===")
src2 = inspect.getsource(sm.StoryManager)
for i,l in enumerate(src2.splitlines(), start=35):
    if 'events_path' in l:
        print(f"  story_manager.py:{i}: {l.strip()}")

print()
print("=== F. old-format loader reachability ===")
for i,l in enumerate(inspect.getsource(yl).splitlines(), start=1):
    if '_load_story_old_format' in l:
        print(f"  yaml_loader.py:{i}: {l.strip()}")
print("discover_stories ids:", [s.id for s in StoryManager(SP,EP).discover_stories()])
print("main_menu ids passed to game_loop: StoryInfo.id from discover_stories only (game.py:429,435)")
print()
print("=== G. old format load WOULD work if called directly ===")
try:
    st, pl = yl.load_story_and_player("Whispers_of_the_Salted_Crypt", SP)
    print("old-format load OK: id=", st.id, "title=", st.title, "events=", len(st.events), "start_loc=", st.starting_location, "part=", st.initial_story_part)
    print("  story_start present:", any(e.id=='story_start' for e in st.events))
    import os
    print("  intro part exists at SP/01_intro.txt:", (SP/"01_intro.txt").exists())
except Exception as e:
    print("old-format load FAILED:", type(e).__name__, e)

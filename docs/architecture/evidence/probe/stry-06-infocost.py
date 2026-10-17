"""STRY-06: cost of get_story_info / validate_story in file opens.

get_story_info (story_manager.py:258-264) calls discover_stories(), which
re-opens and re-parses EVERY arc YAML (story_manager.py:47-50) to answer a
question about ONE story. Count opens via an audit wrapper.
"""
import builtins, sys, io
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
sys.path.insert(0, str(REPO))

real_open = builtins.open
LOG = []
def audit(file, *a, **k):
    try:
        name = str(file)
    except Exception:
        name = "?"
    LOG.append(name)
    return real_open(file, *a, **k)
builtins.open = audit

from text_adventure_tui_lib.story_manager import StoryManager

sp = REPO / "text_adventure_tui_lib" / "story_parts"
ep = REPO / "text_adventure_tui_lib" / "events"
mgr = StoryManager(sp, ep)

def reset():
    LOG.clear()

reset(); stories = mgr.discover_stories()
n = len(stories)
print("stories discovered:", n)
print("opens for ONE discover_stories():", len(LOG),
      "->", sorted(set(LOG)))
print("  = N arc parses, N =", n)

reset(); mgr.get_story_info("whispers_of_the_salted_crypt")
print("opens for ONE get_story_info():", len(LOG))

reset(); res = mgr.validate_story("whispers_of_the_salted_crypt")
print("opens for ONE validate_story():", len(LOG), "->", sorted(set(LOG)))

reset()
import subprocess, os
print()
print("full CLI 'python story_tool.py info <id>' open count (subprocess strace-free estimate):")
print("  = get_story_info (N) + validate_story (5) =", n, "+ 5 =", n + 5, "file opens")

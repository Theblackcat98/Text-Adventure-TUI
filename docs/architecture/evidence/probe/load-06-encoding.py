"""LOAD-6: _load_yaml opens with no encoding= (yaml_loader.py:10).
Run twice: normal env, and LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0
so that locale.getpreferredencoding(False) is ANSI_X3.4-1968 (US-ASCII)."""
import locale, sys, traceback, textwrap
from pathlib import Path

enc = locale.getpreferredencoding(False)
sys.stdout.reconfigure(encoding="ascii", errors="backslashreplace")
print(f"locale.getpreferredencoding(False) = {enc}")
print(f"sys.flags.utf8_mode = {sys.flags.utf8_mode}")
print(f"sys.getfilesystemencoding() = {sys.getfilesystemencoding()}")

from text_adventure_tui_lib.yaml_loader import load_story_and_player

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"

for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    try:
        story, _ = load_story_and_player(sid, STORIES)
        print(f"  {sid}: OK, {len(story.events)} events")
    except Exception as e:
        print(f"  {sid}: {type(e).__name__}: {e}")
        print(textwrap.indent(traceback.format_exc().strip(), "    | "))

print("non-ascii lives in events/general_events.yaml lines 73-76 (U+2022 BULLET)")

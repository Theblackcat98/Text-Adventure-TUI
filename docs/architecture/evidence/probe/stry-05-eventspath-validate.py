"""STRY-05: --events-path divergence as seen through validate_story.

story_manager.validate_story checks <events_path>/<id>_story_events.yaml
(story_manager.py:103) but then calls load_story_and_player(story_id,
self.stories_path) (story_manager.py:144), and the loader ALWAYS derives
events from stories_path.parent/'events' (yaml_loader.py:48).
So validation can bless a file that the game will never read.

Layout:
  pkg/story_parts/   arc + intro for demo_story        (stories_path)
  pkg/events/        ONLY general_events.yaml          <- what the loader reads
  elsewhere/         demo_story_story_events.yaml      <- what validation reads
"""
import shutil, sys
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
PKG = REPO / "text_adventure_tui_lib"
TMP = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-eventspath")
if TMP.exists():
    shutil.rmtree(TMP)
shutil.copytree(PKG / "story_parts", TMP / "pkg" / "story_parts")
shutil.copytree(PKG / "events", TMP / "pkg" / "events")
# strip the story events file from where the LOADER will look
(TMP / "pkg" / "events" / "demo_story_story_events.yaml").unlink(missing_ok=True)
# but provide it where VALIDATION will look
(TMP / "elsewhere").mkdir()
(TMP / "elsewhere" / "demo_story_story_events.yaml").write_text(
    "- id: story_start\n"
    "  trigger:\n"
    "    mode: MANUAL\n"
    "    conditions: [{type: game_start}]\n"
    "  actions:\n"
    "    - type: override_narrative\n"
    "      text: HELLO FROM ELSEWHERE\n"
)
# arc + intro for the demo story
arc = TMP / "pkg" / "story_parts" / "demo_story_story_arc.yaml"
arc.write_text("title: Demo Story\nstarting_location: start\n"
               "initial_story_part: demo_intro.txt\n")
(TMP / "pkg" / "story_parts" / "demo_intro.txt").write_text("demo intro text\n")

sys.path.insert(0, str(REPO))
from rich.console import Console
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState

sp = TMP / "pkg" / "story_parts"
mgr = StoryManager(sp, TMP / "elsewhere")          # --events-path elsewhere

res = mgr.validate_story("demo_story")
print("validate_story('demo_story')  is_valid:", res.is_valid)
print("  errors:  ", res.errors)
print("  warnings:", res.warnings)

print()
print("now load it the way game.py:254 does:")
story, player = load_story_and_player("demo_story", sp)
print("  event ids loaded:", [e.id for e in story.events])
print("  'story_start' in loaded events:", any(e.id == "story_start" for e in story.events))

print()
print("what game.py:272 then does:")
em = EventManager(story.events, Console(quiet=True))
r = em.execute_event_actions("story_start", GameStateManager(
    GameState(current_story=story, player=player,
              current_location=story.starting_location)), [])
print("  result dict:", r)
print()
print("VERDICT: validation says valid=%s; 'HELLO FROM ELSEWHERE' narrative: %s"
      % (res.is_valid, r.get("override_narrative")))

"""LOAD-8: yaml_loader derives events/ from stories_path.parent (line 48) and
ignores StoryManager.events_path -- prove the decoupling."""
import tempfile
from pathlib import Path
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.story_manager import StoryManager

root = Path(tempfile.mkdtemp(prefix="loadprobe8-"))
# author supplies TWO independent dirs (story_tool --stories-path / --events-path)
s = root / "content"; e = root / "events_elsewhere"
s.mkdir(); e.mkdir()
(s / "demo_story_arc.yaml").write_text('title: "D"\nstarting_location: "start"\n')
(e / "demo_story_events.yaml").write_text("- id: story_start\n  name: S\n")
(s.parent / "events").mkdir()
(s.parent / "events" / "general_events.yaml").write_text("- id: gen_only\n  name: G\n")

story, player = load_story_and_player("demo", s)   # only stories_path passed
print("load_story_and_player read events from:", sorted(p.name for p in (s.parent / "events").glob("*.yaml")))
print("  events loaded:", [ev.id for ev in story.events])
print("  -> events_elsewhere/demo_story_events.yaml was IGNORED")

sm = StoryManager(s, e)
res = sm.validate_story("demo")
print("validate_story(events_path=e) errors:", res.errors)
print("validate_story(events_path=e) warnings:", res.warnings)
print("  -> it reports 'Story events file not found' for the dir it was HANDED,")
print("     but its internal load_story_and_player used stories_path.parent/'events' instead")

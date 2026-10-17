"""LOAD-3: exact exception + traceback for three malformed events YAML shapes,
and what story_manager.validate_story says about each."""
import io, contextlib, traceback, tempfile, textwrap
from pathlib import Path

from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.story_manager import StoryManager

ARC = 'title: "T"\nstarting_location: "start"\ninitial_story_part: "01_intro.txt"\n'

CASES = {
    "a_mapping_not_list": textwrap.dedent("""
        story_start:
          id: story_start
          name: hi
    """).strip() + "\n",
    "b_list_of_strings": '- "story_start"\n- "some_event"\n',
    "c_event_missing_id": (
        "- id: story_start\n"
        "  name: ok\n"
        "- name: no id here\n"
        "  actions: []\n"
    ),
}

root = Path(tempfile.mkdtemp(prefix="loadprobe-"))
stories = root / "story_parts"; events = root / "events"
stories.mkdir(); events.mkdir()
(events / "general_events.yaml").write_text("- id: low_health_warning\n  name: Low\n")

for name, body in CASES.items():
    (events / "broken_story_events.yaml").write_text(body)
    (stories / "broken_story_arc.yaml").write_text(ARC)
    print("=" * 70)
    print("CASE", name)
    print("--- yaml.load_safe_load type:", __import__("yaml").safe_load(body).__class__.__name__)
    print("--- load_story_and_player:")
    try:
        load_story_and_player("broken", stories)
        print("    NO EXCEPTION")
    except Exception:
        print(textwrap.indent(traceback.format_exc().strip(), "    | "))
    print("--- StoryManager.validate_story('broken'):")
    res = StoryManager(stories, events).validate_story("broken")
    print(f"    is_valid={res.is_valid}")
    for e in res.errors: print("      ERROR  :", e)
    for w in res.warnings: print("      WARNING:", w)
    print()

print("=" * 70)
print("CASE d: general_events.yaml is the broken one (never validated by validate_story)")
(events / "broken_story_events.yaml").write_text("- id: story_start\n  name: ok\n")
(events / "general_events.yaml").write_text("story_start:\n  id: story_start\n")
res = StoryManager(stories, events).validate_story("broken")
print(f"  validate_story is_valid={res.is_valid} errors={res.errors} warnings={res.warnings}")
try:
    load_story_and_player("broken", stories)
    print("  load: NO EXCEPTION")
except Exception:
    print(textwrap.indent(traceback.format_exc().strip(), "  | "))

print("=" * 70)
print("CASE e: story arc file is EMPTY (safe_load -> None)")
(events / "general_events.yaml").write_text("- id: low_health_warning\n  name: Low\n")
(stories / "broken_story_arc.yaml").write_text("")
try:
    load_story_and_player("broken", stories)
except Exception:
    print(textwrap.indent(traceback.format_exc().strip(), "  | "))

print("=" * 70)
print("CASE f: old-format id with no directory at all")
try:
    load_story_and_player("no_such_story", stories)
except Exception:
    print(textwrap.indent(traceback.format_exc().strip(), "  | "))

print("=" * 70)
print("CASE g: old-format directory with yaml but no story_start event")
(stories / "no_such_story").mkdir()
(stories / "no_such_story" / "a.yaml").write_text("- id: not_start\n  name: x\n")
try:
    load_story_and_player("no_such_story", stories)
except Exception:
    print(textwrap.indent(traceback.format_exc().strip(), "  | "))
print("  validate_story('no_such_story') ->", StoryManager(stories, events).validate_story("no_such_story"))

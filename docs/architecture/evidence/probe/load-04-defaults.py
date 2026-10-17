"""LOAD-4: story_arc_data.get(...) defaults vs @dataclass defaults, and
initial_story_part resolution for every shipped arc."""
import dataclasses
from pathlib import Path
import yaml

from text_adventure_tui_lib.data_structures import Story
from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"
EVENTS = REPO / "text_adventure_tui_lib/events"

# loader defaults, transcribed from yaml_loader.py:82-91
LOADER_DEFAULTS = {
    "starting_location": "start",
    "initial_story_part": "01_intro.txt",
    "total_turns_estimate": 20,
    "description": "",
    "checkpoints": [],
    "tags": [],
    "difficulty": "medium",
    "content_warnings": [],
    "author": "Unknown",
    "version": "1.0",
}
dc_fields = {f.name: f for f in dataclasses.fields(Story)}

print("== loader .get default  vs  @dataclass default ==")
print(f"{'field':22s} {'loader .get default':26s} {'dataclass default':26s} agree?")
mismatches = []
for k, v in LOADER_DEFAULTS.items():
    f = dc_fields.get(k)
    if f is None:
        print(f"{k:22s} {repr(v):26s} {'(NO FIELD ON Story)':26s} !!")
        mismatches.append(k)
        continue
    d = f.default
    agree = (d == v) or (d is dataclasses.MISSING and v is None)
    # mutable defaults: dataclass uses field(default_factory=...)
    kind = "MISSING" if d is dataclasses.MISSING else type(d).__name__
    print(f"{k:22s} {repr(v):26s} {repr(d) if d is not dataclasses.MISSING else 'default_factory':26s} {'OK' if agree or d is dataclasses.MISSING else 'DISAGREE'}")
    if not agree and d is not dataclasses.MISSING:
        mismatches.append(k)

print("\nmismatches:", mismatches or "none")

print("\n== fields Story carries but the loader never populates from YAML ==")
populated = set(LOADER_DEFAULTS) | {"id", "title", "events"}
print(sorted(set(dc_fields) - populated) or "none")

print("\n== initial_story_part: declared vs file present ==")
sm = StoryManager(STORIES, EVTS) if False else StoryManager(STORIES, EVENTS)
for arc in sorted(STORIES.glob("*_story_arc.yaml")):
    sid = arc.stem.replace("_story_arc", "")
    data = yaml.safe_load(arc.read_text())
    declared = data.get("initial_story_part", "01_intro.txt")
    target = STORIES / declared
    print(f"  {sid}")
    print(f"    declared initial_story_part : {declared!r}")
    print(f"    story_parts/{declared} exists: {target.exists()}")
    print(f"    validate_story warnings      : {sm.validate_story(sid).warnings}")
    print(f"    validate_story errors        : {sm.validate_story(sid).errors}")

print("\n== every .txt in story_parts/ and who points at it ==")
for txt in sorted(STORIES.glob("*.txt")):
    refs = []
    for arc in sorted(STORIES.glob("*_story_arc.yaml")):
        if txt.name in arc.read_text():
            refs.append(arc.stem.replace("_story_arc", ""))
    print(f"  {txt.name:24s} referenced by: {refs or 'NOTHING'}")

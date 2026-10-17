from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
SP = LIB / "story_parts"
console = Console(quiet=True)

print("### A. does the arc's initial_story_part exist, and is it overwritten?  (game.py:264-274)")
for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    story, player = load_story_and_player(sid, SP)
    p = SP / story.initial_story_part
    txt = p.read_text(encoding="utf-8") if p.exists() else None
    print(f"  {sid}: initial_story_part={story.initial_story_part!r} exists={p.exists()}")
    print(f"     file starts: {txt[:70]!r}")
    ss = [e for e in story.events if e.id == "story_start"][0]
    on = [a for a in ss.actions if a.get("type") == "override_narrative"]
    print(f"     story_start has override_narrative: {bool(on)} ({len(on[0]['text'])} chars)")
    print(f"     => game.py:273-274 REPLACES the .txt narrative immediately")

print()
print("### B. FileNotFoundError fallback text")
print("  game.py:268-269 -> narrative = 'The story begins...'")

print()
print("### C. story_parts/ inventory")
for f in sorted(SP.rglob("*")):
    if f.is_file() and "__pycache__" not in str(f):
        print(f"  {f.relative_to(LIB)}  ({f.stat().st_size} bytes)")

print()
print("### D. is `initial_story_part` ever used for anything but the first turn?")
import subprocess
print(subprocess.run(["grep","-n","initial_story_part",
                      str(LIB/"game.py"), str(LIB/"yaml_loader.py"), str(LIB/"story_manager.py"),
                      str(LIB/"data_structures.py")], capture_output=True, text=True).stdout)

print()
print("### E. what does `story_tool.py create` write (the author extension point)?")
import tempfile, os
from text_adventure_tui_lib.story_manager import StoryManager
with tempfile.TemporaryDirectory() as td:
    sdir, edir = Path(td)/"sp", Path(td)/"ev"
    sdir.mkdir(); edir.mkdir()
    sm = StoryManager(sdir, edir)
    sm.create_story_template("mystory", "My Story", author="me")
    for f in sorted(Path(td).rglob("*")):
        if f.is_file():
            print(f"  created {f.relative_to(td)}")
    print("  ---- arc ----")
    print("  " + (sdir/"mystory_story_arc.yaml").read_text().replace("\n", "\n  "))
    print("  ---- validate that generated story ----")
    r = sm.validate_story("mystory")
    print("  is_valid:", r.is_valid, "errors:", r.errors, "warnings:", r.warnings)

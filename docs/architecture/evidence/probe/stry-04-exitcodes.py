"""STRY-04: story_tool.py exit codes for CI.

Builds a temp copy with one BROKEN story (arc + intro, events file WITHOUT a
story_start event) plus the two shipped stories, then runs the real CLI as a
subprocess with --stories-path/--events-path pointing at the copy:
  a) validate <broken>          -> expect 'never exits non-zero'
  b) validate <nonexistent>     -> ?
  c) validate (all)             -> expect exit 1 (line 114)
  d) info <broken>              -> expect exit 0 despite FAILED validation
  e) info <nonexistent>         -> expect exit 1 (line 136)
  f) no command                 -> expect exit 0 (help path, line 41-43)
"""
import os, shutil, subprocess, sys
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
PKG = REPO / "text_adventure_tui_lib"
TMP = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-exitcodes")
if TMP.exists():
    shutil.rmtree(TMP)
shutil.copytree(PKG / "story_parts", TMP / "story_parts")
shutil.copytree(PKG / "events", TMP / "events")
sp, ep = TMP / "story_parts", TMP / "events"

# Broken story: valid YAML, list of events, but NO story_start.
(ep / "broken_story_story_events.yaml").write_text(
    "- id: some_other_event\n"
    "  name: Not The Start\n"
    "  trigger:\n"
    "    mode: AND\n"
    "    conditions:\n"
    "      - type: location\n"
    "        value: nowhere\n"
    "  actions:\n"
    "    - type: set_flag\n"
    "      value: broken\n"
)
(sp / "broken_story_story_arc.yaml").write_text(
    "title: Broken Story\nstarting_location: start\n"
    "initial_story_part: broken_story_intro.txt\n"
)
(sp / "broken_story_intro.txt").write_text("broken intro\n")

ENV = dict(os.environ, PYTHONPATH=str(REPO))
TOOL = str(REPO / "story_tool.py")

def run(*args):
    r = subprocess.run([sys.executable, TOOL, *args,
                        "--stories-path", str(sp), "--events-path", str(ep)],
                       capture_output=True, text=True, cwd=str(REPO))
    return r.returncode, r.stdout

for label, args, expect in [
    ("a) validate broken_story        ", ["validate", "broken_story"], "0 (BUG?)"),
    ("b) validate nonexistent_story   ", ["validate", "nonexistent_story"], "0 (BUG?)"),
    ("c) validate (all)               ", ["validate"], "1"),
    ("d) info broken_story            ", ["info", "broken_story"], "0 despite FAILED"),
    ("e) info nonexistent_story       ", ["info", "nonexistent_story"], "1"),
]:
    rc, out = run(*args)
    keep = [l for l in out.splitlines() if any(
        k in l for k in ("valid", "Valid", "❌", "✅", "Error", "not found"))]
    print("%s -> exit %d   (expect %s)" % (label, rc, expect))
    for l in keep[:6]:
        print("      |", l)
    print()

rc, out = run()
print("f) no command -> exit %d   (expect 0, help printed: %s)"
      % (rc, "usage:" in out))

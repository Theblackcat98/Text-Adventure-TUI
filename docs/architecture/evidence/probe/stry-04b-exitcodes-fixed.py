"""STRY-04b: same as stry-04 but global flags BEFORE the subcommand
(argparse rejects them after: exit 2 'unrecognized arguments').
Also prints stderr for one case to document the argparse rejection.
"""
import os, shutil, subprocess, sys
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
PKG = REPO / "text_adventure_tui_lib"
TMP = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-exitcodes")
sp, ep = TMP / "story_parts", TMP / "events"

ENV = dict(os.environ, PYTHONPATH=str(REPO))
TOOL = str(REPO / "story_tool.py")

def run(*args):
    r = subprocess.run([sys.executable, TOOL, "--stories-path", str(sp),
                        "--events-path", str(ep), *args],
                       capture_output=True, text=True, cwd=str(REPO))
    return r.returncode, r.stdout, r.stderr

print("flags AFTER subcommand (natural word order):")
rc, out, err = run("validate", "broken_story", "--stories-path", str(sp))
print("  exit %d | stderr: %s" % (rc, err.strip().splitlines()[-1] if err else ""))
print()

for label, args, expect in [
    ("a) validate broken_story        ", ["validate", "broken_story"], "0 (BUG: invalid story exits 0)"),
    ("b) validate nonexistent_story   ", ["validate", "nonexistent_story"], "0 (BUG)"),
    ("c) validate (all)               ", ["validate"], "1"),
    ("d) info broken_story            ", ["info", "broken_story"], "0 despite FAILED"),
    ("e) info nonexistent_story       ", ["info", "nonexistent_story"], "1"),
]:
    rc, out, err = run(*args)
    keep = [l for l in out.splitlines() if any(
        k in l for k in ("valid", "Valid", "❌", "✅", "Error", "not found"))]
    print("%s -> exit %d   (expect %s)" % (label, rc, expect))
    for l in keep[:6]:
        print("      |", l)
    print()

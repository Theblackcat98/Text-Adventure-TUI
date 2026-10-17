"""STRY-01: what happens when story_tool.py runs from a different working directory.

story_tool.py:13-18 defaults --stories-path/--events-path to RELATIVE Paths.
Run the tool as a subprocess from /tmp/opencode (cwd != repo root) and from the
repo root, and compare output + exit codes.
"""
import os
import subprocess
import sys

REPO = "/home/nick/Documents/Projects/Text-Adventure-TUI"
TOOL = os.path.join(REPO, "story_tool.py")
ENV = dict(os.environ, PYTHONPATH=REPO)

print("=== from repo root (cwd=repo) ===")
r = subprocess.run([sys.executable, TOOL, "list"], cwd=REPO, env=ENV,
                   capture_output=True, text=True)
print("returncode:", r.returncode)
for line in r.stdout.splitlines()[:5]:
    print("   ", line)
if r.stderr:
    print("stderr first 10 lines:")
    for line in r.stderr.splitlines()[:10]:
        print("   ", line)

print()
print("=== from /tmp/opencode (cwd != repo) ===")
r2 = subprocess.run([sys.executable, TOOL, "list"], cwd="/tmp/opencode", env=ENV,
                    capture_output=True, text=True)
print("returncode:", r2.returncode)
print("stdout:", repr(r2.stdout))
if r2.stderr:
    print("stderr (full):")
    print(r2.stderr)

print()
print("=== validate from /tmp/opencode ===")
r3 = subprocess.run([sys.executable, TOOL, "validate"], cwd="/tmp/opencode", env=ENV,
                    capture_output=True, text=True)
print("returncode:", r3.returncode)
print("stdout:", repr(r3.stdout))
if r3.stderr:
    print("stderr first 5 lines:")
    for line in r3.stderr.splitlines()[:5]:
        print("   ", line)

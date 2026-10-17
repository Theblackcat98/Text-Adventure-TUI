"""STRY probe: exit codes, F841, get_story_info cost, thread-safety."""
import subprocess, sys, time, os, tempfile, shutil, inspect
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
PY = sys.executable
env = dict(os.environ, PYTHONPATH=str(REPO))

def run(args, cwd=REPO):
    p = subprocess.run([PY, str(REPO/"story_tool.py"), *args], cwd=cwd, env=env,
                       capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip().splitlines()
    return p.returncode, out

print("=== exit codes (cwd = repo root) ===")
cases = [
    ([], "no subcommand -> help"),
    (["--help"], "explicit --help"),
    (["list"], "list"),
    (["validate"], "validate all"),
    (["validate", "the_clockwork_heist"], "validate known-good id"),
    (["validate", "does_not_exist"], "validate unknown id (INVALID)"),
    (["validate", "Whispers_of_the_Salted_Crypt"], "validate old-format dir id"),
    (["info", "the_clockwork_heist"], "info known-good"),
    (["info", "does_not_exist"], "info unknown"),
    (["bogus_command"], "unknown subcommand"),
    (["--bogus-flag", "list"], "unknown top-level flag"),
    (["list", "--bogus"], "unknown subcommand flag"),
    (["validate", "a", "b"], "too many positionals"),
    (["info"], "info with no id"),
    (["create"], "create with no args"),
]
for args, label in cases:
    rc, out = run(args)
    tail = out[-1] if out else ""
    print(f"  exit={rc:<3} {label:<40} | last line: {tail[:70]}")

print()
print("=== validate <id> on a story that FAILS validation: does it exit non-zero? ===")
tmp = Path(tempfile.mkdtemp(prefix="stry-tool2-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
shutil.copytree(REPO/"text_adventure_tui_lib/story_parts", tmp/"story_parts")
shutil.copytree(REPO/"text_adventure_tui_lib/events", tmp/"events")
(tmp/"story_parts/broken_story_story_arc.yaml").write_text("author: nobody\n")
p = subprocess.run([PY, str(REPO/"story_tool.py"), "--stories-path", str(tmp/"story_parts"),
                    "--events-path", str(tmp/"events"), "validate", "broken_story"],
                   cwd=REPO, env=env, capture_output=True, text=True)
print("  exit:", p.returncode)
print("  stdout:"); [print("   ", l) for l in p.stdout.strip().splitlines()]
p2 = subprocess.run([PY, str(REPO/"story_tool.py"), "--stories-path", str(tmp/"story_parts"),
                     "--events-path", str(tmp/"events"), "validate"],
                    cwd=REPO, env=env, capture_output=True, text=True)
print("  validate-all exit:", p2.returncode)
print("  validate-all stdout:"); [print("   ", l) for l in p2.stdout.strip().splitlines()]

print()
print("=== info <id> where validation FAILS: exit code? ===")
p3 = subprocess.run([PY, str(REPO/"story_tool.py"), "--stories-path", str(tmp/"story_parts"),
                     "--events-path", str(tmp/"events"), "info", "broken_story"],
                    cwd=REPO, env=env, capture_output=True, text=True)
print("  exit:", p3.returncode)
print("  stdout:"); [print("   ", l) for l in p3.stdout.strip().splitlines()]

print()
print("=== flake8 on story_tool.py (F841 for list_parser) ===")
p4 = subprocess.run(["flake8", "--select=F841,F401,E501", str(REPO/"story_tool.py"),
                     str(REPO/"text_adventure_tui_lib/story_manager.py")],
                    cwd=REPO, capture_output=True, text=True)
print("  exit:", p4.returncode); print(p4.stdout.strip() or "  (clean)")

print()
print("=== get_story_info cost: N stories, N calls ===")
sys.path.insert(0, str(REPO))
from text_adventure_tui_lib.story_manager import StoryManager
SP, EP = REPO/"text_adventure_tui_lib/story_parts", REPO/"text_adventure_tui_lib/events"
big = Path(tempfile.mkdtemp(prefix="stry-cost-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
(big/"story_parts").mkdir(); (big/"events").mkdir()
arc0 = (SP/"the_clockwork_heist_story_arc.yaml").read_text()
N = 200
for i in range(N):
    (big/"story_parts"/f"s{i:03d}_story_arc.yaml").write_text(arc0)
mb = StoryManager(big/"story_parts", big/"events")
t0 = time.perf_counter(); [mb.discover_stories() for _ in range(5)]
t_d = (time.perf_counter()-t0)/5
t0 = time.perf_counter(); [mb.get_story_info(f"s{i:03d}") for i in range(N)]
t_i = time.perf_counter()-t0
print(f"  N={N} stories")
print(f"  discover_stories() x1 = {t_d*1000:.2f} ms  ({N} files parsed, {N*t_d/1000/N*1:.0f})")
print(f"  get_story_info() x{N} = {t_i*1000:.2f} ms  => {t_i/(t_d)*1:.1f}x the cost of ONE discover_stories()")
print(f"  arc files parsed by get_story_info for ONE question about ONE story: {N}")
print(f"  IO calls: {N} opens + {N} yaml.safe_load per get_story_info call")

print()
print("=== StoryManager state / thread-safety ===")
sm = StoryManager(SP, EP)
print("  __dict__ keys:", list(sm.__dict__.keys()))
print("  dataclasses on the class?", [n for n in dir(sm) if not n.startswith('_')])
print("  locks / caches:", [k for k in sm.__dict__ if 'lock' in k or 'cache' in k])

print()
print("=== relative-path defaults, from 3 different cwds ===")
for cwd in [REPO, Path("/home/nick"), Path(tempfile.gettempdir())]:
    rc, out = run(["list"], cwd=cwd)
    print(f"  cwd={str(cwd):<55} exit={rc} first={out[0] if out else ''!r}")
print()
print("tmpdirs:", tmp, big)

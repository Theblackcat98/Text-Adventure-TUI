"""Probe: build a wheel from a PRISTINE COPY of the repo (never touches the repo)."""
import subprocess, sys, pathlib, shutil, zipfile, os

REPO = pathlib.Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
WORK = pathlib.Path("/tmp/opencode/cdd-text-adventure-tui/probe/buildsrc")
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)

# copy tracked files only, so the working tree stays untouched
files = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True).stdout.split()
print(f"copying {len(files)} tracked files")
for f in files:
    src = REPO / f
    dst = WORK / f
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

out = WORK / "_dist"
r = subprocess.run([sys.executable, "-m", "build", "--outdir", str(out), str(WORK)],
                   capture_output=True, text=True)
print("build rc:", r.returncode)
print(r.stdout[-3000:])
print(r.stderr[-2000:])

whls = sorted(out.glob("*.whl"))
for w in whls:
    print("=" * 70)
    print("WHEEL:", w.name)
    z = zipfile.ZipFile(w)
    for n in sorted(z.namelist()):
        print("   ", n)
    ep = [n for n in z.namelist() if n.endswith("entry_points.txt")]
    if ep:
        print("ENTRY_POINTS:", repr(z.read(ep[0]).decode()))

"""STRY probe 5: cost of get_story_info() re-running discover_stories()."""
import time, shutil, tempfile, tracemalloc
from pathlib import Path
import yaml
from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SRC = REPO / "text_adventure_tui_lib/story_parts/whispers_of_the_salted_crypt_story_arc.yaml"
src = SRC.read_text()

print("N      arcfiles  discover_stories()      get_story_info(story_0)   ratio")
print("-" * 76)
rows = []
for n in (1, 2, 10, 50, 100, 250):
    tmp = Path(tempfile.mkdtemp(prefix=f"stry-cost-{n}-",
                                dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
    SP, EP = tmp / "story_parts", tmp / "events"
    SP.mkdir(); EP.mkdir()
    for i in range(n):
        (SP / f"s{i:04d}_story_arc.yaml").write_text(
            src.replace("Whispers of the Salted Crypt", f"Story {i}"))
        (EP / f"s{i:04d}_story_events.yaml").write_text("- id: story_start\n")
    m = StoryManager(SP, EP)
    # warm caches
    m.discover_stories()
    t0 = time.perf_counter()
    for _ in range(10):
        m.discover_stories()
    t_dis = (time.perf_counter() - t0) / 10
    m.get_story_info("s0000")
    t0 = time.perf_counter()
    for _ in range(10):
        m.get_story_info("s0000")
    t_info = (time.perf_counter() - t0) / 10
    print(f"{n:<6} {n:<10} {t_dis*1000:8.3f} ms      {t_info*1000:8.3f} ms          "
          f"{t_info/t_dis:.2f}x")
    rows.append((n, t_dis, t_info))
    shutil.rmtree(tmp)

n, t_dis, t_info = rows[-1]
print(f"\nAt N={n}: one main_menu redraw costs {t_dis*1000:.2f} ms; "
      f"one `info` lookup costs {t_info*1000:.2f} ms (reads {n} arcs, "
      f"parses {n} YAML docs, then uses 1).")
print(f"Per-arc marginal cost ~= {(t_dis)/n*1e6:.1f} us of yaml.safe_load + open.")

# memory
tmp = Path(tempfile.mkdtemp(prefix="stry-mem-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP, EP = tmp / "story_parts", tmp / "events"; SP.mkdir(); EP.mkdir()
for i in range(100):
    (SP / f"s{i:04d}_story_arc.yaml").write_text(src)
m = StoryManager(SP, EP)
tracemalloc.start()
res = m.discover_stories()
cur, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"\ndiscover_stories() on 100 arcs -> {len(res)} StoryInfo objects, "
      f"{cur/1024:.1f} KiB retained.")
tracemalloc.start()
m.get_story_info("s0050")
cur2, peak2 = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"get_story_info('s0050')        -> {cur2/1024:.1f} KiB transient (peak {peak2/1024:.1f} KiB).")
shutil.rmtree(tmp)

# StoryInfo vs Story field overlap
from text_adventure_tui_lib.data_structures import Story
import dataclasses
a = {f.name for f in dataclasses.fields(StoryManager.__module__ and __import__('text_adventure_tui_lib.story_manager', fromlist=['StoryInfo']).StoryInfo)}
b = {f.name for f in dataclasses.fields(Story)}
print("\nStoryInfo fields :", sorted(a))
print("Story fields     :", sorted(b))
print("shared           :", sorted(a & b))
print("StoryInfo-only   :", sorted(a - b))
print("Story-only       :", sorted(b - a))

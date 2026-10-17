"""STRY probe 6: is StoryManager stateful / re-entrant / thread-safe?"""
import threading, time
from pathlib import Path
from text_adventure_tui_lib.story_manager import StoryManager, StoryInfo, ValidationResult
import dataclasses, inspect

print("== instance attributes after __init__ ==")
REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
SP = REPO / "text_adventure_tui_lib/story_parts"
EP = REPO / "text_adventure_tui_lib/events"
m = StoryManager(SP, EP)
print("  ", vars(m))
print("   __dict__ keys:", sorted(vars(m)))
print("   dataclass?", dataclasses.is_dataclass(StoryManager), "| slots?", hasattr(StoryManager, '__slots__'))
print("   __init__ signature:", inspect.signature(StoryManager.__init__))
print("   mutable module-level state in story_manager:",
      [k for k, v in vars(__import__('text_adventure_tui_lib.story_manager', fromlist=['x'])).items()
       if not k.startswith('__') and isinstance(v, (list, dict, set))])

print("\n== re-entrancy: no instance attribute is ever reassigned ==")
src = inspect.getsource(StoryManager)
for i, line in enumerate(src.splitlines(), start=35):
    if "self." in line:
        print(f"   {i}: {line.strip()}")

print("\n== thread safety: 8 threads sharing one manager ==")
errs = []
def worker(i):
    try:
        for _ in range(60):
            r = m.validate_story("the_clockwork_heist")
            assert r.is_valid, r
            s = m.get_story_info("whispers_of_the_salted_crypt")
            assert s is not None
    except Exception as e:
        errs.append(repr(e))
ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
t0 = time.perf_counter()
[t.start() for t in ts]; [t.join() for t in ts]
print(f"   8 threads x 60 (validate+get_story_info) in {time.perf_counter()-t0:.2f}s, errors={errs}")
print("   NOTE: shared state is read-only, so this is safe; but it is not declared anywhere.")

print("\n== create_story_template IS a mutation of the filesystem from an 'inert' object ==")
print("   StoryManager holds only 2 Paths; create_story_template writes 3 files and")
print("   returns None -- callers cannot tell success from failure other than the print().")
print("   Signature:", inspect.signature(StoryManager.create_story_template))

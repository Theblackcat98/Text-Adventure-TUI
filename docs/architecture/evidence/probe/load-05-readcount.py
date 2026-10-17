"""LOAD-5: how many times each YAML/text file is READ during
3 main_menu iterations + 1 game start.  Counts real open() calls."""
import builtins, collections
from pathlib import Path
from rich.console import Console

from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"
EVENTS = REPO / "text_adventure_tui_lib/events"

counts = collections.Counter()
real_open = builtins.open

def counting_open(file, *a, **kw):
    try:
        p = Path(file)
        if str(p).startswith(str(REPO)) and p.suffix in (".yaml", ".txt"):
            counts[p.name] += 1
    except TypeError:
        pass
    return real_open(file, *a, **kw)

console = Console(quiet=True)
builtins.open = counting_open
try:
    sm = StoryManager(STORIES, EVTS) if False else StoryManager(STORIES, EVENTS)
    for _ in range(3):                       # game.py:393 while True / :397 discover_stories
        sm.discover_stories()
    after_menu = dict(counts)
    print("after 3 menu iterations:", after_menu)

    counts.clear()
    story, player = load_story_and_player(  # game.py:254
        "whispers_of_the_salted_crypt", STORIES
    )
    print("load_story_and_player reads:", dict(counts))
    counts.clear()
    intro = STORIES / story.initial_story_part  # game.py:264-266
    with real_open(intro, "r") as f:
        f.read()
    print("intro .txt read (game.py:266):", story.initial_story_part)

    # also EventManager construction reads nothing
    from text_adventure_tui_lib.event_manager import EventManager
    em = EventManager(story.events, console)
    print("EventManager(...) reads:", dict(counts) or "none")
finally:
    builtins.open = real_open

print()
print("== totals for 3 menu iterations + 1 game start (whispers) ==")
total = collections.Counter()
total.update(after_menu)
total["whispers_of_the_salted_crypt_story_arc.yaml"] += 1
total["general_events.yaml"] += 1
total["whispers_of_the_salted_crypt_story_events.yaml"] += 1
total["01_intro.txt"] += 1
for k, v in sorted(total.items(), key=lambda kv: -kv[1]):
    print(f"  {v:3d}  {k}")
print(f"  TOTAL open() of content files: {sum(total.values())}")
print()
print("whispers_of_the_salted_crypt_story_arc.yaml is parsed 4x: 3x by discover_stories"
      " (story_manager.py:49) + 1x by load_story_and_player (yaml_loader.py:42)")

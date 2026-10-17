"""Probe DATA-11: are the `story.<field>` reads in game.py / story_tool.py /
story_manager.py reading the Story DATACLASS or the StoryInfo dataclass?"""
import json
from pathlib import Path

from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.story_manager import StoryManager, StoryInfo
from text_adventure_tui_lib.yaml_loader import load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")

print("A. StoryInfo is a DIFFERENT class from Story")
print("   Story    ->", Story.__module__, Story.__qualname__)
print("   StoryInfo->", StoryInfo.__module__, StoryInfo.__qualname__)
print("   same class?", Story is StoryInfo)
print("   Story fields  :", sorted(Story.__dataclass_fields__))
print("   StoryInfo fls :", sorted(StoryInfo.__dataclass_fields__))

print("\nB. what discover_stories() actually returns")
sm = StoryManager(LIB / "story_parts", LIB / "events")
infos = sm.discover_stories()
for i in infos:
    print(f"   {type(i).__qualname__:10} id={i.id!r}")

print("\nC. fields that exist only on StoryInfo, never on a Story instance")
for f in sorted(StoryInfo.__dataclass_fields__):
    print(f"   {f:24} on StoryInfo={hasattr(infos[0], f)}")

print("\nD. real Story instance from yaml_loader")
story, player = load_story_and_player("the_clockwork_heist", LIB / "story_parts")
for k in Story.__dataclass_fields__:
    print(f"   Story.{k:24} = {getattr(story, k)!r:.70}")

print("\nE. yaml_loader.py:82-91 assigns 10 fields AFTER the constructor")
fresh = Story(id="x", title="X")
print("   fresh Story defaults: starting_location=%r initial_story_part=%r version=%r"
      % (fresh.starting_location, fresh.initial_story_part, fresh.version))

print("\nF. exact JSON key set emitted for Story")
d = json.loads(json.dumps(story, default=lambda o: o.__dict__))
print("   ", sorted(d.keys()))
print("   == Story.__dataclass_fields__ keys?",
      sorted(d.keys()) == sorted(Story.__dataclass_fields__))

print("\nG. can a Story be built without ever going through yaml_loader?")
print("   Story(id='x', title='X') works ->", Story(id="x", title="X").events)

"""STRY-03: does a story created by create_story_template actually validate and start?

Replicates the shipped directory layout in a temp copy, points StoryManager at
the COPY (never touches the repo), then:
  1. create_story_template('probe_story', ...)
  2. validate_story('probe_story')           -> ValidationResult
  3. load_story_and_player('probe_story',..) -> Story + Player (what game.py:254 does)
  4. EventManager + GameState exactly like game.py:255-261
  5. execute_event_actions('story_start') like game.py:272
  6. pre-choice sweep  check_and_trigger_events(gsm, "", []) like game.py:285-287
  7. player turn       check_and_trigger_events(gsm, "look around the desk", [], "")
     -> does example_event fire (substring keyword match, event_manager.py:191-197)?
  8. show resulting flags/location + which narrative pieces came back
"""
import shutil, sys
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
PKG = REPO / "text_adventure_tui_lib"
TMP = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-template")
if TMP.exists():
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)
shutil.copytree(PKG / "story_parts", TMP / "story_parts")
shutil.copytree(PKG / "events", TMP / "events")

sys.path.insert(0, str(REPO))
from rich.console import Console
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState

sp, ep = TMP / "story_parts", TMP / "events"
mgr = StoryManager(sp, ep)

print("1. create_story_template('probe_story', 'Probe Story', 'Tester')")
mgr.create_story_template("probe_story", "Probe Story", "Tester")

print()
print("2. files written:")
for p in sorted(TMP.rglob("probe_story*")):
    print("   ", p.relative_to(TMP))

print()
print("3. validate_story('probe_story'):")
res = mgr.validate_story("probe_story")
print("   is_valid:", res.is_valid)
print("   errors:", res.errors)
print("   warnings:", res.warnings)

print()
print("4. discover_stories sees it:", [s.id for s in mgr.discover_stories()])

print()
print("5. load_story_and_player (the game.py:254 call):")
story, player = load_story_and_player("probe_story", sp)
print("   story.id:", story.id, "| title:", story.title)
print("   starting_location:", story.starting_location)
print("   initial_story_part:", story.initial_story_part)
print("   checkpoints:", story.checkpoints)
print("   event ids in load order:", [e.id for e in story.events])

print()
print("6. engine spin-up exactly like game.py:255-261:")
game_state = GameState(current_story=story, player=player,
                       current_location=story.starting_location)
gsm = GameStateManager(game_state)
em = EventManager(story.events, Console(quiet=True))
print("   initial location:", gsm.get_current_location(),
      "| turn:", gsm.get_turn_count())

print()
print("7. manual story_start execution (game.py:272):")
r = em.execute_event_actions("story_start", gsm, [])
print("   override_narrative:", r.get("override_narrative"))
print("   location after story_start:", gsm.get_current_location())
print("   story_start recorded as triggered?", "story_start" in em.triggered_event_ids)

print()
print("8. pre-choice sweep with empty input (game.py:285-287), turn still 0:")
r2 = em.check_and_trigger_events(gsm, "", [])
print("   example_event fired?", r2["injected_narratives_post"] != [] or r2["override_narrative"] is not None)

print()
print("9. player types 'I look around the desk' (game.py:313 call shape):")
r3 = em.check_and_trigger_events(gsm, "I look around the desk", [], "")
print("   injected_post:", r3["injected_narratives_post"])
print("   override:", r3["override_narrative"])
print("   flags now:", gsm.get_flags())
print("   example_event marked once-triggered:", "example_event" in em.triggered_event_ids)

print()
print("10. repeat same input (once=True):")
r4 = em.check_and_trigger_events(gsm, "I look around the desk", [], "")
print("   injected_post:", r4["injected_narratives_post"])

print()
print("11. raw events file the template wrote (story_start trigger):")
import yaml
data = yaml.safe_load((ep / "probe_story_story_events.yaml").read_text())
for ev in data:
    print("   id=%s trigger=%s options=%s" % (ev["id"], ev["trigger"], ev.get("options")))
    for a in ev["actions"]:
        print("      action:", a)

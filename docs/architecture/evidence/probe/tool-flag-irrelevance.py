"""Probe: does game_state.flags["current_location"] matter for a `location` trigger?

Reproduces test_new_engine.py:71-92 and test_game_engine.py:62-85, then runs the
same scenario WITHOUT the flags write, and also with a bogus value.
"""
import sys
sys.path.insert(0, "/home/nick/Documents/Projects/Text-Adventure-TUI")
from text_adventure_tui_lib.data_structures import GameState, Player, Story, Event
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console


def run(write_flag, flag_value):
    event = Event(id="test_event", name="Test",
                  trigger={"mode": "AND", "conditions": [{"type": "location", "value": "start"}]},
                  actions=[{"type": "set_flag", "value": "event_triggered"}],
                  options={})
    story = Story(id="test", title="Test", events=[event])
    gs = GameState(current_story=story, player=Player())
    if write_flag:
        gs.flags["current_location"] = flag_value
    gsm = GameStateManager(gs)
    em = EventManager(story.events, Console())
    res = em.check_and_trigger_events(gsm, "", [])
    return gs, res


gs, res = run(True, "start")
print("A) with flags['current_location']='start'  -> flag set:", gs.flags.get("event_triggered"), "added_choices:", res["added_choices"])

gs2, res2 = run(False, None)
print("B) NO flags write at all                    -> flag set:", gs2.flags.get("event_triggered"), "added_choices:", res2["added_choices"])

gs3, res3 = run(True, "TOTALLY_BOGUS_LOCATION")
print("C) flags['current_location']='TOTALLY_BOGUS' -> flag set:", gs3.flags.get("event_triggered"), "added_choices:", res3["added_choices"])

print("D) GameState default current_location:", repr(GameState(current_story=Story(id='s',title='s'), player=Player()).current_location))

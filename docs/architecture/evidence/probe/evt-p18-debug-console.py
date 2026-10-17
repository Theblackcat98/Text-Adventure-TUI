"""Probe: does the :60-62 DEBUG line actually emit? Use a FIREABLE trigger."""
import io
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

story = Story(id="t", title="t")
gs = GameState(current_story=story, player=Player(), flags={}, turn_count=0,
               current_location="start", turns_in_location=0)
gsm = GameStateManager(gs)
trig = {"mode": "AND", "conditions": [{"type": "location", "value": "start"}]}

def mk(c):
    return EventManager([Event(id="dbg", name="", trigger=trig, actions=[], options={})], c)

buf = io.StringIO(); c = Console(file=buf, width=120, no_color=True)
mk(c).check_and_trigger_events(gsm, "x", [], "")
print("check_and_trigger_events (fires)  :", repr(buf.getvalue()))

buf = io.StringIO(); c = Console(file=buf, width=120, no_color=True)
mk(c).execute_event_actions("dbg", gsm, [])
print("execute_event_actions (live def)  :", repr(buf.getvalue()), "<- silent")

buf = io.StringIO(); c = Console(file=buf, width=120, no_color=True)
mk(c).execute_event_actions("NOPE", gsm, [])
print("execute_event_actions (missing id):", repr(buf.getvalue()), "<- silent")

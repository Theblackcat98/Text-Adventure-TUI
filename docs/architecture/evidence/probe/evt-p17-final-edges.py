"""Probe: remaining edges - actions=None, DEBUG leakage, dict-shape asymmetry."""
import yaml
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

console = Console(quiet=True)
story = Story(id="t", title="t")
gs = GameState(current_story=story, player=Player(), flags={}, turn_count=0,
               current_location="start", turns_in_location=0)
gsm = GameStateManager(gs)

print("A) YAML `actions:` with a null value -> Event.actions is None")
em = EventManager([Event(id="n", name="", trigger={"mode": "MANUAL"}, actions=None, options={})], console)
try:
    em.execute_event_actions("n", gsm, [])
    print("   ok")
except Exception as e:
    print("   RAISES", type(e).__name__, ":", e)
print("   yaml_loader.py:24 `data.get('actions', [])` returns None when the key is")
print("   present-but-null; the default only covers a MISSING key.")

print("\nB) trigger key missing entirely -> Event.trigger == {} -> dead")
em2 = EventManager([Event(id="t0", name="", trigger={}, actions=[{"type": "set_flag", "value": "x"}], options={})], console)
print("   check_and_trigger_events ->", em2.check_and_trigger_events(gsm, "anything", [], ""),
      " flags:", gs.flags)

print("\nC) return-dict shape asymmetry between the two execute_event_actions paths")
em3 = EventManager([Event(id="ok", name="", trigger={"mode": "MANUAL"}, actions=[], options={})], console)
a = sorted(em3.execute_event_actions("ok", gsm, []).keys())
b = sorted(em3.execute_event_actions("MISSING", gsm, []).keys())
print("   found   :", a)
print("   not-found:", b)
print("   not-found has the extra key 'modified_prompt_instructions'; _perform_actions does not.")
print("   game.py:273 / :305 both use .get('override_narrative') so the gap is invisible.")

print("\nD) DEBUG print at event_manager.py:60-62 still runs for every triggered event")
import io
buf = io.StringIO()
c2 = Console(file=buf, force_terminal=False, width=200)
em4 = EventManager([Event(id="dbg", name="", trigger={"mode": "MANUAL"}, actions=[], options={})], c2)
em4.check_and_trigger_events(gsm, "x", [], "")
print("   emitted:", repr(buf.getvalue()))
print("   execute_event_actions emits NOTHING (dead :26-29 and :32-35).")

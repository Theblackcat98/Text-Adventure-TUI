"""Probe DATA-4: do tests/test_game_engine.py:76 and tests/test_new_engine.py:85
pass for the right reason?  They write flags['current_location']='start',
which is a FLAG, not game_state.current_location."""
from text_adventure_tui_lib.data_structures import GameState, Player, Story, Event
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console

print("A. GameState default current_location")
s = Story(id="test", title="Test", events=[])
gs = GameState(current_story=s, player=Player())
print("   current_location =", repr(gs.current_location),
      "  <- data_structures.py:44 default is 'start'")
print("   flags            =", gs.flags)

print("\nB. exact test_new_engine.py:71-92 scenario")
event = Event(
    id="test_event", name="Test",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "start"}]},
    actions=[{"type": "set_flag", "value": "event_triggered"}],
    options={},
)
story = Story(id="test", title="Test", events=[event])
game_state = GameState(current_story=story, player=Player())
game_state.flags["current_location"] = "start"
gsm = GameStateManager(game_state)
print("   flags now              :", gsm.get_flags())
print("   current_location now   :", repr(gsm.get_current_location()))
print("   the 'location' condition reads get_current_location() "
      "(event_manager.py:186), NOT flags.")
res = EventManager(story.events, Console(quiet=True)).check_and_trigger_events(gsm, "", [])
print("   event fired?           :", bool(gsm.get_flags().get("event_triggered")))
print("   added_choices          :", res["added_choices"])

print("\nC. delete the bogus flag and re-run the same assertion")
del game_state.flags["current_location"]
res2 = EventManager(story.events, Console(quiet=True)).check_and_trigger_events(gsm, "", [])
print("   event fired without the flag?:",
      bool(gsm.get_flags().get("event_triggered")),
      " <- the assertion in test_new_engine.py:92 is driven by the "
      "DEFAULT current_location, not by the flag it sets")
print("   flags:", gsm.get_flags())

print("\nD. would the test fail if the default were anything but 'start'?")
game_state2 = GameState(current_story=story, player=Player(),
                        current_location="somewhere_else")
game_state2.flags["current_location"] = "start"
gsm2 = GameStateManager(game_state2)
EventManager(story.events, Console(quiet=True)).check_and_trigger_events(gsm2, "", [])
print("   fired?:", bool(gsm2.get_flags().get("event_triggered")))

print("\nE. does a 'flag_set' condition see the bogus flag?")
ev2 = Event(
    id="flag_ev", name="F",
    trigger={"mode": "AND", "conditions": [{"type": "flag_set", "value": "current_location"}]},
    actions=[{"type": "set_flag", "value": "flag_style_fired"}],
    options={},
)
gs3 = GameState(current_story=s, player=Player())
GameStateManager(gs3).set_flag("current_location")   # string 'start' -> True
EventManager([ev2], Console(quiet=True)).check_and_trigger_events(
    GameStateManager(gs3), "", [])
print("   flag_set current_location fired?:",
      bool(gs3.flags.get("flag_style_fired")),
      " <- the flag IS live, it just is not what the test asserts")

print("\nF. type hole: flags is annotated Dict[str, bool] but the tests "
      "store a str")
print("   value type stored:", type(gs3.flags["current_location"]).__name__,
      " while annotation is Dict[str, bool]")

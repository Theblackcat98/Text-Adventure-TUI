"""FLOW-3 probe 5: which condition types can fire in the PRE-CHOICE event
pass, where player_input_text='' and player_intent='' (game.py:285-287).
Direct _evaluate_trigger matrix (evt:163-258)."""
import f3_common as C
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from rich.console import Console

sink = Console(file=C and __import__("io").StringIO(), width=200)


def gsm(turn=0, loc="study", turns_in_loc=0, flags=None, inv=None, stats=None):
    st = Story(id="s", title="s")
    gs = GameState(current_story=st,
                   player=Player(stats=stats or {"health": 100},
                                 inventory=inv if inv is not None else []),
                   flags=flags or {}, turn_count=turn,
                   current_location=loc, turns_in_location=turns_in_loc)
    return GameStateManager(gs)


def ev(cond, mode="AND"):
    return {"mode": mode, "conditions": [cond]}


def fires(trigger, manager_gsm, text="", intent=""):
    m = EventManager([], sink)
    return m._evaluate_trigger(trigger, manager_gsm, text, intent)


M0 = gsm()  # turn 0, study, turns_in_location 0, no flags, empty inventory
M1 = gsm(turn=1, turns_in_loc=1, flags={"f": True}, inv=["key"],
         stats={"health": 50})

rows = [
    ("location",              ev({"type": "location", "value": "study"}), M0, True),
    ("location (wrong)",      ev({"type": "location", "value": "coast"}), M0, False),
    ("flag_set (set)",        ev({"type": "flag_set", "value": "f"}), M1, True),
    ("flag_set (unset)",      ev({"type": "flag_set", "value": "f"}), M0, False),
    ("flag_not_set (unset)",  ev({"type": "flag_not_set", "value": "f"}), M0, True),
    ("flag_not_set (set)",    ev({"type": "flag_not_set", "value": "f"}), M1, False),
    ("inventory_has (have)",  ev({"type": "inventory_has", "value": "key"}), M1, True),
    ("inventory_has (lack)",  ev({"type": "inventory_has", "value": "key"}), M0, False),
    ("inventory_not_has",     ev({"type": "inventory_not_has", "value": "key"}), M0, True),
    ("game_start turn 0",     ev({"type": "game_start"}), M0, True),
    ("game_start turn 1",     ev({"type": "game_start"}), M1, False),
    ("turn_count_in_loc ==0", ev({"type": "turn_count_in_location", "value": 0, "operator": "=="}), M0, True),
    ("turn_count_in_loc >=1", ev({"type": "turn_count_in_location", "value": 1, "operator": ">="}), M1, True),
    ("turn_count_in_loc >=1 @0", ev({"type": "turn_count_in_location", "value": 1, "operator": ">="}), M0, False),
    ("turn_count_global ==0", ev({"type": "turn_count_global", "value": 0, "operator": "=="}), M0, True),
    ("turn_count_global ==1", ev({"type": "turn_count_global", "value": 1, "operator": "=="}), M1, True),
    ("stat_check >=50",       ev({"type": "stat_check", "stat": "health", "operator": ">=", "value": 50}), M0, True),
    ("stat_check <50",        ev({"type": "stat_check", "stat": "health", "operator": "<", "value": 50}), M0, False),
    ("player_action_keyword", ev({"type": "player_action_keyword", "keywords": ["x"]}), M0, False),
    ("player_intent 'x'",     ev({"type": "player_intent", "value": "x"}), M0, False),
    ("player_intent ''",      ev({"type": "player_intent", "value": ""}), M0, True),
    ("player_action 'x'",     ev({"type": "player_action", "value": "x"}), M0, False),
    ("player_action ''",      ev({"type": "player_action", "value": ""}), M0, True),
    ("MANUAL mode",           {"mode": "MANUAL", "conditions": [{"type": "game_start"}]}, M0, False),
    ("no conditions",         {"mode": "AND", "conditions": []}, M0, False),
    ("unknown type",          ev({"type": "flag_is_set", "value": "f"}), M1, False),
    ("OR with 1 true",        {"mode": "OR", "conditions": [
        {"type": "player_action_keyword", "keywords": ["x"]},
        {"type": "location", "value": "study"}]}, M0, True),
    ("AND with 1 false",      {"mode": "AND", "conditions": [
        {"type": "game_start"},
        {"type": "location", "value": "study"},
        {"type": "player_action_keyword", "keywords": ["x"]}]}, M0, False),
]
for name, trig, m, expected in rows:
    got = fires(trig, m)
    C.check("empty-input: " + name, got == expected, "got %s" % got)

# in-loop confirmation: player-typed text never reaches the post pass either
# (already proven in f3-normal: 'backflip' in no prompt); here: the chosen
# LABEL is the input that matches in the post pass.
story = C.make_story([
    Event(id="ev_lbl", name="lbl",
          trigger={"mode": "AND",
                   "conditions": [{"type": "player_action", "value": "opt1a"}]},
          actions=[{"type": "inject_narrative", "text": "LABEL-HIT", "position": "post"}]),
])
fake, out, oc = C.run(story, ["1", "1"])
C.check("post pass matches the raw LLM label (lowercased)",
        "LABEL-HIT" in out and out.count("Event 'ev_lbl' triggered!") >= 1)

C.done("f3-emptyinput")

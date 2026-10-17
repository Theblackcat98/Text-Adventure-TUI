"""Probe: condition-type table, unknown types, operators, modes."""
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Player, Story

console = Console(quiet=True)
story = Story(id="t", title="t")
em = EventManager([], console)


def ev(conds, mode="AND"):
    gs = GameState(current_story=story,
                   player=Player(stats={"health": 10}, inventory=["lamp"]), flags={"f": True},
                   turn_count=3, current_location="start", turns_in_location=2)
    return em._evaluate_trigger({"mode": mode, "conditions": conds},
                                GameStateManager(gs), "I search the Desk", "search_desk")


rows = [
    ("location", [{"type": "location", "value": "start"}]),
    ("location (mismatch)", [{"type": "location", "value": "crypt"}]),
    ("flag_set", [{"type": "flag_set", "value": "f"}]),
    ("flag_not_set", [{"type": "flag_not_set", "value": "g"}]),
    ("player_action_keyword mixed-case kw",
     [{"type": "player_action_keyword", "keywords": ["Search Desk"]}]),
    ("player_action_keyword out-of-order kw",
     [{"type": "player_action_keyword", "keywords": ["Desk Search"]}]),
    ("player_action_keyword 'get' in prose",
     [{"type": "player_action_keyword", "keywords": ["get"]}]),
    ("player_intent", [{"type": "player_intent", "value": "search_desk"}]),
    ("player_action exact", [{"type": "player_action", "value": "i search the DESK"}]),
    ("player_action non-exact", [{"type": "player_action", "value": "search"}]),
    ("inventory_has", [{"type": "inventory_has", "value": "lamp"}]),
    ("inventory_has item_id key", [{"type": "inventory_has", "item_id": "lamp"}]),
    ("inventory_not_has", [{"type": "inventory_not_has", "value": "rope"}]),
    ("game_start (turn_count==3)", [{"type": "game_start"}]),
    ("turn_count_in_location ==2", [{"type": "turn_count_in_location", "operator": "==", "value": 2}]),
    ("turn_count_global >=3", [{"type": "turn_count_global", "operator": ">=", "value": 3}]),
    ("stat_check health<=25", [{"type": "stat_check", "stat": "health", "operator": "<=", "value": 25}]),
    ("stat_check missing operator", [{"type": "stat_check", "stat": "health", "value": 10}]),
    ("UNKNOWN flag_is_set", [{"type": "flag_is_set", "value": "f"}]),
    ("UNKNOWN bogus_type", [{"type": "bogus_type", "value": "x"}]),
    ("stat_check missing stat key", [{"type": "stat_check", "value": 5}]),
]
for label, conds in rows:
    try:
        print(f"  {label:42s} -> {ev(conds)}")
    except Exception as e:
        print(f"  {label:42s} -> RAISES {type(e).__name__}: {e}")

print("\nmode / emptiness:")
print("  mode MANUAL + conditions      ->", ev([{"type": "location", "value": "start"}], "MANUAL"))
print("  mode MANUAL lower-case        ->", ev([{"type": "location", "value": "start"}], "manual"))
print("  empty conditions AND          ->", ev([]))
print("  empty conditions OR           ->", ev([], "OR"))
print("  mode NOT_A_MODE               ->", ev([{"type": "location", "value": "start"}], "XOR"))
print("  mode OR both false            ->", ev([{"type": "location", "value": "crypt"}], "OR"))
print("  mode AND one true one unknown ->",
      ev([{"type": "location", "value": "start"}, {"type": "flag_is_set", "value": "f"}]))
print("  mode OR one true one unknown  ->",
      ev([{"type": "location", "value": "crypt"}, {"type": "flag_is_set", "value": "f"}], "OR"))
print("  trigger_config is None        ->", end=" ")
try:
    print(em._evaluate_trigger(None, None, "x", "y"))
except Exception as e:
    print(f"RAISES {type(e).__name__}: {e}")

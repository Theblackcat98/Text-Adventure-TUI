"""Probe: update_stat edge cases (event_manager.py:116-120)."""
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

console = Console(quiet=True)


def run(actions, start_stats=None):
    story = Story(id="t", title="t")
    gs = GameState(current_story=story, player=Player(stats=dict(start_stats or {})),
                   flags={}, turn_count=0, current_location="start", turns_in_location=0)
    gsm = GameStateManager(gs)
    em = EventManager([Event(id="u", name="", trigger={"mode": "MANUAL"},
                             actions=actions, options={})], console)
    try:
        em.execute_event_actions("u", gsm, [])
        print("   -> ok, stats =", gs.player.stats)
    except Exception as e:
        print("   -> RAISES", type(e).__name__, ":", e, "| stats =", gs.player.stats)


print("1) well-formed: stat=stealth, change_by=-10 (clockwork:96-98)")
run([{"type": "update_stat", "stat": "stealth", "change_by": -10}], {"stealth": 80})

print("2) well-formed: stat=health, change_by=-20 (clockwork:272-274)")
run([{"type": "update_stat", "stat": "health", "change_by": -20}], {"health": 100})

print("3) change_by MISSING")
run([{"type": "update_stat", "stat": "health"}], {"health": 100})

print("4) stat MISSING, change_by present")
run([{"type": "update_stat", "change_by": 5}], {"health": 100})

print("5) change_by is a YAML string 'ten'")
run([{"type": "update_stat", "stat": "health", "change_by": "ten"}], {"health": 100})

print("6) change_by is 0")
run([{"type": "update_stat", "stat": "health", "change_by": 0}], {"health": 100})

print("7) stat exists but current value is a string (stat_check would also break)")
run([{"type": "update_stat", "stat": "mood", "change_by": 1}], {"mood": "calm"})

print("8) TWO update_stat actions in one event list, no change_by on the second")
run([{"type": "update_stat", "stat": "health", "change_by": -20},
     {"type": "set_flag", "value": "hit"},
     {"type": "update_stat", "stat": "health"}], {"health": 100})

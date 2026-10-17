"""Probe: old-format chapter files, flag_is_set runtime effect, save/load round-trip."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

SP = Path("text_adventure_tui_lib/story_parts")
console = Console(quiet=True)

print("### A) which format does the shipped id take?")
story, player = load_story_and_player("whispers_of_the_salted_crypt", SP)
print("  lowercase id ->", len(story.events), "events:",
      [e.id for e in story.events][:4], "...")
print("  chapter files present:",
      sorted(p.name for p in (SP / "Whispers_of_the_Salted_Crypt").glob("*.yaml")))
try:
    s2, p2 = load_story_and_player("Whispers_of_the_Salted_Crypt", SP)
    print("  Capitalised id (old-format fallback) ->", len(s2.events), "events:",
          [e.id for e in s2.events])
except Exception as e:
    print("  Capitalised id -> RAISES", type(e).__name__, ":", e)

print("\n### B) runtime effect of an unknown condition type (flag_is_set)")
gs = GameState(current_story=story, player=player, flags={"knows_about_bluffs": True},
               turn_count=0, current_location="start", turns_in_location=0)
gsm = GameStateManager(gs)
em = EventManager([], console)
for t in ("flag_is_set", "flag_set", "flag_not_set"):
    r = em._evaluate_trigger({"mode": "AND", "conditions": [{"type": t, "value": "knows_about_bluffs"}]},
                             gsm, "", "")
    print(f"  {t:14s} with the flag SET -> {r}")
print("  -> unknown type: `met` keeps its initialiser False (event_manager.py:184),")
print("     no else branch, no warning, appended to results at :252, so AND -> False.")

print("\n### C) get_state / load_state round-trip (event_manager.py:12-16)")
gs2 = GameState(current_story=story, player=player, flags={}, turn_count=0,
                current_location="start", turns_in_location=0)
gsm2 = GameStateManager(gs2)
em2 = EventManager([e for e in story.events if e.options.get("once")], console)
em2.check_and_trigger_events(gsm2, "search desk", [], "search_desk")
state = em2.get_state()
print("  get_state() ->", state)
em3 = EventManager([e for e in story.events if e.options.get("once")], console)
em3.load_state(state)
print("  after load_state, triggered =", sorted(em3.triggered_event_ids))
print("  load_state restores only the id set; the events dict itself is NOT saved,")
print("  so game.py:250 restores the set against a freshly loaded story.")
bad = em3.load_state({"triggered_event_ids": "not_a_list"})
print("  load_state({'triggered_event_ids': 'ab'}) ->", em3.triggered_event_ids,
      "  (string is turned into a set of chars)")
print("  load_state({}) ->", EventManager([], console).load_state({}) or "set()")

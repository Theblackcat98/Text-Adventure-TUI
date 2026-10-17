"""Probe: once-persistence, old-format flag_is_set events, first_time_in_location scope."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

SP = Path("text_adventure_tui_lib/story_parts")
console = Console(quiet=True)

story, player = load_story_and_player("whispers_of_the_salted_crypt", SP)
once_events = [e for e in story.events if e.options.get("once")]

print("### A) once events in the shipped Whispers story:",
      [e.id for e in once_events])
gs = GameState(current_story=story, player=player, flags={}, turn_count=0,
               current_location="elian_study", turns_in_location=0)
gsm = GameStateManager(gs)
em = EventManager(once_events, console)
em.check_and_trigger_events(gsm, "search desk", [], "search_desk")
state = em.get_state()
print("  get_state() after find_elians_journal ->", state)
em3 = EventManager(once_events, console)
em3.load_state(state)
print("  load_state then re-run the same input ->",
      em3.check_and_trigger_events(gsm, "search desk", [], "search_desk")["override_narrative"])
print("  -> resume correctly refuses to replay the once-event.")

print("\n### B) force_event BEFORE the natural trigger eats the single firing")
gs2 = GameState(current_story=story, player=player, flags={}, turn_count=0,
                current_location="elian_study", turns_in_location=0)
gsm2 = GameStateManager(gs2)
em4 = EventManager(once_events, console)
em4.execute_event_actions("find_elians_journal", gsm2, [])   # game.py:213
print("  after /force_event find_elians_journal -> flags:", sorted(gs2.flags),
      " inv:", gs2.player.inventory, " triggered:", sorted(em4.triggered_event_ids))
r = em4.check_and_trigger_events(gsm2, "search desk", [], "search_desk")
print("  later natural pass ->", r["override_narrative"],
      "| the desk prose never reaches the player via the normal path")

print("\n### C) old-format chapter events that use the UNIMPLEMENTED flag_is_set")
s_old, _ = load_story_and_player("Whispers_of_the_Salted_Crypt", SP)
for e in s_old.events:
    bad = [c for c in e.trigger.get("conditions", []) or []
           if c.get("type") not in {
               "location", "flag_set", "flag_not_set", "player_action_keyword",
               "player_intent", "player_action", "inventory_has",
               "inventory_not_has", "game_start", "turn_count_in_location",
               "turn_count_global", "stat_check"}]
    if bad:
        print(f"  {e.id}: unknown condition types {[c['type'] for c in bad]}")
gs3 = GameState(current_story=s_old, player=player, flags={"knows_about_bluffs": True},
                turn_count=0, current_location="elian_study", turns_in_location=0)
gsm3 = GameStateManager(gs3)
em5 = EventManager(s_old.events, console)
r = em5.check_and_trigger_events(gsm3, "", [], "")
print("  whole old-format story, every condition met, empty input ->",
      r["override_narrative"], "| triggered:", sorted(em5.triggered_event_ids))
print("  -> find_hidden_key (chapter1:67) can never fire in the old format either.")

print("\n### D) first_time_in_location (general:33) is once=True and location-agnostic")
gs4 = GameState(current_story=story, player=player, flags={}, turn_count=0,
                current_location="start", turns_in_location=0)
gsm4 = GameStateManager(gs4)
em6 = EventManager(story.events, console)
instr = []
em6.check_and_trigger_events(gsm4, "", instr, "")
gsm4.increment_turn(); gsm4.increment_turns_in_location()
em6.check_and_trigger_events(gsm4, "", instr, "")
print("  after 2 passes in `start`, instructions =", instr)
gsm4.set_current_location("saltstone_bluffs")   # gsm resets turns_in_location
gsm4.increment_turn()
em6.check_and_trigger_events(gsm4, "", instr, "")
print("  arriving at a NEW location does NOT re-fire it: instructions =", instr)

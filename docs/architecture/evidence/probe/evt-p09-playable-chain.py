"""Probe: (a) add_item(None) crashes get_llm_options, (b) clockwork playthrough,
(c) the rescue_elian -> present_choices -> player_action exact-match chain."""
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.yaml_loader import load_story_and_player

console = Console(quiet=True)


def load(name):
    story, player = load_story_and_player(
        name, Path("text_adventure_tui_lib/story_parts"))
    gs = GameState(current_story=story, player=player, flags={}, turn_count=0,
                   current_location=story.starting_location, turns_in_location=0)
    gsm = GameStateManager(gs)
    return story, gs, gsm, EventManager(story.events, console)


print("=== A) game.py:130 `', '.join(inventory)` when inventory holds None ===")
import text_adventure_tui_lib.game as g
g.ollama_client = None
story, gs, gsm, em = load("whispers_of_the_salted_crypt")
em.execute_event_actions("find_elians_journal", gsm, []) if False else None
# reproduce the state after a real 'search desk' turn
r = em.check_and_trigger_events(gsm, "search desk", [], "search_desk")
print("  inventory after find_elians_journal:", gs.player.inventory)
try:
    g.get_llm_options("narrative", gsm)
except Exception as e:
    print("  get_llm_options RAISES", type(e).__name__, ":", e)
    print("  -> the prompt f-string at game.py:127-137 is built BEFORE try: at 139,")
    print("     so the fallback at game.py:165 is never reached and game_loop dies.")

print("\n=== B) clockwork playthrough (inventory seeded by story_arc:7) ===")
story, gs, gsm, em = load("the_clockwork_heist")
em.execute_event_actions("story_start", gsm, [])
print("  start loc/inv:", gsm.get_current_location(), gs.player.inventory)
moves = ["scout the museum from the shadows", "sneak in quietly",
         "I sneak in quietly and look for the temporal gear",
         "use lockpicks to disable security",
         "use lockpicks to bypass the case and grab the temporal gear",
         "throw smoke", "throw smoke", "smoke"]
for t, mv in enumerate(moves):
    instr = []
    em.check_and_trigger_events(gsm, "", instr, "")
    r = em.check_and_trigger_events(gsm, mv, instr, "i")
    ov = r.get("override_narrative")
    print(f"  turn {t}: {mv[:52]:54s} -> {str(ov)[:40]!r:44s} loc={gsm.get_current_location()}"
          f" inv={gs.player.inventory} ended={gsm.get_flags().get('game_ended')}")
    gsm.increment_turn(); gsm.increment_turns_in_location()

print("\n=== C) rescue_elian present_choices -> player_action exact match ===")
story, gs, gsm, em = load("whispers_of_the_salted_crypt")
em.execute_event_actions("story_start", gsm, [])
gsm.set_current_location("crypt_antechamber")
gs.player.inventory.append("runic_key")       # bypass the add_item bug on purpose
gsm.set_flag("tide_is_low")
r = em.check_and_trigger_events(gsm, "use key", [], "use_item")
print("  rescue_elian override:", str(r["override_narrative"])[:40])
print("  added_choices        :", r["added_choices"])
print("  inventory after remove_item(value:):", gs.player.inventory)
label = r["added_choices"][0]["label"]
action = r["added_choices"][0]["action"]
print("\n  player picks menu item. game.py:190-197 returns:")
print("    label =", repr(label))
print("    action startswith 'trigger:' ?", action.startswith("trigger:"), "->",
      "returns (action, None) at game.py:197" if not action.startswith("trigger:")
      else "returns ('EVENT_TRIGGERED', id) at game.py:195")
r2 = em.check_and_trigger_events(gsm, action, [], "unknown_intent")
print("  check_and_trigger_events(player_action=%r) ->" % action,
      str(r2["override_narrative"])[:45])
print("  flags:", {k: v for k, v in gs.flags.items() if k.startswith("game_ended")})
print("\n  If the author had written action: 'trigger:end_story_success_heroic':")
r3 = em.execute_event_actions("end_story_success_heroic", gsm, [])
print("    game.py:301 path fires the actions DIRECTLY; the `player_action`")
print("    condition at whispers...yaml:227-228 is never evaluated.")
print("    override ->", str(r3["override_narrative"])[:45])
print("    triggered_event_ids ->", sorted(em.triggered_event_ids))

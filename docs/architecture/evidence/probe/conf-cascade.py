from pathlib import Path
import yaml
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
SP = LIB / "story_parts"
console = Console(quiet=True)

print("### 1. WHISPERS cascade: which flag breaks the chain first?")
story, player = load_story_and_player("whispers_of_the_salted_crypt", SP)
p = Player(stats={"health":100,"sanity":100,"knowledge":10}, inventory=[])
st = Story(id="w", title="W", events=story.events)
gsm = GameStateManager(GameState(current_story=st, player=p, current_location="start"))
em = EventManager(story.events, console)
em.execute_event_actions("story_start", gsm, [])
r = em.check_and_trigger_events(gsm, "Search desk", [], "")
print("  after 'Search desk': flags=", sorted(gsm.get_flags()), "inv=", gsm.get_inventory())
tests = {
  "read_journal_clue": [("inventory_has","elians_journal"),("flag_not_set","knows_about_bluffs")],
  "find_hidden_key":   [("flag_set","knows_about_bluffs")],
  "arrive_at_bluffs": [("flag_set","knows_about_bluffs")],
  "enter_the_crypt":  [("flag_set","tide_is_low")],
  "rescue_elian":     [("inventory_has","runic_key")],
}
for eid, conds in tests.items():
    ev = [e for e in story.events if e.id == eid][0]
    res = {t: em._evaluate_trigger({"mode":"AND","conditions":[{"type":t,"value":v}]}, gsm, "x", "") for t,v in conds}
    print(f"  {eid:20} -> {res}  => reachable: {all(res.values())}")
print("  knows_about_bluffs is set ONLY by read_journal_clue (whispers...yaml:65-66),")
print("  which is gated on inventory_has elians_journal, which needs add_item at :41-42 to")
print("  have written 'item_id:' instead of 'value:'. Chain broken at turn 1.")

print()
print("### 2. CLOCKWORK: inventory comes from the ARC, so only add_item is affected")
story2, player2 = load_story_and_player("the_clockwork_heist", SP)
print("  arc initial_inventory (the_clockwork_heist_story_arc.yaml:7) =", player2.inventory)
p2 = Player(stats={"health":100,"stealth":80,"cunning":70}, inventory=list(player2.inventory))
st2 = Story(id="c", title="C", events=story2.events)
gsm2 = GameStateManager(GameState(current_story=st2, player=p2, current_location="start"))
em2 = EventManager(story2.events, console)
em2.execute_event_actions("story_start", gsm2, [])
for lab, flags in [("Scout the museum from the shadows.", {}),
                   ("Sneak in through the service entrance.", {"museum_scouted": True}),
                   ("Find the Temporal Gear display case.", {"museum_scouted": True}),
                   ("Use lockpicks to bypass security.", {"museum_scouted": True, "found_gear_location": True, "inside_museum": True}),
                   ("Take gear.", {"museum_scouted": True,"inside_museum":True,"security_disabled":True,"found_gear_location":True})]:
    r = em2.check_and_trigger_events(gsm2, lab, [], "")
    print(f"  {lab!r:46} loc={gsm2.get_current_location():24} inv={gsm2.get_inventory()}")
    print(f"       flags={sorted(gsm2.get_flags())}")
print("  => the clockwork chain is NOT blocked; only add_item:186-187 is a no-op that leaves")
print("     the literal None in the inventory.")

print()
print("### 3. Consequence of the stray None: game.py:130 does ', '.join(inventory) OUTSIDE try")
print("  source of get_llm_options, lines 122-145:")
src = (LIB/"game.py").read_text(encoding="utf-8").splitlines()
for i in range(121, 146):
    print(f"  game.py:{i+1:3} {src[i]}")
try:
    ", ".join(gsm2.get_inventory())
except TypeError as e:
    print("  ', '.join([None]) ->", type(e).__name__ + ":", e)
print("  and that expression is evaluated while BUILDING the prompt string, i.e. before the")
print("  try: at game.py:139, so no fallback and no except branch can catch it.")

print()
print("### 4. is low_health_warning (general_events.yaml:4-18) reachable in either story?")
print("  stats declared: whispers health 100 (arc:9), clockwork health 100 (arc:9)")
print("  the only health mutation in any shipped event: clockwork:272-274  health -20")
print("  => health floor is 80; condition is health <= 25 (general_events.yaml:9-12). Never true.")
print("  the stealth -10 (clockwork:96-98) is never tested by ANY condition type "
      "(stat_check is used once, for health only).")

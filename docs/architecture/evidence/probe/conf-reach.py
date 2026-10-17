from pathlib import Path
import yaml
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import _create_events_from_data, load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
console = Console(quiet=True)

print("### A. could the legacy dir ever be loaded?  yaml_loader.py:38-45, 96-106")
sp = LIB / "story_parts"
arcs = sorted(sp.glob("*_story_arc.yaml"))
print("  files matching discover_stories()' glob (story_manager.py:44):",
      [a.name for a in arcs])
for a in arcs:
    sid = a.stem.replace("_story_arc", "")
    print(f"  arc {a.name}: story_name={sid!r} -> arc file exists=True -> "
          f"_load_story_old_format NOT called (yaml_loader.py:43-45)")
print("  legacy loader would need a story_name with NO *_story_arc.yaml; "
      "there is no such name in the repo:",
      [p.name for p in sp.iterdir() if p.is_dir() and p.name != "__pycache__"])
print("  and legacy loader would look for sp/<name>/  (yaml_loader.py:100), i.e. a")
print("  directory literally named after the story_id, not Whispers_of_the_Salted_Crypt")

print()
print("### B. collision if both copies were ever concatenated (event_manager.py:8)")
shipped = yaml.safe_load((LIB / "events/whispers_of_the_salted_crypt_story_events.yaml").read_text(encoding="utf-8"))
legacy = []
for f in sorted((sp / "Whispers_of_the_Salted_Crypt").glob("*.yaml")):
    legacy += yaml.safe_load(f.read_text(encoding="utf-8"))
both = shipped + legacy
evs = _create_events_from_data(both)
em = EventManager(evs, console)
print(f"  {len(both)} event dicts -> EventManager.events has {len(em.events)} entries "
      f"(dict comprehension at event_manager.py:8 keeps the LAST of each id)")
ids = [e["id"] for e in both]
dupes = sorted({i for i in ids if ids.count(i) > 1})
print("  silently shadowed ids:", dupes)
for d in dupes:
    kept = em.events[d]
    src = [f.name for f in (sp/"Whispers_of_the_Salted_Crypt").glob("*.yaml")
           if any(e["id"] == d for e in yaml.safe_load(f.read_text(encoding="utf-8")))]
    print(f"     {d}: surviving copy came from the legacy dir {src}; "
          f"its conditions are {[(c['type'], c.get('value')) for c in kept.trigger['conditions']]}")

print()
print("### C. reachability of every whispers beat, driven through EventManager")
story, player = load_story_and_player("whispers_of_the_salted_crypt", sp)
def fresh():
    p = Player(stats={"health": 100, "sanity": 100, "knowledge": 10}, inventory=[])
    st = Story(id="whispers_of_the_salted_crypt", title="W", events=story.events)
    g = GameState(current_story=st, player=p, current_location="start")
    return GameStateManager(g), EventManager(story.events, console)

# LLM choice labels chosen to hit each keyword list in turn
LABELS = [
    "Search desk for any clue.",
    "Read journal.",                 # inventory_has elians_journal -> needs the add_item bug fixed
    "Search bookshelf.",
    "Leave study.",
    "Look around.",                 # burn turns so tide_recedes (>=3) fires
    "Look around.",
    "Look around.",
    "Enter archway.",
    "Use key on the door.",
    "Take the gear.",
]
gsm, em = fresh()
em.execute_event_actions("story_start", gsm, [])
print(f"  start: location={gsm.get_current_location()} flags={sorted(gsm.get_flags())}")
print(f"         inventory={gsm.get_inventory()}")
for i, lab in enumerate(LABELS, 1):
    r = em.check_and_trigger_events(gsm, lab, [], f"intent_{i}")
    gsm.increment_turn(); gsm.increment_turns_in_location()
    print(f"  T{i:2} label={lab!r:34} override={'Y' if r['override_narrative'] else 'n'} "
          f"loc={gsm.get_current_location():18} inv={gsm.get_inventory()} flags={sorted(gsm.get_flags())}")
print("  end of run: game_ended =", gsm.get_flags().get("game_ended"))
print("  reached beats:", [e for e in ("story_start","find_elians_journal","read_journal_clue",
                                        "find_hidden_key","arrive_at_bluffs","tide_recedes",
                                        "enter_the_crypt","rescue_elian",
                                        "end_story_success_heroic","end_story_success_cautious")
                            if e in em.triggered_event_ids or e == "story_start"])
print("  NEVER triggered:", sorted({"story_start","find_elians_journal","read_journal_clue",
                                    "find_hidden_key","arrive_at_bluffs","tide_recedes",
                                    "enter_the_crypt","rescue_elian","end_story_success_heroic",
                                    "end_story_success_cautious"} - em.triggered_event_ids))

print()
print("### D. same run but with `inventory_has` manually satisfied, to isolate the add_item bug")
gsm2, em2 = fresh()
em2.execute_event_actions("story_start", gsm2, [])
gsm2.get_inventory().append("runic_key")   # simulate a FIXED add_item
for i, lab in enumerate(LABELS, 1):
    em2.check_and_trigger_events(gsm2, lab, [], f"intent_{i}")
    gsm2.increment_turn(); gsm2.increment_turns_in_location()
print("  with runic_key present, rescue_elian triggered?",
      "rescue_elian" in em2.triggered_event_ids,
      "| elian_is_found?", gsm2.get_flags().get("elian_is_found"))
print("  added_choices offered by rescue_elian were returned by the engine but dropped by game.py:294")

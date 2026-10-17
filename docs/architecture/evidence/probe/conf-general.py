from pathlib import Path
import yaml
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import _create_events_from_data

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
console = Console(quiet=True)
gen = yaml.safe_load((LIB / "events/general_events.yaml").read_text(encoding="utf-8"))

def mkinst(events, loc="start", stats=None, inv=None, flags=None):
    p = Player(stats=dict(stats or {}), inventory=list(inv or []))
    st = Story(id="t", title="t", events=events)
    gsm = GameStateManager(GameState(current_story=st, player=p,
                                      current_location=loc, flags=dict(flags or {})))
    return gsm, EventManager(events, console)

print("### A. inventory_full_warning false positives  (general_events.yaml:20-30)")
warnings = [e for e in gen if e["id"] == "inventory_full_warning"]
evs = _create_events_from_data(warnings)
SAMPLES = [
    "Look around the room.",
    "Examine the target on the wall.",          # 'get' substring of 'target'
    "Search for information about the runes.", # 'get' substring of 'information'
    "Take the brass key.",
    "Approach the hovering object.",
    "Remember the plan you discussed earlier.", # no match expected
    "Reach for the ledge.",
]
for s in SAMPLES:
    gsm, em = mkinst(evs, inv=[])   # inventory deliberately EMPTY - no capacity concept exists
    r = em.check_and_trigger_events(gsm, s, [], "")
    print(f"  input={s!r:45} inject_post={r['injected_narratives_post']}")

print()
print("### A2. does inventory size affect it at all?")
import inspect
print("  event has any numeric/capacity condition?",
      [c for e in warnings for c in e["trigger"]["conditions"]])
gsm, em = mkinst(evs, inv=["a","b","c","d","e","f","g","h","i","j","k"])
print("  with an 11-item inventory, input='Look around.':", em.check_and_trigger_events(gsm, "Look around.", [], "")["injected_narratives_post"])

print()
print("### B. first_time_in_location (general_events.yaml:33-45) once-global")
f = [e for e in gen if e["id"] == "first_time_in_location"]
evs = _create_events_from_data(f)
gsm, em = mkinst(evs, loc="elian_study")
L = ["elian_study", "saltstone_bluffs", "crypt_antechamber", "clock_tower", "harbor"]
print("  turns_in_location starts at", gsm.game_state.turns_in_location)
for i, loc in enumerate(L, 1):
    if gsm.get_current_location() != loc:
        gsm.set_current_location(loc)
    print(f"  arrive {loc:20} turns_in_location={gsm.game_state.turns_in_location}")
    r = em.check_and_trigger_events(gsm, "", [], "")   # game.py:285-287 passes ""
    gsm.increment_turns_in_location()
    r2 = em.check_and_trigger_events(gsm, "", [], "")
    fired = "instruct" if r2["modified_prompt_instructions"] else "-"
    print(f"     after +1 turn -> turns={gsm.game_state.turns_in_location} fired={fired} triggered_ids={em.triggered_event_ids}")

print()
print("### C. long_time_in_location (general_events.yaml:48-59) is NOT once")
lt = [e for e in gen if e["id"] == "long_time_in_location"]
evs = _create_events_from_data(lt)
gsm, em = mkinst(evs, loc="room")
for t in range(1, 9):
    gsm.game_state.turns_in_location = t
    r = em.check_and_trigger_events(gsm, "", [], "")
    if r["injected_narratives_pre"]:
        print(f"  turns={t} -> fired")

print()
print("### D. help_command / debug_info reachability inside a turn")
he = [e for e in gen if e["id"] in ("help_command", "debug_info")]
evs = _create_events_from_data(he)
gsm, em = mkinst(evs)
print("  pre-choice call  (game.py:285-287 passes player_input_text=''):")
r = em.check_and_trigger_events(gsm, "", [], "")
print("    override=", r["override_narrative"], " post=", r["injected_narratives_post"])
for s in ["/help", "help", "?", "I need help", "What can I do?", "Check the status of things."]:
    gsm, em = mkinst(_create_events_from_data(he))
    r = em.check_and_trigger_events(gsm, s, [], "")
    print(f"  as free text {s!r:30} override={str(r['override_narrative'])[:26]!r} post={r['injected_narratives_post']}")
for s in ["Ask the librarian for help.", "Where do I go?", "Examine the runes.", "Gather more information."]:
    gsm, em = mkinst(_create_events_from_data(he))
    r = em.check_and_trigger_events(gsm, s, [], "")
    print(f"  as LLM choice label {s!r:40} override={str(r['override_narrative'])[:20]!r} post={r['injected_narratives_post']}")

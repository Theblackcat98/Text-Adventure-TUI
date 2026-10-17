"""CONF: trace the ending route and the added_choices discard in game.py."""
from pathlib import Path
import inspect, re, yaml
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import _create_events_from_data

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
W = LIB / "events/whispers_of_the_salted_crypt_story_events.yaml"
console = Console(quiet=True)
data = yaml.safe_load(W.read_text(encoding="utf-8"))
evs = _create_events_from_data(data)

def mkinv(loc="crypt_antechamber", flags=None, inv=None):
    p = Player(stats={"health": 100, "sanity": 100, "knowledge": 10}, inventory=list(inv or []))
    st = Story(id="whispers_of_the_salted_crypt", title="W", events=evs)
    return GameStateManager(GameState(current_story=st, player=p, current_location=loc,
                                      flags=dict(flags or {})))

print("### Step 1  `present_choices` -> added_choices  (event_manager.py:139-147)")
gsm = mkinv(flags={"tide_is_low": True}, inv=[None, None])
em = EventManager(evs, console)
# rescue_elian needs inventory_has runic_key which we showed can never be true;
# force it so we can inspect the choice plumbing itself.
rescue = [e for e in yaml.safe_load(W.read_text(encoding="utf-8")) if e["id"] == "rescue_elian"][0]
import copy
rescue_wo_inv = copy.deepcopy(rescue)
rescue_wo_inv["trigger"]["conditions"] = [c for c in rescue_wo_inv["trigger"]["conditions"]
                                         if c["type"] != "inventory_has"]
evs2 = _create_events_from_data([e if e["id"] != "rescue_elian" else rescue_wo_inv for e in
                                 yaml.safe_load(W.read_text(encoding="utf-8"))])
p = Player(stats={"health": 100}, inventory=[])
st = Story(id="w", title="W", events=evs2)
gsm = GameStateManager(GameState(current_story=st, player=p,
                                 current_location="crypt_antechamber", flags={"tide_is_low": True}))
em = EventManager(evs2, console)
r = em.check_and_trigger_events(gsm, "Insert key into the bronze door.", [], "")
print("  override_narrative set :", bool(r["override_narrative"]))
print("  added_choices returned  :", r["added_choices"])

print()
print("### Step 2  does game.py ever read added_choices from the POST-choice result?")
src = Path(LIB / "game.py").read_text(encoding="utf-8").splitlines()
for i, l in enumerate(src, 1):
    if "added_choices" in l or "event_results" in l:
        print(f"  game.py:{i:3}  {l}")

print()
print("### Step 3  simulate the exact turn the way game.py:276-348 does it")
# fake a turn: pre-choice check, then post-choice check; a dropped added_choices
LLM_CHOICES = ["Look around.", "Insert key into the bronze door.", "Search the altar.", "Wait."]
pre = em.check_and_trigger_events(gsm, "", [], "")          # game.py:285-287
print("  PRE-CHOICE  added_choices (game.py:294) :", pre["added_choices"])
gsm.game_state.turn_count += 1
post = em.check_and_trigger_events(gsm, "Insert key into the bronze door.", [], "use_key")  # game.py:313-315
print("  POST-CHOICE added_choices (never read)  :", post["added_choices"])
print("  POST-CHOICE override_narrative read at game.py:318 ->", bool(post["override_narrative"]))
print("  => the 2 ending choices are constructed and thrown away")
print("  triggered_event_ids after rescue_elian:", sorted(em.triggered_event_ids))

print()
print("### Step 4  can the player type the action id?  game.py:181-199")
gsm2 = mkinv(flags={}, inv=[])
em2 = EventManager(evs, console)
for typed in ["end_story_success_heroic", "1", "End Story Success Heroic", "trigger:end_story_success_heroic"]:
    u = typed.strip().lower()
    if u.startswith("/"):
        kind = "handle_command -> " + u.split()[0]
    elif u.isdigit() and 1 <= int(u) <= 5:
        kind = "returns LLM choice label or added_choice.action"
    else:
        kind = "prints 'Invalid choice.' (game.py:199) and re-prompts -- NEVER reaches event_manager"
    print(f"  typed {typed!r:42} -> {kind}")

print()
print("### Step 5  `player_action` condition semantics (event_manager.py:200-201)")
for a, b in [("end_story_success_heroic", "end_story_success_heroic"),
             ("End_Story_Success_Heroic", "end_story_success_heroic"),
             ("end_story_success_heroic.", "end_story_success_heroic"),
             ("  end_story_success_heroic  ", "end_story_success_heroic")]:
    print(f"  {a!r:32} == {b!r} -> {a.lower() == b.lower()}")

print()
print("### Step 6  the only live path to the endings: /force_event (game.py:212-213)")
gsm3 = mkinv(flags={}, inv=[])
em3 = EventManager(evs, console)
out = em3.execute_event_actions("end_story_success_heroic", gsm3, [])
print("  override_narrative[:60] :", out["override_narrative"][:60].replace("\n", " "))
print("  flags now               :", gsm3.get_flags())
print("  triggered_event_ids     :", sorted(em3.triggered_event_ids), "<- once:true honoured at event_manager.py:278-279")
out2 = em3.execute_event_actions("end_story_success_heroic", gsm3, [])
print("  second force -> game_ended_success still set, override replaced:", bool(out2["override_narrative"]))
print("  NOTE: execute_event_actions does NOT consult `once` before running, only records it")

print()
print("### Step 7  which execute_event_actions survives?")
import text_adventure_tui_lib.event_manager as EM
src2 = inspect.getsource(EM)
print("  'def execute_event_actions' occurrences:", src2.count("def execute_event_actions"))
print("  surviving definition starts at line:",
      inspect.getsourcelines(EM.EventManager.execute_event_actions)[1])
print("  surviving definition has docstring:", EM.EventManager.execute_event_actions.__doc__)
print("  surviving definition prints the DEBUG 'not found' banner:",
      "not found for force execution" in inspect.getsource(EM.EventManager.execute_event_actions))

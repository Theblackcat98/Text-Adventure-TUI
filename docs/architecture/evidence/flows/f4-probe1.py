"""FLOW-4 probes: one YAML event -> state mutations. Run from repo root with PYTHONPATH=repo."""
import sys, yaml
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
sys.path.insert(0, str(REPO))
from rich.console import Console
from text_adventure_tui_lib.yaml_loader import _load_yaml, _create_events_from_data
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager

story_events = REPO / "text_adventure_tui_lib/events/whispers_of_the_salted_crypt_story_events.yaml"
general_events = REPO / "text_adventure_tui_lib/events/general_events.yaml"

print("=" * 70)
print("F4-P1: YAML bytes -> dict -> Event  (hop 1)")
print("=" * 70)
raw_bytes = story_events.read_bytes()
print("first 60 bytes:", raw_bytes[:60])
raw_dict_list = yaml.safe_load(raw_bytes)
print("top-level type:", type(raw_dict_list).__name__, "| len:", len(raw_dict_list))
file_pos = next(i for i, d in enumerate(raw_dict_list) if d.get("id") == "find_elians_journal")
print("find_elians_journal position within its own file:", file_pos)
print("raw keys in file order:", list(raw_dict_list[file_pos].keys()))

all_events = []
for f in (general_events, story_events):
    d = _load_yaml(f)
    if d:
        all_events.extend(d)
print("all_events len (general 6 + story 10):", len(all_events))

events = _create_events_from_data(all_events)
fe = next(e for e in events if e.id == "find_elians_journal")
print("Event dataclass fields:")
for k, v in vars(fe).items():
    print("  ", k, "=", repr(v)[:80])

# unknown keys silently dropped
synth = [{"id": "x", "name": "X", "extra_key": "LOST", "priority": 5}]
ev = _create_events_from_data(synth)[0]
print("synthetic event with extra_key/priority -> vars:", vars(ev))

# null trap: 'trigger:' with no value
nulltrap = yaml.safe_load("- id: n\n  trigger:\n  actions:\n")
print("null-trap parse:", nulltrap)
ev2 = _create_events_from_data(nulltrap)[0]
print("null-trap Event: trigger =", repr(ev2.trigger), "| actions =", repr(ev2.actions))

print()
print("=" * 70)
print("F4-P2: Event list -> EventManager dict (hop 2: insertion position)")
print("=" * 70)
mgr = EventManager(events, Console())
order = list(mgr.events.keys())
print("dict order:", order)
print("position of find_elians_journal:", order.index("find_elians_journal"))

print()
print("=" * 70)
print("F4-P3: trigger evaluation, condition by condition (hop 3)")
print("=" * 70)
gsm = GameStateManager(GameState(current_story=Story(id="w", title="W"), player=Player()))
gsm.set_current_location("elian_study")  # story_start already ran (change_location elian_study)
gsm.set_flag("knows_elian_is_missing")
print("state before: location=%r flags=%r turn_count=%r turns_in_location=%r" % (
    gsm.get_current_location(), gsm.get_flags(), gsm.game_state.turn_count, gsm.game_state.turns_in_location))

trig = fe.trigger
print("trigger config:", trig)
conds = trig["conditions"]
for i, c in enumerate(conds):
    ct, cv = c.get("type"), c.get("value")
    if ct == "location":
        met = gsm.get_current_location() == cv
        print(f"cond{i} location: read get_current_location()={gsm.get_current_location()!r} == {cv!r} -> {met}")
    elif ct == "player_action_keyword":
        kws = c.get("keywords", [])
        for inp in ("", "search desk", "I search the desk", "SEARCH DESK", "search the desk"):
            m = any(str(k).lower() in inp.lower() for k in kws) if inp else False
            print(f"cond{i} player_action_keyword input={inp!r} -> met={m}")
    elif ct == "flag_not_set":
        met = not gsm.get_flags().get(cv, False)
        print(f"cond{i} flag_not_set: read get_flags()={gsm.get_flags()!r}.get({cv!r}, False) -> met={met}")

for inp in ("", "search desk", "I search the desk", "search the desk"):
    print(f"engine _evaluate_trigger(input={inp!r}) -> {mgr._evaluate_trigger(trig, gsm, inp, '')}")

print("empty conditions -> engine returns:", mgr._evaluate_trigger({"conditions": [], "mode": "AND"}, gsm, "x", ""))
print("unknown condition type under AND ->", mgr._evaluate_trigger({"conditions": [{"type": "nope"}], "mode": "AND"}, gsm, "", ""))

print()
print("=" * 70)
print("F4-P4: the firing: actions, results, once-marking (hops 4-5)")
print("=" * 70)
llm_instructions = []  # game.py:284-equivalent, one per turn
print("-- pre-choice pass, input='' (game.py:285-287) --")
res_pre = mgr.check_and_trigger_events(gsm, "", llm_instructions)
print("fired? override=%r" % (res_pre["override_narrative"],))
print("llm_instructions after pre-pass:", llm_instructions)

print("-- post-choice pass, input='search desk' (game.py:313-315) --")
res_post = mgr.check_and_trigger_events(gsm, "search desk", llm_instructions, "search")
print("returned keys:", list(res_post.keys()))
print("identity: res_post['modified_prompt_instructions'] is llm_instructions ->",
      res_post["modified_prompt_instructions"] is llm_instructions)
print("override_narrative:", repr(res_post["override_narrative"])[:90])
print("injected pre/post:", res_post["injected_narratives_pre"], res_post["injected_narratives_post"])
print("added_choices:", res_post["added_choices"])
print("STATE AFTER: flags=%r" % gsm.get_flags())
print("STATE AFTER: inventory=%r  (identity: is gsm.game_state.player.inventory -> %s)"
      % (gsm.get_inventory(), gsm.get_inventory() is gsm.game_state.player.inventory))
print("STATE AFTER: location=%r (unchanged: no change_location action)" % gsm.get_current_location())
print("llm_instructions after post-pass (modify_prompt landed here):", llm_instructions)
print("once-marked:", sorted(mgr.triggered_event_ids))
res_again = mgr.check_and_trigger_events(gsm, "search desk", llm_instructions, "search")
print("2nd identical pass override=%r (once-skip at :51-55)" % (res_again["override_narrative"],))

print()
print("=" * 70)
print("F4-P5: exception in action 2 of 4 (hop 7: no transactionality)")
print("=" * 70)
crashy = Event(
    id="crashy", name="C",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "elian_study"}]},
    actions=[
        {"type": "set_flag", "value": "a_ran"},
        {"type": "update_stat", "stat": "health", "change_by": None},  # TypeError
        {"type": "set_flag", "value": "c_never"},
        {"type": "override_narrative", "text": "NEVER SEEN"},
    ],
    options={"once": True},
)
mgr2 = EventManager(events + [crashy], Console())
llm2 = []
try:
    mgr2.check_and_trigger_events(gsm, "search desk", llm2)
except TypeError as e:
    print("exception surfaced out of check_and_trigger_events:", type(e).__name__, "-", e)
print("flags after crash: a_ran=%r c_never=%r" % (
    gsm.get_flags().get("a_ran"), gsm.get_flags().get("c_never")))
print("once marked despite crash (natural path)?", "crashy" in mgr2.triggered_event_ids)
try:
    mgr2.execute_event_actions("crashy", gsm, [])
except TypeError as e:
    print("forced run also crashes:", type(e).__name__)
print("once marked by FORCED path despite crash?", "crashy" in mgr2.triggered_event_ids)

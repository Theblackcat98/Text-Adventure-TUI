"""CONF: prove the `flag_is_set` typo and the `value:` vs `item_id:` add_item bug."""
from pathlib import Path
import yaml
from rich.console import Console

from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import _create_events_from_data

ROOT = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
LIB = ROOT / "text_adventure_tui_lib"
console = Console(quiet=True)

def mk(events, stats=None, inv=None, loc="start", flags=None):
    p = Player(stats=dict(stats or {}), inventory=list(inv or []))
    st = Story(id="t", title="t", events=events)
    gs = GameState(current_story=st, player=p, current_location=loc,
                   flags=dict(flags or {}))
    return GameStateManager(gs), EventManager(events, console)

def line(f, needle):
    for i, l in enumerate(Path(f).read_text(encoding="utf-8").splitlines(), 1):
        if needle in l:
            return i
    return -1

# ---------- PROBE 1: `flag_is_set` typo ----------
print("### PROBE 1  flag_is_set typo  (chapter1_study.yaml:67, chapter2_coast.yaml:10, chapter3_crypt.yaml:12)")
D = LIB / "story_parts/Whispers_of_the_Salted_Crypt"
ch1 = yaml.safe_load((D / "chapter1_study.yaml").read_text(encoding="utf-8"))
find_key = [e for e in ch1 if e["id"] == "find_hidden_key"][0]
print("  condition type used:", [c["type"] for c in find_key["trigger"]["conditions"]])

events = _create_events_from_data(ch1)
gsm, em = mk(events, stats={"health": 100}, inv=["runic_key"], loc="elian_study",
              flags={"knows_about_bluffs": True})
# feed the exact keyword string from chapter1_study.yaml:66-67 would need
em._evaluate_trigger(find_key["trigger"], gsm, "search bookshelf", "")
print("  trigger evaluate -> ", em._evaluate_trigger(find_key["trigger"], gsm, "search bookshelf", ""))
# prove the engine has no `flag_is_set` branch
import inspect
src = inspect.getsource(EventManager._evaluate_trigger)
print("  'flag_is_set' present in _evaluate_trigger source? ", "flag_is_set" in src)
print("  'flag_set'      present in _evaluate_trigger source? ", "flag_set" in src)
print("  direct call with the shipped flag_set spelling:")
good = dict(find_key["trigger"])
good["conditions"] = [dict(c, type="flag_set") if c["type"] == "flag_is_set" else c
                      for c in find_key["trigger"]["conditions"]]
print("    flag_is_set version ->", em._evaluate_trigger(find_key["trigger"], gsm, "search bookshelf", ""))
print("    flag_set    version ->", em._evaluate_trigger(good, gsm, "search bookshelf", ""))
# player_intent path used by chapter1
print("  also via player_intent 'search_bookshelf':",
      em._evaluate_trigger(find_key["trigger"], gsm, "x", "search_bookshelf"))

# ---------- PROBE 2: add_item `value:` key ----------
print()
print("### PROBE 2  add_item writes `value:`, engine reads action.get('item_id')")
E = LIB / "events/whispers_of_the_salted_crypt_story_events.yaml"
data = yaml.safe_load(E.read_text(encoding="utf-8"))
for f, eid in ((E, "find_elians_journal"), (E, "find_hidden_key"),
               (LIB / "events/the_clockwork_heist_story_events.yaml", "steal_temporal_gear")):
    ev = [e for e in data if e["id"] == eid] if "whispers" in E.name else None
    print("  (scanning per file separately)")

def add_item_probe(path, event_id, inv_before, location, flags, keyword):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ev = [e for e in data if e["id"] == event_id][0]
    add_act = [a for a in ev["actions"] if a["type"] == "add_item"][0]
    ln = line(path, f"value: \"{add_act['value']}\"")
    events = _create_events_from_data(data)
    gsm, em = mk(events, stats={"health": 100}, inv=inv_before, loc=location, flags=flags)
    res = em.check_and_trigger_events(gsm, keyword, [], "")
    print(f"  {Path(path).name}:{ln}  {event_id:24} add_item keys={sorted(add_act)}")
    print(f"      inventory after trigger = {gsm.get_inventory()!r}")
    return gsm

W = LIB / "events/whispers_of_the_salted_crypt_story_events.yaml"
C = LIB / "events/the_clockwork_heist_story_events.yaml"
g1 = add_item_probe(W, "find_elians_journal", [], "elian_study", {}, "search desk")
g2 = add_item_probe(W, "find_hidden_key", [], "elian_study", {"knows_about_bluffs": True},
                    "search bookshelf")
g3 = add_item_probe(C, "steal_temporal_gear", [], "chronos_exhibition_hall",
                    {"inside_museum": True, "security_disabled": True}, "take gear")

# now show downstream inventory_has never fires
print()
print("### PROBE 2b  downstream `inventory_has` conditions")
for path, eid, kw, need in ((W, "read_journal_clue", "read journal", {}),
                            (W, "rescue_elian", "use key", {}),
                            (C, "disable_security_lockpicks", "use lockpicks", {})):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ev = [e for e in data if e["id"] == eid][0]
    has = [c for c in ev["trigger"]["conditions"] if c["type"] == "inventory_has"][0]
    ln = line(path, f'value: "{has["value"]}"')
    evs = _create_events_from_data(data)
    gsm, em = mk(evs, stats={"health": 100}, inv=[None, None], loc="start", flags=dict(need))
    before = em._evaluate_trigger(ev["trigger"], gsm, kw, "")
    print(f"  {Path(path).name}:{ln}  {eid:26} inventory_has value={has['value']!r}")
    print(f"      with inventory==[None, None]: trigger -> {before}")

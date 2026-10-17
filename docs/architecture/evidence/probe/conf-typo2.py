from pathlib import Path
import yaml, copy
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import _create_events_from_data

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
D = LIB / "story_parts/Whispers_of_the_Salted_Crypt"
console = Console(quiet=True)

def mk(events, stats, inv, loc, flags):
    p = Player(stats=dict(stats), inventory=list(inv))
    st = Story(id="t", title="t", events=events)
    return GameStateManager(GameState(current_story=st, player=p,
                                       current_location=loc, flags=dict(flags)))

def nlines(path, needle, ctx=None, after=0):
    """Return 1-based line numbers where `needle` occurs after line `after`."""
    ls = Path(path).read_text(encoding="utf-8").splitlines()
    out = []
    for i, l in enumerate(ls, 1):
        if i <= after:
            continue
        if needle in l:
            out.append(i)
            if ctx:
                for j in range(i, min(i + ctx, len(ls) + 1)):
                    pass
            if len(out) == 1 and not ctx:
                break
    return out

print("### PROBE 1 (redone) flag_is_set vs flag_set, same conditions otherwise")
ch1 = yaml.safe_load((D / "chapter1_study.yaml").read_text(encoding="utf-8"))
fk = [e for e in ch1 if e["id"] == "find_hidden_key"][0]
evs = _create_events_from_data(ch1)
gsm = mk(evs, {"health": 100}, ["runic_key"], "elian_study", {"knows_about_bluffs": True})
em = EventManager(evs, console)
shipped = fk["trigger"]
fixed = copy.deepcopy(shipped)
for c in fixed["conditions"]:
    if c["type"] == "flag_is_set":
        c["type"] = "flag_set"
print("  conditions (shipped):", [(c['type'], c.get('value')) for c in shipped['conditions']])
print("  conditions (fixed)  :", [(c['type'], c.get('value')) for c in fixed['conditions']])
print("  shipped trigger, input='Search the bookshelf.', intent='search_bookshelf' ->",
      em._evaluate_trigger(shipped, gsm, "Search the bookshelf.", "search_bookshelf"))
print("  fixed   trigger, same input                                        ->",
      em._evaluate_trigger(fixed, gsm, "Search the bookshelf.", "search_bookshelf"))
# show the typo is a no-op False even when the flag IS set
only = {"mode": "AND", "conditions": [dict(c) for c in shipped["conditions"] if c["type"] == "flag_is_set"]}
only2 = {"mode": "AND", "conditions": [dict(c) for c in fixed["conditions"] if c["type"] == "flag_set"]}
print("  isolated flag_is_set(knows_about_bluffs) with flag True ->", em._evaluate_trigger(only, gsm, "", ""))
print("  isolated flag_set(knows_about_bluffs)    with flag True ->", em._evaluate_trigger(only2, gsm, "", ""))

print()
print("### exact line numbers of every flag_is_set in the repo")
import subprocess
print(subprocess.run(["grep", "-rn", "flag_is_set", str(LIB.parent)], capture_output=True, text=True).stdout)

print("### exact line numbers of every add_item / inventory_has / remove_item in shipped YAML")
for f in (LIB / "events/whispers_of_the_salted_crypt_story_events.yaml",
          LIB / "events/the_clockwork_heist_story_events.yaml",
          LIB / "events/general_events.yaml"):
    print("--", f.name)
    print(subprocess.run(["grep", "-nE", r"type: (add_item|inventory_has|inventory_not_has|remove_item|player_action|present_choices|add_choice|end_game|update_stat)", str(f)], capture_output=True, text=True).stdout)

print("### all condition types + all action types used anywhere in the YAML")
import collections
ct, at = collections.Counter(), collections.Counter()
for f in list((LIB / "events").glob("*.yaml")) + list(D.glob("*.yaml")):
    for e in yaml.safe_load(f.read_text(encoding="utf-8")):
        for c in (e.get("trigger") or {}).get("conditions", []):
            ct[c.get("type")] += 1
        for a in e.get("actions", []):
            at[a.get("type")] += 1
print("  condition types:", dict(ct))
print("  action types   :", dict(at))

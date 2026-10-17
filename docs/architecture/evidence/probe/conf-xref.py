"""CONF: build event cross-reference tables from the shipped story YAML."""
from pathlib import Path
import yaml

ROOT = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
LIB = ROOT / "text_adventure_tui_lib"

STORIES = {
    "whispers": LIB / "events/whispers_of_the_salted_crypt_story_events.yaml",
    "clockwork": LIB / "events/the_clockwork_heist_story_events.yaml",
}

for label, path in STORIES.items():
    print("=" * 100)
    print(f"STORY {label}  <- {path.relative_to(ROOT)}")
    print("=" * 100)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    set_flags, tested_flags = set(), set()
    for ev in data:
        once = (ev.get("options") or {}).get("once", False)
        cond_types, act_types = [], []
        for c in (ev.get("trigger") or {}).get("conditions", []):
            t = c.get("type")
            cond_types.append(f"{t}={c.get('value') or c.get('keywords')}")
            if t in ("flag_set", "flag_not_set"):
                tested_flags.add(c["value"])
            if t == "inventory_has":
                tested_flags.add("ITEM:" + str(c.get("value")))
        for a in ev.get("actions", []):
            t = a.get("type")
            act_types.append(f"{t}({a.get('value') or a.get('instruction','')[:24]})")
            if t == "set_flag":
                set_flags.add(a.get("value"))
            if t in ("add_item", "remove_item"):
                set_flags.add("ITEM:" + str(a.get("value") or a.get("item_id")))
        print(f"{ev['id']:32} once={str(once):5} mode={(ev.get('trigger') or {}).get('mode')}")
        print(f"    TRIG : {cond_types}")
        print(f"    ACT  : {act_types}")
    print(f"\n  FLAGS SET       : {sorted(x for x in set_flags if not x.startswith('ITEM:'))}")
    print(f"  FLAGS TESTED    : {sorted(x for x in tested_flags if not x.startswith('ITEM:'))}")
    print(f"  SET-never-TESTED: {sorted(x for x in set_flags - tested_flags if not x.startswith('ITEM:'))}")
    print(f"  TESTED-never-SET: {sorted(x for x in tested_flags - set_flags if not x.startswith('ITEM:'))}")
    print(f"  ITEMS written   : {sorted(x for x in set_flags if x.startswith('ITEM:'))}")
    print(f"  ITEMS tested    : {sorted(x for x in tested_flags if x.startswith('ITEM:'))}")
    print()

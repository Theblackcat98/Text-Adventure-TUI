from pathlib import Path
import yaml, difflib

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
D = LIB / "story_parts/Whispers_of_the_Salted_Crypt"
SHIPPED = LIB / "events/whispers_of_the_salted_crypt_story_events.yaml"
LEGACY = sorted(D.glob("*.yaml"))

def index(paths):
    ev = {}
    for p in paths:
        for e in yaml.safe_load(Path(p).read_text(encoding="utf-8")):
            eid = e["id"]
            ev.setdefault(eid, []).append((Path(p).name, e))
    return ev

a = index([SHIPPED])
b = index(LEGACY)
print("shipped ids :", sorted(a))
print("legacy  ids :", sorted(b))
print("shared      :", sorted(set(a) & set(b)))
print("shipped-only:", sorted(set(a) - set(b)))
print("legacy-only :", sorted(set(b) - set(a)))
print()

for eid in sorted(set(a) & set(b)):
    (_, s), (_, l) = a[eid][0], b[eid][0]
    def cond_types(e): return [c.get("type") for c in (e.get("trigger") or {}).get("conditions", [])]
    def act_types(e):  return [x.get("type") for x in e.get("actions", [])]
    once_s = (s.get("options") or {}).get("once")
    once_l = (l.get("options") or {}).get("once")
    diffs = []
    if cond_types(s) != cond_types(l): diffs.append(f"COND  {cond_types(s)}  vs  {cond_types(l)}")
    if act_types(s)  != act_types(l):  diffs.append(f"ACT   {act_types(s)}  vs  {act_types(l)}")
    if once_s != once_l: diffs.append(f"ONCE  {once_s} vs {once_l}")
    # text comparison
    if s.get("name") != l.get("name"): diffs.append(f"NAME  {s.get('name')!r} vs {l.get('name')!r}")
    print(f"--- {eid}   {'IDENTICAL SHAPE' if not diffs else 'DIFFERS'}")
    for d in diffs: print("      ", d)

print()
print("### flags / locations / items per copy")
def vocab(ev):
    flags_s, flags_t, locs_s, locs_t, items_s, items_t = set(), set(), set(), set(), set(), set()
    for eid, entries in ev.items():
        for fn, e in entries:
            for c in (e.get("trigger") or {}).get("conditions", []):
                if c.get("type") in ("flag_set", "flag_not_set"): flags_t.add(c["value"])
                if c.get("type") == "location": locs_t.add(c["value"])
                if c.get("type") == "inventory_has": items_t.add(c.get("value"))
            for x in e.get("actions", []):
                if x.get("type") == "set_flag": flags_s.add(x["value"])
                if x.get("type") == "change_location": locs_s.add(x["value"])
                if x.get("type") in ("add_item", "remove_item"): items_s.add(x.get("value") or x.get("item_id"))
    return flags_s, flags_t, locs_s, locs_t, items_s, items_t
fs_s, ft_s, ls_s, lt_s, is_s, it_s = vocab(a)
fs_l, ft_l, ls_l, lt_l, is_l, it_l = vocab(b)
for name, (s, l) in {"flags set": (fs_s, fs_l), "flags tested": (ft_s, ft_l),
                     "locations set": (ls_s, ls_l), "locations tested": (lt_s, lt_l),
                     "items written": (is_s, is_l), "items tested": (it_s, it_l)}.items():
    print(f"  {name:16} shipped={sorted(s)}")
    print(f"  {'':16} legacy ={sorted(l)}")
    if s != l: print(f"  {'':16} DIFF: only-shipped={sorted(s-l)} only-legacy={sorted(l-s)}")

print()
print("### verbatim narrative diff for the 5 shared ids")
for eid in sorted(set(a) & set(b)):
    (_, s), (_, l) = a[eid][0], b[eid][0]
    st = "\n".join(str(x.get("text", "")) for x in s.get("actions", []) if x.get("type") in ("override_narrative", "modify_prompt", "inject_narrative"))
    lt_ = "\n".join(str(x.get("text", "")) for x in l.get("actions", []) if x.get("type") in ("override_narrative", "modify_prompt", "inject_narrative"))
    same = st == lt_
    print(f"  {eid:28} prose identical: {same}")
    if not same:
        for line in difflib.unified_diff(st.splitlines(), lt_.splitlines(), "shipped", "legacy", lineterm="", n=0):
            print("      " + line)

print()
print("### arc: is the legacy dir referenced anywhere?")
import subprocess
print(subprocess.run(["grep","-rn","Whispers_of_the_Salted_Crypt",
                      str(LIB.parent), "--include=*.py","--include=*.yaml","--include=*.txt","--include=*.md","--include=*.in","--include=*.cfg","--include=*.toml"],
                     capture_output=True, text=True).stdout or "(no matches)")

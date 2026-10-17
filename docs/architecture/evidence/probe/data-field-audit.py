"""Probe DATA-8: per-field read/write audit using AST + runtime instrumentation."""
import ast, pathlib, sys
from collections import defaultdict

ROOT = pathlib.Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
FIELDS = {
    "Player": ["stats", "inventory"],
    "Event": ["id", "name", "trigger", "actions", "options"],
    "Story": ["id", "title", "events", "starting_location", "initial_story_part",
              "total_turns_estimate", "description", "checkpoints", "tags",
              "difficulty", "content_warnings", "author", "version"],
    "GameState": ["current_story", "player", "flags", "turn_count",
                  "current_location", "turns_in_location"],
}
ALIAS = {
    # local variable names that hold each dataclass instance
    "GameState": {"game_state", "gs", "gsm.game_state"},
    "Player": {"player"},
    "Story": {"story", "story2", "selected_story", "story_arc_data"},
    "Event": {"event", "ev"},
}

reads = defaultdict(list)
writes = defaultdict(list)
kwarg_ctor = defaultdict(list)
subscript_writes = defaultdict(list)

for path in sorted(ROOT.rglob("*.py")):
    rel = path.relative_to(ROOT)
    if any(p in str(rel) for p in ("site-packages", "dist/", ".temp", "build/")):
        continue
    tree = ast.parse(path.read_text(), filename=str(rel))
    for node in ast.walk(tree):
        # attribute store/load on <name>.<field>
        if isinstance(node, ast.Attribute):
            base = None
            if isinstance(node.value, ast.Name):
                base = node.value.id
            elif isinstance(node.value, ast.Attribute) and node.value.attr == "game_state":
                base = "gsm.game_state"
            if base:
                for cls, names in ALIAS.items():
                    if base in names and node.attr in FIELDS[cls]:
                        key = (cls, node.attr)
                        ctx = ast.get_source_segment(path.read_text(), node) or ""
                        loc = f"{rel}:{node.lineno}"
                        if isinstance(node.ctx, ast.Store):
                            writes[key].append(loc)
                        else:
                            reads[key].append(loc)
            # subscript store/load, e.g. game_state.flags["x"] = ...
            if isinstance(node.ctx, (ast.Store, ast.Load)) and node.attr in (
                    "flags", "stats", "inventory"):
                src = ast.get_source_segment(path.read_text(), node) or ""
                if isinstance(node.ctx, ast.Store):
                    subscript_writes[(node.attr, src)].append(f"{rel}:{node.lineno}")
        if isinstance(node, ast.Subscript):
            seg = ast.get_source_segment(path.read_text(), node) or ""
            if isinstance(node.ctx, ast.Store) and (
                "flags" in seg or "inventory" in seg or "stats" in seg):
                subscript_writes[("SubscriptStore", seg)].append(
                    f"{rel}:{node.lineno}")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else None)


            if name in ("GameState", "Story", "Event", "Player"):
                for kw in node.keywords:
                    if kw.arg in FIELDS.get(name, []):
                        kwarg_ctor[(name, kw.arg)].append(f"{rel}:{kw.lineno}")

print("=== keyword-argument construction (positional or keyword) ===")
for k in sorted(kwarg_ctor, key=str):
    print(f"  {k[0]}.{k[1]:20} <- {sorted(set(kwarg_ctor[k]))}")

print("\n=== attribute reads ===")
for k in sorted(reads, key=str):
    print(f"  {k[0]}.{k[1]:20} {sorted(set(reads[k]))}")

print("\n=== attribute writes ===")
for k in sorted(writes, key=str):
    print(f"  {k[0]}.{k[1]:20} {sorted(set(writes[k]))}")

print("\n=== subscript stores (dict/list item assignment) ===")
for k in sorted(subscript_writes, key=str):
    print(f"  {k[0]:14} {k[1]:45} {sorted(set(subscript_writes[k]))}")

print("\n=== fields declared but NEVER read anywhere in the repo ===")
allloc = set()
for d in (reads, writes, kwarg_ctor):
    for k, v in d.items():
        allloc.update(v)
for cls, names in FIELDS.items():
    for n in names:
        rr = {l for k, v in reads.items() if k == (cls, n) for l in v}
        rr |= {l for k, v in kwarg_ctor.items() if k == (cls, n) for l in v}
        # o.__dict__ serialization touches every field
        if not rr:
            print(f"  {cls}.{n}: NEVER read outside construction")

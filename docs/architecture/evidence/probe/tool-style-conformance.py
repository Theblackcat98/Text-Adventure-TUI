"""Probe: measure AGENTS.md style conformance (docstrings, type hints, try/except)."""
import ast, pathlib
ROOT = pathlib.Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
LIB = ROOT / "text_adventure_tui_lib"

def func_nodes(tree):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n

print(f"{'file':45s} {'defs':>5s} {'doc':>4s} {'full-annot':>11s} {'params':>7s} {'excepts':>8s} {'bare/Exc':>9s}")
tot = {}
for f in sorted(LIB.glob("*.py")):
    tree = ast.parse(f.read_text())
    defs = list(func_nodes(tree))
    n_defs = len(defs)
    n_doc = sum(1 for d in defs if ast.get_docstring(d))
    # full annotation: every param annotated (self/cls excluded) AND return annotated
    full, nparams = 0, 0
    for d in defs:
        a = d.args
        params = [p for p in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs) if p.arg not in ("self", "cls")]
        if a.vararg: params.append(a.vararg)
        if a.kwarg: params.append(a.kwarg)
        nparams += len(params)
        if params and d.returns is not None and all(p.annotation is not None for p in params):
            full += 1
    excepts = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            excepts.append(n)
    broad = [e for e in excepts if e.type is None or (isinstance(e.type, ast.Name) and e.type.id == "Exception")]
    print(f"{f.relative_to(ROOT)!s:45s} {n_defs:5d} {n_doc:4d} {full:11d} {nparams:7d} {len(excepts):8d} {len(broad):9d}")
    tot[f.name] = (n_defs, n_doc, full, nparams, len(excepts), len(broad))

print()
T = [sum(v[i] for v in tot.values()) for i in range(6)]
print(f"{'TOTAL':45s} {T[0]:5d} {T[1]:4d} {T[2]:11d} {T[3]:7d} {T[4]:8d} {T[5]:9d}")
print()
print(f"docstring coverage      : {T[1]}/{T[0]} functions")
print(f"fully annotated funcs  : {T[2]}/{T[0]} functions; {T[3]} params total")
print(f"except handlers        : {T[4]} total, {T[5]} are `except:` or `except Exception:`")

# module-level docstrings
print()
for f in sorted(LIB.glob("*.py")):
    tree = ast.parse(f.read_text())
    print(f"module docstring {f.relative_to(ROOT)!s:50s} {bool(ast.get_docstring(tree))}")

# Google-style check: presence of Args:/Returns:/Raises: sections
print()
g = 0
for f in sorted(LIB.glob("*.py")):
    for d in func_nodes(ast.parse(f.read_text())):
        ds = ast.get_docstring(d) or ""
        if any(s in ds for s in ("Args:", "Returns:", "Raises:", "Example", "Yields:")):
            g += 1
            print(f"  google-section {f.relative_to(ROOT)}:{d.lineno}")
print(f"docstrings with Google sections: {g}")

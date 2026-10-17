"""Probe: find PEP 585 builtin-generic annotations evaluated at def time."""
import ast, sys, pathlib

root = pathlib.Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
BUILTIN_GENERICS = {"list", "dict", "tuple", "set", "frozenset", "type"}

for f in sorted(root.rglob("*.py")):
    if "__pycache__" in str(f):
        continue
    tree = ast.parse(f.read_text())
    has_future = any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__"
        and any(a.name == "annotations" for a in n.names)
        for n in tree.body
    )
    for node in ast.walk(tree):
        ann = None
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if node.returns is not None:
                ann = node.returns
            a = node.args
            for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
                if arg is a.vararg:
                    ann = a.vararg.annotation
                elif arg is a.kwarg:
                    ann = a.kwarg.annotation
                if ann is None and arg.annotation is not None:
                    ann = arg.annotation
                    loc = (f"{f.relative_to(root)}:{arg.lineno}")
                    if isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name) and ann.value.id in BUILTIN_GENERICS:
                        print(f"PEP585-ANNOTATION {loc}: {ann.value.id}[...]  (future_annotations={has_future})")
            if node.returns is not None and isinstance(node.returns, ast.Subscript) \
               and isinstance(node.returns.value, ast.Name) and node.returns.value.id in BUILTIN_GENERICS:
                print(f"PEP585-RETURN {f.relative_to(root)}:{node.lineno}: {node.returns.value.id}[...]  (future_annotations={has_future})")

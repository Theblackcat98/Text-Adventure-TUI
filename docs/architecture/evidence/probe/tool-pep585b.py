import ast, pathlib
root = pathlib.Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
BG = {"list", "dict", "tuple", "set", "frozenset", "type"}
for f in sorted(root.rglob("*.py")):
    if "__pycache__" in str(f):
        continue
    src = f.read_text()
    tree = ast.parse(src)
    fut = any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in tree.body)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for name, a in [("arg", node.args.args), ("posonly", node.args.posonlyargs), ("kwonly", node.args.kwonlyargs)]:
            for arg in a:
                if arg.annotation is not None:
                    ann = arg.annotation
                    if isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name) and ann.value.id in BG:
                        print(f"{f.relative_to(root)}:{arg.lineno}  {name} '{arg.arg}: {ast.unparse(ann)}'  future_annotations={bool(fut)}")
        if node.returns is not None:
            r = node.returns
            if isinstance(r, ast.Subscript) and isinstance(r.value, ast.Name) and r.value.id in BG:
                print(f"{f.relative_to(root)}:{node.lineno}  return '-> {ast.unparse(r)}'  future_annotations={bool(fut)}")

"""Probe TOOL: what is the SECOND 3.8 blocker after game.py:83's f-string SyntaxError?"""
import sys, types, traceback

REPO = "/home/nick/Documents/Projects/Text-Adventure-TUI"
print("python:", sys.version.split()[0])

src = open(REPO + "/text_adventure_tui_lib/game.py").read()
src = src.replace(
    "f\"\\nImportant context to consider:\\n- {'\\n- '.join(instructions)}\"",
    "'\\nImportant context to consider:\\n- ' + '\\n- '.join(instructions)",
)
try:
    code = compile(src, "game.py(patched)", "exec")
    print("game.py (f-string patched): COMPILES")
except SyntaxError as e:
    print(f"game.py (f-string patched): SyntaxError line {e.lineno}: {e.msg}")
    code = None

if code is not None:
    m = types.ModuleType("ollama"); m.Client = object; sys.modules["ollama"] = m
    rich = types.ModuleType("rich"); cm = types.ModuleType("rich.console"); cm.Console = object
    rich.console = cm; sys.modules["rich"] = rich; sys.modules["rich.console"] = cm
    for sub, attr in (("panel","Panel"),("prompt","Prompt"),("text","Text"),("theme","Theme")):
        mm = types.ModuleType("rich."+sub); setattr(mm, attr, object)
        sys.modules["rich."+sub] = mm; setattr(rich, sub, mm)
    pkg = types.ModuleType("text_adventure_tui_lib")
    pkg.__path__ = [REPO + "/text_adventure_tui_lib"]
    sys.modules["text_adventure_tui_lib"] = pkg
    sys.path.insert(0, REPO)
    try:
        exec(code, {"__name__": "text_adventure_tui_lib.gprobe", "__package__": "text_adventure_tui_lib", "__file__": REPO + "/text_adventure_tui_lib/game.py"})
        print("game.py EXEC: OK")
    except TypeError as e:
        print(f"game.py EXEC: TypeError: {e}")
        for fr in traceback.extract_tb(sys.exc_info()[2]):
            print(f"   at {fr.filename}:{fr.lineno}  {fr.line}")

print()
try:
    import text_adventure_tui_lib.event_manager  # noqa
    print("event_manager EXEC: OK")
except TypeError as e:
    print(f"event_manager EXEC: TypeError: {e}")
    for fr in traceback.extract_tb(sys.exc_info()[2]):
        print(f"   at {fr.filename}:{fr.lineno}  {fr.line}")
except Exception as e:
    print(f"event_manager EXEC: {type(e).__name__}: {e}")

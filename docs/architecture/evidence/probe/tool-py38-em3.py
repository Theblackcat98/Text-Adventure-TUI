import sys, types, traceback, importlib
rich = types.ModuleType("rich"); sys.modules["rich"] = rich
rc = types.ModuleType("rich.console"); rc.Console = type("Console", (), {}); sys.modules["rich.console"] = rc
sys.path.insert(0, "/home/nick/Documents/Projects/Text-Adventure-TUI")
try:
    importlib.import_module("text_adventure_tui_lib.event_manager")
    print("OK event_manager imported")
except Exception:
    traceback.print_exc()

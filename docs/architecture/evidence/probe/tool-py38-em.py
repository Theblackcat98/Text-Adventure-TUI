import sys, types, importlib.util, traceback
for n in ["rich", "rich.console"]:
    m = types.ModuleType(n); sys.modules[n] = m
sys.modules["rich"].console = sys.modules["rich.console"]
p = "/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib/event_manager.py"
spec = importlib.util.spec_from_file_location("em38", p)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    print("OK")
except Exception:
    traceback.print_exc()

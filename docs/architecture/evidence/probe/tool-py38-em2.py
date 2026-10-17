import sys, types, importlib.util, traceback
rich = types.ModuleType("rich"); sys.modules["rich"] = rich
rc = types.ModuleType("rich.console")
class Console: pass
rc.Console = Console
sys.modules["rich.console"] = rc
gsm = types.ModuleType("x_gsm")
p = "/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib/event_manager.py"
spec = importlib.util.spec_from_file_location("em38", p)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    print("OK")
except Exception:
    traceback.print_exc()

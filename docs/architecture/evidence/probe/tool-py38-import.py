"""Probe: import the repo modules on Python 3.8 with third-party deps stubbed."""
import sys, types, importlib.util, pathlib, traceback

REPO = "/home/nick/Documents/Projects/Text-Adventure-TUI"

def stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# stub the third-party imports game.py makes
class _C:
    def __getattr__(self, n): return _C()
    def __call__(self, *a, **k): return _C()
rich = stub("rich")
stub("rich.console", Console=_C)
stub("rich.panel", Panel=_C)
stub("rich.prompt", Prompt=_C)
stub("rich.text", Text=_C)
stub("rich.theme", Theme=_C)
stub("ollama", Client=_C)

for mod in ["data_structures", "game_state_manager", "event_manager", "yaml_loader", "story_manager", "game"]:
    path = pathlib.Path(REPO) / "text_adventure_tui_lib" / f"{mod}.py"
    name = f"text_adventure_tui_lib.{mod}"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
        print(f"OK   {mod}")
    except Exception as e:
        print(f"FAIL {mod}: {type(e).__name__}: {e}")
        traceback.print_exc(limit=1)

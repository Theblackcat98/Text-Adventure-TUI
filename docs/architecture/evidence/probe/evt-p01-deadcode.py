"""Probe: which execute_event_actions definition is live in Python?"""
import inspect
from text_adventure_tui_lib.event_manager import EventManager

fn = EventManager.__dict__["execute_event_actions"]
print("module file      :", inspect.getsourcefile(fn))
print("live firstlineno :", fn.__code__.co_firstlineno)
print("live argcount    :", fn.__code__.co_argcount)
print("live consts(str) :", [c for c in fn.__code__.co_consts if isinstance(c, str)][:8])

src = inspect.getsource(fn)
print("has DEBUG print  :", "DEBUG" in src)
print("marks once event :", "triggered_event_ids.add" in src)
print("source shown starts at file line:", inspect.getsourcelines(fn)[1])
print("class-body keys  :", sorted(EventManager.__dict__.keys()))

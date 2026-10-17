"""ENTRY probe 02: does an Ollama connection failure hit UnboundLocalError at game.py:163?"""
import traceback
from pathlib import Path

import text_adventure_tui_lib.game as game
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Player, Story

story = Story(id="probe", title="Probe", events=[])
gsm = GameStateManager(GameState(current_story=story, player=Player()))


class Case:
    def __init__(self, name, chat_impl):
        self.name = name
        self.chat_impl = chat_impl

    def __call__(self, **kwargs):
        return self.chat_impl(**kwargs)


CASES = [
    # A: transport failure -- nothing is assigned to raw_json_str
    Case("A. chat() raises (connection refused / model missing)",
         lambda **k: (_ for _ in ()).throw(ConnectionError("connection refused")),
         ),
    # B: chat() returns a non-JSON body -- raw_json_str IS bound, json.loads fails
    Case("B. chat() returns non-JSON text",
         lambda **k: {"message": {"content": "Sorry, I cannot help."}}),
    # C: choices list has 5 entries -> explicit ValueError at game.py:157, raw_json_str bound
    Case("C. chat() returns JSON with 5 choices",
         lambda **k: {"message": {"content":
             '{"narrative_summary": "n", "choices": ["a","b","c","d","e"]}'}}),
    # D: choices list empty -> explicit ValueError
    Case("D. chat() returns JSON with 0 choices",
         lambda **k: {"message": {"content": '{"narrative_summary": "n", "choices": []}'}}),
]

for case in CASES:
    print("=" * 78)
    print(case.name)
    game.ollama_client = Case.__call__ and type("C", (), {"chat": staticmethod(case)})()
    try:
        out = game.get_llm_options("CURRENT NARRATIVE", gsm)
        print("   RETURNED:", out)
    except Exception as exc:
        tb = traceback.extract_tb(exc.__traceback__)
        last = tb[-1]
        print(f"   RAISED {type(exc).__name__}: {exc}")
        print(f"   innermost frame: {Path(last.filename).name}:{last.lineno} -> {last.line}")
        print(f"   fallback at game.py:165 reached? NO")

print("=" * 78)
print("Is the 'Look around./Check inventory./Wait./Leave.' fallback at game.py:165")
print("reachable by ANY input?  Enumerating every statement that can raise inside the")
print("try block of game.py:139-159 and whether raw_json_str is bound first:")
print("  game.py:140 chat()      -> raises -> raw_json_str UNBOUND -> ULE at 163")
print("  game.py:146 [..] lookup -> raises -> raw_json_str UNBOUND -> ULE at 163")
print("  game.py:149 .replace    -> raises -> raw_json_str UNBOUND -> ULE at 163")
print("  game.py:151 json.loads  -> raises -> raw_json_str BOUND   -> fallback works")
print("  game.py:156-157 ValueErr-> explicit                    -> fallback works")

"""ENTRY probe 07: a turn ended via EVENT_TRIGGERED (added choice 'trigger:ev')."""
import json
import text_adventure_tui_lib.game as game
from text_adventure_tui_lib.data_structures import Event, Player, Story

CALLS = []


class Stop(Exception):
    pass


class FakeClient:
    def chat(self, model=None, messages=None, options=None, format=None):
        t = (options or {}).get("temperature")
        CALLS.append({0.7: "options", 0.2: "intent", 0.5: "continuation"}[t])
        if t == 0.7:
            return {"message": {"content": json.dumps(
                {"narrative_summary": "<<SUM>>",
                 "choices": ["A.", "B.", "C.", "D."]})}}
        if t == 0.2:
            return {"message": {"content": "intent_x"}}
        return {"message": {"content": "<<CONT>>"}}


class FakePrompt:
    queue = ["5", "5", "1"]  # pick the added choice (entry 5) twice, then a normal one  # pick the added choice twice, then a normal one

    @staticmethod
    def ask(text=None, **kw):
        if FakePrompt.queue:
            return FakePrompt.queue.pop(0)
        raise Stop()


game.ollama_client = FakeClient()
game.Prompt = FakePrompt
game.input = lambda *a: ""
game.display_story = lambda t: None
game.console = type("C", (), {"print": staticmethod(lambda *a, **k: None),
                              "rule": staticmethod(lambda *a, **k: None)})()

EV = Event(id="trig_ev", name="T",
           trigger={"mode": "AND",
                    "conditions": [{"type": "location", "value": "room"}]},
           actions=[{"type": "add_choice", "label": "Take shortcut.",
                     "action": "trigger:trig_ev"},
                    {"type": "modify_prompt", "instruction": "<<TRIG INSTR>>"},
                    {"type": "override_narrative", "text": "<<TRIG OVERRIDE>>"}],
           options={"once": False})
STORY = Story(id="probe", title="P", events=[EV], checkpoints=[], starting_location="room")
game.load_story_and_player = lambda n, p: (STORY, Player(stats={"health": 100}, inventory=[]))

try:
    game.game_loop("probe")
except Stop:
    pass
print("LLM call sequence across 3 turns:")
print(" ", CALLS)
print("-> an EVENT_TRIGGERED turn makes exactly 1 LLM call (options only);")
print("   get_player_intent is never reached (continue at game.py:306 precedes game.py:312)")

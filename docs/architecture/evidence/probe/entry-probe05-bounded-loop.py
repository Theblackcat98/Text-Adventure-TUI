"""ENTRY probe 05: bounded game_loop -- terminates after N choices."""
import json

import text_adventure_tui_lib.game as game
from text_adventure_tui_lib.data_structures import Story, Player, Event

CALLS = []
NARRATIVE_IN = []
CHOICES_MADE = []
PANELS = []


class Stop(Exception):
    pass


class FakeClient:
    def chat(self, model=None, messages=None, options=None, format=None):
        t = (options or {}).get("temperature")
        prompt = messages[0]["content"]
        kind = {0.7: "options(280)", 0.2: "intent(312)", 0.5: "continuation(322)"}[t]
        CALLS.append({"kind": kind,
                      "ctx": "Important context to consider" in prompt})
        if t == 0.7:
            n = sum(1 for c in CALLS if c["kind"] == "options(280)")
            return {"message": {"content": json.dumps(
                {"narrative_summary": f"<<SUMMARY {n}>>",
                 "choices": ["A.", "B."]})}}
        if t == 0.2:
            return {"message": {"content": "intent_a"}}
        return {"message": {"content": "<<CONTINUATION>>"}}


game.ollama_client = FakeClient()

_real_options = game.get_llm_options
_real_choice = game.get_player_choice


def traced_options(cur, gsm):
    NARRATIVE_IN.append(cur)
    return _real_options(cur, gsm)


def traced_choice(choices, added, gsm, em):
    if len(CHOICES_MADE) >= 3:
        raise Stop()
    CHOICES_MADE.append(1)
    return _real_choice(choices, added, gsm, em)


game.get_llm_options = traced_options
game.get_player_choice = traced_choice
game.Prompt = type("P", (), {"ask": staticmethod(lambda t, **k: "1")})
game.console = type("C", (), {"print": staticmethod(lambda *a, **k: None),
                              "rule": staticmethod(lambda *a, **k: None)})()
game.display_story = PANELS.append
game.input = lambda *a: ""
STORY = Story(id="probe", title="Probe", events=[], checkpoints=[])
PLAYER = Player(stats={"health": 100}, inventory=[])
game.load_story_and_player = lambda n, p: (STORY, PLAYER)


def reset():
    CALLS.clear(); NARRATIVE_IN.clear(); CHOICES_MADE.clear(); PANELS.clear()


def run(label):
    try:
        game.game_loop("probe")
    except Stop:
        pass
    print("\n" + "=" * 74)
    print(label)
    print("  LLM calls, in order:")
    for i, c in enumerate(CALLS, 1):
        print(f"    {i:>2}. {c['kind']:<18} 'Important context' in prompt: {c['ctx']}")
    print("  narrative entering get_llm_options (line 280):")
    for i, n in enumerate(NARRATIVE_IN, 1):
        print(f"    iter {i}: {str(n)[:70]!r}")
    print("  display_story panels:")
    for i, t in enumerate(PANELS, 1):
        print(f"    {i:>2}. {str(t)[:70]!r}")


# ---- Path A: no override, plain turns
reset()
run("PATH A -- plain turn, no event override")

# ---- Path B: post-choice event always overrides narrative
OVR = Event(id="ovr", name="ovr",
            trigger={"mode": "AND",
                     "conditions": [{"type": "player_action", "value": "A."}]},
            actions=[{"type": "override_narrative", "text": "<<OVERRIDE>>"},
                     {"type": "modify_prompt", "instruction": "<<EVENT INSTR>>"}],
            options={})
STORY.events = [OVR]
reset()
run("PATH B -- post-choice event overrides narrative every turn")

# ---- Path C: event supplies an added_choice that triggers another event
TRIG = Event(id="trig", name="trig",
             trigger={"mode": "AND",
                      "conditions": [{"type": "location", "value": "probe_room"}]},
             actions=[{"type": "add_choice", "label": "Take shortcut.",
                       "action": "trigger:trig"},
                      {"type": "modify_prompt", "instruction": "<<TRIG INSTR>>"}],
             options={})
STORY.events = [TRIG]
_orig_init = game.GameStateManager.__init__


def patched(self, gs):
    _orig_init(self, gs)
    self.game_state.current_location = "probe_room"


game.GameStateManager.__init__ = patched
reset()
run("PATH C -- added_choice -> EVENT_TRIGGERED -> execute_event_actions -> continue")

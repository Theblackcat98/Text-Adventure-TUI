"""ENTRY probe 04:
 (a) post-choice override path -> how many LLM calls are wasted
 (b) checkpoint turn semantics (increment_turn at game.py:347 happens FIRST)
 (c) checkpoint prompt_injection (game.py:355) -> does it ever reach a prompt?
"""
import pathlib
import text_adventure_tui_lib.game as game
from text_adventure_tui_lib.data_structures import Story, Player, Event, GameState

CALLS = []


class FakeClient:
    def chat(self, model=None, messages=None, options=None, format=None):
        t = (options or {}).get("temperature")
        CALLS.append({0.7: "options", 0.2: "intent", 0.5: "continuation"}[t])
        if t == 0.7:
            return {"message": {"content":
                '{"narrative_summary": "<<SUMMARY>>", "choices": ["Continue on.", "Other."]}'}}
        if t == 0.2:
            return {"message": {"content": "continue"}}
        return {"message": {"content": "<<CONTINUATION>>"}}


game.ollama_client = FakeClient()

EVENT = Event(id="forced_override", name="F",
              trigger={"mode": "AND", "conditions": [{"type": "player_action", "value": "Continue on."}]},
              actions=[{"type": "override_narrative", "text": "<<OVERRIDE FROM EVENT>>"},
                       {"type": "modify_prompt", "instruction": "<<INSTRUCTION FROM EVENT>>"}],
              options={})


class FakePrompt:
    queue = []

    @staticmethod
    def ask(text, **kw):
        return FakePrompt.queue.pop(0) if FakePrompt.queue else "1"


class FakeConsole:
    def print(self, *a, **k):
        pass

    def rule(self, *a, **k):
        pass


game.Prompt = FakePrompt
game.console = FakeConsole()
PANELS = []
game.display_story = PANELS.append
game.input = lambda *a: ""


def run(checkpoints, n_iterations, label):
    CALLS.clear()
    PANELS.clear()
    story = Story(id="probe_story", title="Probe", events=[EVENT], checkpoints=checkpoints)
    player = Player(stats={"health": 100}, inventory=[])
    FakePrompt.queue = ["1"] * n_iterations
    game.load_story_and_player = lambda name, path: (story, player)
    game.game_loop("probe_story")
    print(f"\n--- {label} ---")
    print("   LLM calls:", CALLS)
    print("   panels   :", PANELS)
    return list(CALLS), list(PANELS)


# (a) override path
calls, panels = run(checkpoints=[], n_iterations=3,
                    label="(a) post-choice override_narrative on every turn")
print("   -> per turn: options + intent, and NO continuation (game.py:318-319 wins)")
print("   -> wasted calls per turn on this path: 1 (get_player_intent at game.py:312)")

# (b) checkpoint semantics
run(checkpoints=[{"turn": 2, "prompt_injection": "<<CHECKPOINT INSTRUCTION>>",
                  "force_end_game": False}],
    n_iterations=4,
    label="(b) checkpoint turn=2, prompt_injection only")
print("   -> did <<CHECKPOINT INSTRUCTION>> appear in any LLM prompt? see probes below")

# capture prompts for the checkpoint case
PROMPTS = []


class RecordingClient(FakeClient):
    def chat(self, model=None, messages=None, options=None, format=None):
        PROMPTS.append(((options or {}).get("temperature"), messages[0]["content"]))
        return super().chat(model=model, messages=messages, options=options, format=format)


game.ollama_client = RecordingClient()
PROMPTS.clear()
run(checkpoints=[{"turn": 2, "prompt_injection": "<<CHECKPOINT INSTRUCTION>>",
                  "force_end_game": False}],
    n_iterations=4, label="(b2) same, recording every prompt")
hits = [(t, "<<CHECKPOINT INSTRUCTION>>" in p) for t, p in PROMPTS]
print("   (temperature, instruction present) per LLM call:")
print("  ", hits)
print("   -> instruction appears in any prompt:",
      any(h for _, h in hits))

# (c) force_end_game
calls, panels = run(checkpoints=[{"turn": 3, "force_end_game": True,
                                  "prompt_injection": "<<CP INSTR>>",
                                  "flag_messages": [
                                      {"flag": "won", "message_if_set": "<<YOU WON>>",
                                       "message_if_not_set": "<<YOU LOST>>"}]}],
                    n_iterations=6,
                    label="(c) force_end_game checkpoint at turn 3")
print("   -> loop ended after", len(panels) // 2, "iterations; last panel:", panels[-1])
print("   -> checkpoints declare turn 3, but the loop ended after the 3rd")
print("      increment_turn, i.e. turn_count had already been bumped to 3")
print("      BEFORE the checkpoint was tested (game.py:347 then 351-353).")

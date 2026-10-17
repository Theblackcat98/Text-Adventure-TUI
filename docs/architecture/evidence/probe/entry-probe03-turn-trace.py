"""ENTRY probe 03: one full game_loop run with a fake ollama client.

Records, per LLM round-trip, which prompt was sent (temperature/format identify
the call site), and records the value of `narrative` as it enters get_llm_options
(game.py:280), i.e. the top of each loop iteration.
"""
import builtins
import json

import text_adventure_tui_lib.game as game

CALLS = []           # every ollama round-trip, in order
NARRATIVE_IN = []    # value of `narrative` seen by get_llm_options each iteration


class FakeClient:
    def chat(self, model=None, messages=None, options=None, format=None):
        prompt = messages[0]["content"]
        kind = {
            0.7: "get_llm_options  (game.py:140, temperature 0.7, format=json)",
            0.2: "get_player_intent  (game.py:110, temperature 0.2)",
            0.5: "get_llm_story_continuation (game.py:86, temperature 0.5)",
        }.get((options or {}).get("temperature"), "???")
        CALLS.append({"kind": kind, "prompt": prompt,
                      "format": format, "temperature": (options or {}).get("temperature")})
        n = sum(1 for c in CALLS if c["temperature"] == 0.7)
        if (options or {}).get("temperature") == 0.7:
            choices = {
                1: ["Search the desk.", "Examine the bookshelf.", "Read the notes.", "Wait."],
            }.get(n, ["Search the desk.", "Examine the bookshelf.", "Read the notes.", "Wait."])
            return {"message": {"content": json.dumps(
                {"narrative_summary": f"<<SUMMARY WRITTEN BY LLM, turn {n}>>", "choices": choices})}}
        if (options or {}).get("temperature") == 0.2:
            return {"message": {"content": "search desk"}}
        return {"message": {"content": "<<CONTINUATION WRITTEN BY LLM>>"}}


game.ollama_client = FakeClient()

# --- instrument the loop without changing behaviour -------------------------
_real_options = game.get_llm_options


def traced_options(current_narrative, gsm):
    NARRATIVE_IN.append(current_narrative)
    return _real_options(current_narrative, gsm)


game.get_llm_options = traced_options

# --- fake UI ----------------------------------------------------------------
SCRIPT = ["1", "2", "2", "/save", "1"]     # last entry quits the fake prompt feed
PROMPT_LOG = []
SCREENS = []


class FakePrompt:
    @staticmethod
    def ask(text, **kw):
        value = SCRIPT.pop(0) if SCRIPT else "1"
        PROMPT_LOG.append((text, value))
        return value


class FakeConsole:
    def print(self, *a, **k):
        SCREENS.append(" ".join(str(x) for x in a))

    def rule(self, *a, **k):
        SCREENS.append("RULE " + " ".join(str(x) for x in a))


game.Prompt = FakePrompt
game.console = FakeConsole()
_real_story = game.display_story
STORY_PANELS = []
game.display_story = lambda t: STORY_PANELS.append(t)

INPUTS_SEEN = []
game.input = lambda *a: INPUTS_SEEN.append(a) or ""

import tempfile, os, shutil, json as _json
tmp = tempfile.mkdtemp(prefix="entry-probe03-")
game.SAVE_GAME_PATH = __import__("pathlib").Path(tmp)
_real_save = game.save_game_state


def traced_save(gsm, em):
    _real_save(gsm, em)
    path = sorted(game.SAVE_GAME_PATH.glob("*.json"))[0]
    data = _json.loads(path.read_text())
    print("\nSAVE FILE top-level keys :", sorted(data.keys()))
    print("SAVE FILE game_state keys:", sorted(data["game_state"].keys()))
    print("SAVE FILE event_manager_state:", data["event_manager_state"])
    print("'narrative' in save file? :", "narrative" in data)


game.save_game_state = traced_save

# --- run --------------------------------------------------------------------
print("### running game_loop('whispers_of_the_salted_crypt') ###")
game.game_loop("whispers_of_the_salted_crypt")

print("\n" + "=" * 78)
print("narrative entering get_llm_options, per iteration (game.py:280):")
for i, n in enumerate(NARRATIVE_IN, 1):
    print(f"  iter {i}: {n[:90]!r}")

print("\nStory panels displayed via display_story(), in order:")
for i, t in enumerate(STORY_PANELS, 1):
    print(f"  panel {i}: {t[:90]!r}")

print("\n" + "=" * 78)
print(f"LLM round-trips: {len(CALLS)}")
for i, c in enumerate(CALLS, 1):
    tag = c["kind"]
    has_instr = "Important context to consider" in c["prompt"]
    print(f"  {i:>2}. {tag}  | instructions embedded in prompt: {has_instr}")

print("\nDo any of the choices-prompt calls (temperature 0.7) contain an")
print("'Important context' / instructions block?")
for c in CALLS:
    if c["temperature"] == 0.7:
        print("   ", "Instructions" in c["prompt"],
              "| contains 'Instructions to consider':", "Important context" in c["prompt"],
              "| has a line '- ':", "\n- " in c["prompt"])

shutil.rmtree(tmp, ignore_errors=True)

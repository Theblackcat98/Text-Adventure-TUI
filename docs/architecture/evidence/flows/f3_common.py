"""Shared harness for FLOW-3 probes (one turn of the game loop).

Run probes from the repo root:
  PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI:/tmp/opencode/cdd-text-adventure-tui/flows python <probe>.py

Stubs game.ollama_client with a recording fake so no Ollama server is needed,
and drives the REAL game_loop from the repo (stale site-packages shadow is
defeated by putting the repo first on sys.path).
"""
import builtins
import io
import sys
from collections import deque

REPO = "/home/nick/Documents/Projects/Text-Adventure-TUI"
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from rich.console import Console  # noqa: E402

from text_adventure_tui_lib import game as g  # noqa: E402
from text_adventure_tui_lib.data_structures import Event, Player, Story  # noqa: E402


class OutOfInputs(BaseException):
    """Raised when the scripted choice queue is empty: clean probe stop."""


def classify(prompt: str) -> str:
    """Route a chat() call to which game.py helper sent it (prompt shapes are
    mutually exclusive: game.py:75-81, :102-108, :127-137)."""
    if "narrative_summary" in prompt:
        return "options"
    if "storyteller" in prompt:
        return "continuation"
    if "classify" in prompt:
        return "intent"
    return "unknown"


class FakeOllama:
    """Records every chat() call; canned answers keyed by call kind.

    script maps kind -> list of contents; an item may be a BaseException
    (raised) or a str (returned as response['message']['content']).
    Defaults: options -> 4-choice JSON marked SUMM<n>/OPT<n>X,
    continuation -> CONT<n>, intent -> 'search_desk'.  <n> is 1-based
    per kind.
    """

    def __init__(self, script=None):
        self.calls = []
        self.script = script or {}

    def chat(self, model=None, messages=(), options=None, format=None, **kw):
        prompt = messages[0]["content"]
        kind = classify(prompt)
        n = sum(1 for c in self.calls if c["kind"] == kind)
        self.calls.append(
            {
                "kind": kind,
                "n": n,
                "prompt": prompt,
                "model": model,
                "options": options,
                "format": format,
            }
        )
        lst = self.script.get(kind)
        item = lst[min(n, len(lst) - 1)] if lst else None
        if isinstance(item, BaseException):
            raise item
        if item is None:
            if kind == "options":
                i = n + 1
                item = (
                    '{"narrative_summary": "SUMM%d", "choices": '
                    '["OPT%dA", "OPT%dB", "OPT%dC", "OPT%dD"]}'
                    % (i, i, i, i, i)
                )
            elif kind == "continuation":
                item = "CONT%d" % (n + 1)
            else:
                item = "search_desk"
        return {"message": {"content": item}}


class FakePrompt:
    """Stands in for rich.prompt.Prompt inside game.py (game.py:181)."""

    def __init__(self, inputs):
        self.inputs = deque(inputs)

    def ask(self, *a, **kw):
        if not self.inputs:
            raise OutOfInputs("choice queue empty")
        item = self.inputs.popleft()
        if isinstance(item, BaseException):
            raise item
        return item


class FakeInput:
    """Stands in for the bare builtins.input calls (game.py:343, :376)."""

    def __init__(self, script=()):
        self.inputs = deque(script)

    def __call__(self, *a, **kw):
        if self.inputs:
            item = self.inputs.popleft()
            if isinstance(item, BaseException):
                raise item
            return item
        return ""


def make_story(events, checkpoints=None, starting_location="study"):
    """A Story game_loop can use without touching repo files.

    game.py:264-269 tries to read initial_story_part, gets FileNotFoundError,
    and falls back to narrative = 'The story begins...'.
    """
    return Story(
        id="f3story",
        title="F3 Probe Story",
        events=list(events),
        checkpoints=checkpoints or [],
        starting_location=starting_location,
        initial_story_part="_no_such_intro_file_f3.txt",
    )


def run(
    story,
    choice_inputs,
    chat_script=None,
    input_inputs=(),
    stats=None,
    inventory=None,
    debug=False,
):
    """Drive the real game_loop; returns (fake, captured_output, outcome)."""
    player = Player(
        stats=dict(stats or {"health": 100, "sanity": 100, "knowledge": 10}),
        inventory=list(inventory or []),
    )
    g.load_story_and_player = lambda name, path: (story, player)
    fake = FakeOllama(chat_script)
    g.ollama_client = fake
    g.DEBUG_MODE_ENABLED = debug
    buf = io.StringIO()
    g.console = Console(
        file=buf,
        theme=g.custom_theme,
        width=500,
        soft_wrap=True,
        highlight=False,
        emoji=False,
    )
    g.Prompt = FakePrompt(choice_inputs)
    real_input = builtins.input
    builtins.input = FakeInput(input_inputs)
    outcome = {"return": None, "exception": None}
    try:
        outcome["return"] = g.game_loop("f3story")
    except BaseException as e:  # noqa: BLE001 - probes deliberately catch all
        outcome["exception"] = e
    finally:
        builtins.input = real_input
    return fake, buf.getvalue(), outcome


def kinds(fake):
    return [c["kind"] for c in fake.calls]


def prompts(fake, kind):
    return [c["prompt"] for c in fake.calls if c["kind"] == kind]


def call(fake, kind, n):
    """n is the 0-based index within the kind."""
    return [c for c in fake.calls if c["kind"] == kind][n]


FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(name)
    print(("PASS " if cond else "FAIL ") + name + ("  | " + detail if detail else ""))


def done(probe_name):
    if FAILS:
        print("\n%s: %d FAILED -> %s" % (probe_name, len(FAILS), FAILS))
        sys.exit(1)
    print("\n%s: all checks passed" % probe_name)

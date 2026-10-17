"""ENTRY probe 06 (bounded):
 (a) checkpoint turn semantics + prompt_injection disposal (game.py:284 vs 351-355)
 (b) resumed game: first options prompt context is the placeholder (game.py:251,280)
 (c) /quit reachability + live-vs-dead execute_event_actions (event_manager.py:18 vs 260)
 (d) main_menu dispatch with ZERO discovered stories (game.py:420-422 vs 428-460)
"""
import pathlib
import tempfile

import text_adventure_tui_lib.game as game
import text_adventure_tui_lib.event_manager as em
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

CALLS = []  # (temperature, prompt)


class Stop(Exception):
    pass


class FakeClient:
    def chat(self, model=None, messages=None, options=None, format=None):
        t = (options or {}).get("temperature")
        CALLS.append((t, messages[0]["content"]))
        if t == 0.7:
            return {"message": {"content": '{"narrative_summary": "<<SUMMARY>>", "choices": ["A.", "B.", "C.", "D."]}'}}
        if t == 0.2:
            return {"message": {"content": "intent_a"}}
        return {"message": {"content": "<<CONTINUATION>>"}}


class FakePrompt:
    queue = []

    @staticmethod
    def ask(text=None, **kw):
        if FakePrompt.queue:
            return FakePrompt.queue.pop(0)
        raise Stop()


class FakeConsole:
    def __init__(self):
        self.lines = []

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))

    def rule(self, *a, **k):
        self.lines.append("RULE " + " ".join(str(x) for x in a))


game.ollama_client = FakeClient()
game.Prompt = FakePrompt
game.input = lambda *a: ""
game.display_story = lambda t: None

STORY = Story(id="probe", title="Probe", events=[], checkpoints=[])
PLAYER = Player(stats={"health": 100}, inventory=[])
game.load_story_and_player = lambda n, p: (STORY, PLAYER)


def sit_line(prompt):
    lines = prompt.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("**Current Situation:**"):
            return lines[i + 1]
    return None


print("=" * 78)
print("(a) CHECKPOINTS: turn=0 and turn=1, prompt_injection only")
STORY.checkpoints = [
    {"turn": 0, "prompt_injection": "<<CP-TURN0>>", "force_end_game": False},
    {"turn": 1, "prompt_injection": "<<CP-TURN1>>", "force_end_game": False},
]
CALLS.clear()
FakePrompt.queue = ["1", "1", "1"]
try:
    game.game_loop("probe")
except Stop:
    pass
for i, (t, p) in enumerate(CALLS, 1):
    mark = ""
    if "<<CP-TURN0>>" in p:
        mark = "  <== contains CP-TURN0"
    if "<<CP-TURN1>>" in p:
        mark += "  <== contains CP-TURN1"
    print(f"  call {i:>2} t={t}: {p[:60]!r}{mark}")
n_cp1 = sum(1 for _, p in CALLS if "<<CP-TURN1>>" in p)
print(f"  -> CP-TURN1 appeared in {n_cp1} of {len(CALLS)} LLM prompts")

print("=" * 78)
print("(a2) force_end_game checkpoint at turn 2 -- game_loop returns normally")
STORY.checkpoints = [{"turn": 2, "force_end_game": True,
                      "flag_messages": [{"flag": "won",
                                         "message_if_set": "<<WON>>",
                                         "message_if_not_set": "<<LOST>>"}]}]
CALLS.clear()
returned = None
FakePrompt.queue = ["1", "1", "1"]
try:
    returned = game.game_loop("probe")
    print(f"  game_loop RETURNED {returned!r} (main_menu just re-shows the menu)")
except Stop:
    print("  game_loop did NOT stop at checkpoint (BAD)")
print(f"  LLM calls made before return: {len(CALLS)}")

print("=" * 78)
print("(b) RESUME: saved_state without 'narrative' key (what /save writes)")
CALLS.clear()
saved = {
    "game_state": {
        "flags": {"k": True},
        "turn_count": 5,
        "current_location": "study",
        "turns_in_location": 2,
        "current_story": {"id": "probe"},
        "player": {"inventory": ["SAVED_SWORD"], "stats": {"health": 42}},
    },
    "event_manager_state": {"triggered_event_ids": []},
}
FakePrompt.queue = ["1"]
try:
    game.game_loop("probe", saved)
except Stop:
    pass
t, p = CALLS[0]
print(f"  first options prompt situation line: {sit_line(p)!r}")
print(f"  prompt mentions SAVED_SWORD inventory? {'SAVED_SWORD' in p}")
inv_line = [l for l in p.splitlines() if l.startswith("- Inventory")]
print(f"  inventory line in prompt: {inv_line}")

print("=" * 78)
print("(c) /quit and /force_event liveness")
print(f"  EventManager.execute_event_actions defined at line "
      f"{em.EventManager.execute_event_actions.__code__.co_firstlineno} "
      f"(candidates: 18 dead / 260 live)")
story = Story(id="p2", title="T", events=[
    Event(id="once_ev", name="O", trigger={"mode": "AND", "conditions": []},
          actions=[{"type": "add_item", "item_id": "X"}], options={"once": True}),
])
from text_adventure_tui_lib.game_state_manager import GameStateManager
gsm = GameStateManager(GameState(current_story=story, player=Player()))
evt_mgr = em.EventManager(story.events, FakeConsole())
con = FakeConsole()
game.console = con
game.Prompt = FakePrompt
FakePrompt.queue = ["/quit"]
try:
    game.get_player_choice(["A.", "B."], [], gsm, evt_mgr)
    print("  /quit did NOT raise (BAD)")
except SystemExit as e:
    print(f"  /quit -> SystemExit({e!r}) propagates out of get_player_choice: REACHABLE")
con.lines.clear()
game.handle_command("/force_event no_such_event", gsm, evt_mgr)
out = [l for l in con.lines if "DEBUG" in l or "not found" in l]
print(f"  /force_event no_such_event printed: {out}  (dead def would print DEBUG)")
game.handle_command("/force_event once_ev", gsm, evt_mgr)
print(f"  inventory after /force_event once_ev: {gsm.get_inventory()}")
print(f"  triggered_event_ids after force of once-event: {evt_mgr.triggered_event_ids}")
import tempfile
game.SAVE_GAME_PATH = pathlib.Path(tempfile.mkdtemp(prefix="entry-probe06-saves"))
con.lines.clear()
FakePrompt.queue = ["/QUIT"]  # lowercased at game.py:181 -> "/quit"
try:
    game.get_player_choice(["A.", "B."], [], gsm, evt_mgr)
except SystemExit as e:
    print(f"  '/QUIT' (uppercased) also exits after lowercasing: SystemExit({e!r})")

print("=" * 78)
print("(d) main_menu dispatch with ZERO discovered stories")


class StubSM:
    def __init__(self, stories):
        self.stories = stories

    def discover_stories(self):
        return self.stories


real_client = game.ollama.Client
game.ollama.Client = lambda host=None: object()
for label, seq in [
    ("types '1' (printed as '1. Toggle Debug Output')", ["1", "3"]),
    ("types '2' (printed as '2. Quit')", ["2", "3"]),
    ("types 'x' (non-digit)", ["x", "3"]),
    ("types '9' (out of range)", ["9", "3"]),
]:
    con = FakeConsole()
    game.console = con
    game.StoryManager = lambda sp, ep, _s=None: StubSM([])
    FakePrompt.queue = list(seq)
    game.DEBUG_MODE_ENABLED = False
    try:
        game.main_menu()
        ended = "menu exited via break (choice 3 == len+3)"
    except Stop:
        ended = "input ran out"
    print(f"  {label}:")
    for l in con.lines:
        if l.strip():
            print(f"      | {l[:80]}")
    print(f"      -> {ended}; DEBUG_MODE_ENABLED now {game.DEBUG_MODE_ENABLED}")

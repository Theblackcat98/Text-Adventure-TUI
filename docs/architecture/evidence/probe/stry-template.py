"""STRY probe 4: create a story from the template in a tmp copy, then validate + start it."""
import shutil, tempfile, subprocess, sys
from pathlib import Path
from rich.console import Console

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
tmp = Path(tempfile.mkdtemp(prefix="stry-template-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP, EP = tmp / "story_parts", tmp / "events"
SP.mkdir(); EP.mkdir()
# seed general_events so the tmp copy mirrors the shipped layout
shutil.copy(REPO / "text_adventure_tui_lib/events/general_events.yaml", EP / "general_events.yaml")

from text_adventure_tui_lib.story_manager import StoryManager
m = StoryManager(SP, EP)
m.create_story_template("my_story", "My Amazing Adventure", "Probe Author")

print("\n== files written ==")
for p in sorted(tmp.rglob("*")):
    if p.is_file():
        print("  ", p.relative_to(tmp), p.stat().st_size)

print("\n== arc as dumped ==")
print((SP / "my_story_story_arc.yaml").read_text())
print("== events as dumped ==")
print((EP / "my_story_story_events.yaml").read_text())

print("== validate the fresh template ==")
r = m.validate_story("my_story")
print("  is_valid:", r.is_valid, "errors:", r.errors, "warnings:", r.warnings)

print("== discover_stories sees it? ==")
print("  ", [(s.id, s.title, s.total_turns_estimate, s.author) for s in m.discover_stories()])

print("\n== can it be loaded and started? (mirrors game.py:239-274) ==")
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
console = Console(quiet=True)
story, player = load_story_and_player("my_story", SP)
print("  starting_location:", story.starting_location,
      "| initial_story_part:", story.initial_story_part)
gs = GameState(current_story=story, player=player,
               current_location=story.starting_location)
gsm = GameStateManager(gs)
em = EventManager(story.events, console)
print("  current_location before story_start:", gsm.get_current_location())
print("  turns_in_location before story_start:", gsm.game_state.turns_in_location)
em.execute_event_actions("story_start", gsm, [])
print("  current_location after  story_start:", gsm.get_current_location())
print("  turns_in_location after  story_start:", gsm.game_state.turns_in_location)
intro = SP / story.initial_story_part
print("  intro file exists:", intro.exists(), "| first line:",
      intro.read_text().splitlines()[0] if intro.exists() else None)

print("\n== example_event keyword trigger, verbatim game.py path ==")
ev = em.events["example_event"]
print("  trigger:", ev.trigger)
print("  _evaluate_trigger('', '')      ->", em._evaluate_trigger(ev.trigger, gsm, "", ""))
for probe in ["look around", "LOOK AROUND", "examine the desk", "look", "I examine",
              "Look Around!", "x"]:
    print(f"  _evaluate_trigger({probe!r}) ->", em._evaluate_trigger(ev.trigger, gsm, probe, ""))
print("  NOTE game.py:285-287 calls check_and_trigger_events with player_input_text=''")
print("  -> keyword branch never runs on the pre-choice pass")

print("\n== checkpoint at turn 20 (game.py:350-377) ==")
gsm.game_state.turn_count = 19
gsm.increment_turn()   # -> 20
gsm.increment_turns_in_location()
current_turn = gsm.get_turn_count()
for checkpoint in story.checkpoints:
    print("  checkpoint:", checkpoint.get("turn"), "== current", current_turn,
          "?", checkpoint.get("turn") == current_turn)
    if checkpoint.get("force_end_game"):
        end_message = "The story reaches its conclusion."
        for flag_msg in checkpoint.get("flag_messages", []):
            fn = flag_msg.get("flag")
            print("    flag", fn, "set?", gsm.get_flags().get(fn, False))
            if gsm.get_flags().get(fn, False):
                if flag_msg.get("message_if_set"):
                    end_message = flag_msg["message_if_set"]; break
            else:
                if flag_msg.get("message_if_not_set"):
                    end_message = flag_msg["message_if_not_set"]; break
        print("    >>> PLAYER SEES:", repr(end_message))

print("\n== do any template events ever set flag 'success'? ==")
import yaml
evs = yaml.safe_load((EP / "my_story_story_events.yaml").read_text())
for e in evs:
    for a in e.get("actions", []):
        if a.get("type") in ("set_flag", "clear_flag"):
            print(f"    {e['id']}: {a.get('type')} value={a.get('value')!r}")
print("  set_flag 'success' anywhere in the template:",
      any(a.get("type") == "set_flag" and a.get("value") == "success"
          for e in evs for a in e.get("actions", [])))

print("\n== story_tool.py create/validate against the tmp copy ==")
env = {"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"}
for cmd in (["list"], ["validate"], ["validate", "my_story"], ["info", "my_story"]):
    p = subprocess.run([sys.executable, str(REPO / "story_tool.py"),
                        "--stories-path", str(SP), "--events-path", str(EP), *cmd],
                       capture_output=True, text=True, cwd=str(tmp), env=env)
    print(f"  $ story_tool.py --stories-path <tmp> --events-path <tmp> {' '.join(cmd)}"
          f"  -> exit {p.returncode}")
    print("    " + p.stdout.strip().replace("\n", "\n    "))
    if p.stderr.strip():
        print("    STDERR:", p.stderr.strip()[:400])
print("\ntmpdir:", tmp)

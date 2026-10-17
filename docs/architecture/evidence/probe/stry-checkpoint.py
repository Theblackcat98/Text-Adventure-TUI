"""STRY probe: template checkpoint at turn 20, traced through game.py:350-377 verbatim."""
import io, shutil, tempfile, contextlib
from pathlib import Path
import yaml
from rich.console import Console

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
tmp = Path(tempfile.mkdtemp(prefix="stry-ckpt-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP, EP = tmp/"story_parts", tmp/"events"
SP.mkdir(); EP.mkdir()
shutil.copy(REPO/"text_adventure_tui_lib/events/general_events.yaml", EP/"general_events.yaml")

from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager

m = StoryManager(SP, EP)
m.create_story_template("ckpt_story", "Checkpoint Story")

story, player = load_story_and_player("ckpt_story", SP)
gs = GameState(current_story=story, player=player, current_location=story.starting_location)
gsm = GameStateManager(gs)
em = EventManager(story.events, Console(quiet=True))

print("=== arc checkpoints as loaded ===")
print(yaml.dump(story.checkpoints, sort_keys=False))
print("=== every set_flag action in the template events ===")
for e in story.events:
    for a in e.actions:
        if a.get("type") in ("set_flag", "clear_flag"):
            print(f"   event {e.id}: {a}")
print("   any event sets 'success'? ",
      any(a.get("type") == "set_flag" and a.get("value") == "success"
          for e in story.events for a in e.actions))
print("   flags at game start:", gsm.get_flags())
print("   total_turns_estimate:", story.total_turns_estimate)

print()
print("=== VERBATIM replay of game.py:350-377 at current_turn = 20 ===")
buf = io.StringIO()
console = Console(file=buf, force_terminal=False, width=80)
class FakeInput:
    def __init__(self): self.n = 0
    def __call__(self, prompt=""):
        self.n += 1
        console.print(f"[input() called -> {prompt.strip()}]")
        return ""
fi = FakeInput()
builtins_input = __builtins__['input'] if isinstance(__builtins__, dict) else __builtins__.input
import builtins
old = builtins.input; builtins.input = fi
try:
    for cp in story.checkpoints:
        if cp.get("turn") == 20:
            if cp.get("prompt_injection"):
                print("   prompt_injection appended to llm_instructions:", repr(cp["prompt_injection"]))
            if cp.get("force_end_game"):
                end_message = "The story reaches its conclusion."
                flag_messages = cp.get("flag_messages", [])
                for flag_msg in flag_messages:
                    flag_name = flag_msg.get("flag")
                    if gsm.get_flags().get(flag_name, False):
                        if flag_msg.get("message_if_set"):
                            end_message = flag_msg["message_if_set"]; break
                    else:
                        if flag_msg.get("message_if_not_set"):
                            end_message = flag_msg["message_if_not_set"]; break
                from rich.panel import Panel
                from rich.text import Text
                console.print(Panel(Text(end_message, style="story"), title="Story",
                                     border_style="info", padding=(1, 2)))
                console.print("\n" + "="*50, style="bold magenta")
                console.print("📖 STORY CONCLUDED 📖", style="bold cyan")
                console.print("="*50, style="bold magenta")
                console.print("\nThank you for playing!", style="info")
                builtins.input("\nPress Enter to return to the main menu...")
                print("   >>> game.py:377 `return` taken")
finally:
    builtins.input = old
print()
print("=== EXACT TEXT THE PLAYER SEES ===")
print(buf.getvalue())
print("=== END ===")
print("tmpdir:", tmp)

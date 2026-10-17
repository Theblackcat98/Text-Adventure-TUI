"""STRY-07: what does a template story's player actually SEE at turn 20?

game_loop's checkpoint block (game.py:350-377) is straight-line dict logic with
no LLM call, so we re-execute an exact copy of it against a template story's
real checkpoint data + real GameStateManager.

Also: (b) create_story_template into a NONEXISTENT stories_path (error path)
      (c) discover_stories over a MALFORMED arc file (the bare-print path, :69)
      (d) discover_stories over a missing stories_path entirely
"""
import shutil, sys, io, contextlib
from pathlib import Path

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
sys.path.insert(0, str(REPO))
from text_adventure_tui_lib.story_manager import StoryManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Story, Player

print("(a) turn-20 checkpoint, exact copy of game.py:350-377")
# --- what stry-03 proved the template writes ---
checkpoint = {'turn': 20, 'force_end_game': True,
              'prompt_injection': 'The story reaches its natural conclusion.',
              'flag_messages': [{'flag': 'success',
                                 'message_if_set': 'You have succeeded in your quest!',
                                 'message_if_not_set': 'Your adventure ends, but perhaps not as you hoped.'}]}
# Only flag ever set by template events is looked_around (stry-03 probe, step 9)
story = Story(id="probe_story", title="Probe Story", checkpoints=[checkpoint])
game_state = GameState(current_story=story, player=Player(), flags={'looked_around': True},
                       turn_count=19, current_location="somewhere", turns_in_location=5)
gsm = GameStateManager(game_state)
llm_instructions = []

# ---- begin verbatim copy of game.py:346-377 (display_story -> print) ----
gsm.increment_turn()
gsm.increment_turns_in_location()

current_turn = gsm.get_turn_count()
captured = []
for cp in story.checkpoints:
    if cp.get("turn") == current_turn:
        if cp.get("prompt_injection"):
            llm_instructions.append(cp["prompt_injection"])
        if cp.get("force_end_game"):
            end_message = "The story reaches its conclusion."
            flag_messages = cp.get("flag_messages", [])
            for flag_msg in flag_messages:
                flag_name = flag_msg.get("flag")
                if gsm.get_flags().get(flag_name, False):
                    if flag_msg.get("message_if_set"):
                        end_message = flag_msg["message_if_set"]
                        break
                else:
                    if flag_msg.get("message_if_not_set"):
                        end_message = flag_msg["message_if_not_set"]
                        break
            captured.append(end_message)
            captured.append("== STORY CONCLUDED ==")
            captured.append("Thank you for playing!")
            captured.append("Press Enter to return to the main menu...")
            print("  RETURN (to main_menu) reached:", True)
# ---- end copy ----
print("  turn_count now:", gsm.get_turn_count())
print("  llm_instructions (discarded by the return):", llm_instructions)
print("  PLAYER SEES, in order:")
for c in captured:
    print("    |", c)

print()
print("(b) create_story_template into a nonexistent stories_path:")
TMP = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-missing")
if TMP.exists():
    shutil.rmtree(TMP)
mgr = StoryManager(TMP / "nope", TMP / "nope2")
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        mgr.create_story_template("x", "X")
    print("  no exception; printed:", repr(buf.getvalue()))
except Exception as e:
    print("  raises:", type(e).__name__, "-", e)
print("  (story_tool.py:117-130 wraps create in try/except -> exit 1)")

print()
print("(c) discover_stories over a MALFORMED arc file (bare print at :69):")
TMP2 = Path("/tmp/opencode/cdd-text-adventure-tui/probe/stry-tmp-malformed")
if TMP2.exists():
    shutil.rmtree(TMP2)
(TMP2 / "story_parts").mkdir(parents=True)
(TMP2 / "story_parts" / "bad_story_arc.yaml").write_text("title: [unclosed\n  bad")
(TMP2 / "story_parts" / "good_story_arc.yaml").write_text("title: Good Story\n")
mgr2 = StoryManager(TMP2 / "story_parts", TMP2 / "events")
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    found = mgr2.discover_stories()
print("  discovered ids:", [s.id for s in found])
print("  bare-print output captured:", repr(buf2.getvalue()))

print()
print("(d) discover_stories over a MISSING stories_path:")
mgr3 = StoryManager(Path("/tmp/opencode/definitely_not_here"), Path("/tmp/opencode/also_not"))
buf3 = io.StringIO()
with contextlib.redirect_stdout(buf3):
    found3 = mgr3.discover_stories()
print("  result:", found3, "| printed:", repr(buf3.getvalue()),
      "| (glob over missing dir is silently empty)")

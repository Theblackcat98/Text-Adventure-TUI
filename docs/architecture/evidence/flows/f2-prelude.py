"""FLOW-2 probe: replay game_loop(saved_state=None) steps 2-6 (game.py:252-274)
against the real whispers_of_the_salted_crypt YAML, plus error-path probes.

Run: cd /home/nick/Documents/Projects/Text-Adventure-TUI &&
     PYTHONPATH=/home/nick/Documents/Projects/Text-Adventure-TUI python
     /tmp/opencode/cdd-text-adventure-tui/flows/f2-prelude.py
"""
import locale
from pathlib import Path

from text_adventure_tui_lib import game as game_mod
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

STORY = "whispers_of_the_salted_crypt"

print("imported game module from:", game_mod.__file__)
print("locale.getpreferredencoding(False):", locale.getpreferredencoding(False))

# ---- game.py:234-235 ----
# display_title() is a pure rich banner print; skipped here (no tty value).
stories_path = Path(game_mod.__file__).parent / "story_parts"
print("stories_path anchor:", stories_path)

# ---- STEP 2: load_story_and_player (game.py:254 -> yaml_loader.py:32-93) ----
story, player = load_story_and_player(STORY, stories_path)
print("\n== STEP 2: loader output ==")
print("story.id               :", story.id)
print("story.title            :", story.title)
print("story.starting_location:", story.starting_location)
print("story.initial_story_part:", story.initial_story_part)
print("story.total_turns_estimate:", story.total_turns_estimate)
print("story.difficulty/author/version:", story.difficulty, "/", story.author, "/", story.version)
print("story.tags             :", story.tags)
print("story.content_warnings :", story.content_warnings)
print("story.checkpoints      :", story.checkpoints)
print("story.description[:70] :", repr(story.description[:70]))
print("player.stats           :", player.stats)
print("player.inventory       :", player.inventory)
print("len(story.events)      :", len(story.events))
print("story.events order     :", [e.id for e in story.events])

# EventManager construction (game.py:261 -> event_manager.py:8 dict comprehension)
em = EventManager(story.events, game_mod.console)
print("em.events dict keys    :", list(em.events.keys()))
print("em.triggered_event_ids :", em.triggered_event_ids)
fn = EventManager.execute_event_actions
print("execute_event_actions co_firstlineno:", fn.__code__.co_firstlineno,
      "(260 = live second definition; 18 = dead first)")

# ---- STEP 3: GameState + GameStateManager (game.py:255-260) ----
game_state = GameState(
    current_story=story, player=player, current_location=story.starting_location
)
gsm = GameStateManager(game_state)
print("\n== STEP 3: GameState defaults ==")
print("flags            :", gsm.get_flags())
print("turn_count       :", gsm.get_turn_count())
print("turns_in_location:", game_state.turns_in_location)
print("current_location :", gsm.get_current_location(), "(from story.starting_location)")

# ---- STEP 4: intro read (game.py:263-269) ----
print("\n== STEP 4: intro read ==")
intro_part_path = stories_path / story.initial_story_part
print("intro_part_path   :", intro_part_path)
try:
    with open(intro_part_path, "r") as f:
        narrative_before = f.read()
    print("intro file read OK")
    print("intro text (repr) :", repr(narrative_before))
except FileNotFoundError:
    narrative_before = "The story begins..."
    print("FileNotFoundError -> fallback narrative:", repr(narrative_before))

# ---- STEP 5: execute_event_actions("story_start") (game.py:272-274) ----
print("\n== STEP 5: forced story_start ==")
llm_instructions_discarded = []  # the literal [] at game.py:272
story_start_results = em.execute_event_actions("story_start", gsm, llm_instructions_discarded)
print("result keys       :", sorted(story_start_results.keys()))
print("has 'modified_prompt_instructions' key? ",
      "modified_prompt_instructions" in story_start_results,
      "(4-key _perform_actions shape => no)")
print("override_narrative is not None?", story_start_results.get("override_narrative") is not None)
print("injected_pre/post  :", story_start_results.get("injected_narratives_pre"),
      "/", story_start_results.get("injected_narratives_post"))
print("added_choices      :", story_start_results.get("added_choices"))
print("the passed [] now  :", llm_instructions_discarded,
      "<- modify_prompt appended here; game.py never binds this list")
print("flags after        :", gsm.get_flags())
print("location after     :", gsm.get_current_location())
print("turn_count after   :", gsm.get_turn_count())
print("turns_in_loc after :", game_state.turns_in_location)
print("em.triggered_event_ids after:", em.triggered_event_ids,
      "(story_start has no options.once => not marked)")

# ---- STEP 6: override replaces intro (game.py:273-274) ----
print("\n== STEP 6: override wins ==")
if story_start_results.get("override_narrative"):
    narrative = story_start_results["override_narrative"]
print("narrative == intro file text?          ", narrative == narrative_before)
print("narrative == story_start override text?", narrative == story_start_results["override_narrative"])
print("narrative shown to the player (repr):")
print(repr(narrative))

# ---- STEP 9: what the loop sees next (game.py:276-284) ----
print("\n== STEP 9: end state ==")
print(f"first header would be: console.rule(f\"Turn {gsm.get_turn_count()}\") -> 'Turn 0'")
print("'llm_instructions' does not exist yet: created at game.py:284, inside the")
print("loop, AFTER the get_llm_options call at :280 has already been sent.")

# ---- STEP 7a: unknown event id (live def shape, event_manager.py:268-275) ----
print("\n== STEP 7a: execute_event_actions with an id that does not exist ==")
res = em.execute_event_actions("no_such_event", gsm, [])
print("returns 5-key dict:", sorted(res.keys()))
print("override_narrative:", res.get("override_narrative"))
print("(a story whose YAML lacks story_start reaches this same branch at game.py:272;")
print(" override .get() is falsy -> intro text would survive game.py:273-274)")

# ---- STEP 7b: missing intro file ----
print("\n== STEP 7b: missing intro file ==")
story.initial_story_part = "definitely_not_here.txt"
try:
    with open(stories_path / story.initial_story_part, "r") as f:
        narrative_before = f.read()
    print("unexpectedly exists")
except FileNotFoundError:
    print("FileNotFoundError -> game.py:268-269 sets narrative = 'The story begins...'")
story.initial_story_part = "01_intro.txt"

# ---- STEP 7c: arc file present but empty (yaml_loader.py:42 + :67) ----
print("\n== STEP 7c: empty story arc file ==")
tmp = Path("/tmp/opencode/cdd-text-adventure-tui/flows/f2-emptycase")
(tmp / "story_parts").mkdir(parents=True, exist_ok=True)
arc = tmp / "story_parts" / "f2_empty_story_arc.yaml"
arc.write_text("")
try:
    load_story_and_player("f2_empty", tmp / "story_parts")
except AttributeError as e:
    print(f"AttributeError: {e}  <- story_arc_data is None (yaml.safe_load of empty file)")

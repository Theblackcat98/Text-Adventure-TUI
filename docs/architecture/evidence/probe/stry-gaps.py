"""STRY probe 3: what validate_story does NOT check.

Builds a story in a tmp copy whose events file contains every class of
brokenness the engine cares about, and shows validate_story reports it valid.
"""
import shutil
import tempfile
from pathlib import Path
from text_adventure_tui_lib.story_manager import StoryManager

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
tmp = Path(tempfile.mkdtemp(prefix="stry-gaps-", dir="/tmp/opencode/cdd-text-adventure-tui/probe"))
SP = tmp / "story_parts"
EP = tmp / "events"
SP.mkdir()
EP.mkdir()

(SP / "broken_story_story_arc.yaml").write_text("""
title: Broken Story
starting_location: nowhere_at_all
initial_story_part: does_not_exist.txt
total_turns_estimate: 3
initial_inventory: ["rusty key"]
initial_player_stats: {health: 100}
checkpoints:
  - turn: 2
    force_end_game: true
    flag_messages:
      - flag: never_set_anywhere
        message_if_set: "win"
        message_if_not_set: "lose"
""")
(SP / "does_not_exist.txt").write_text("")  # note: this EXISTS, see below

EP.joinpath("broken_story_story_events.yaml").write_text("""
- id: story_start
  name: Start
  trigger:
    mode: MANUAL
    conditions: [{type: game_start}]
  actions:
    - {type: change_location, value: nowhere_at_all}
    - {type: totally_made_up_action, value: 123}
    - {type: add_item, value: rusty key}
    - {type: update_stat, value: -10}
- id: bad_triggers
  name: Bad triggers
  trigger:
    mode: XOR
    conditions:
      - {type: not_a_real_condition_type, value: q}
      - {type: turn_count_global, operator: '~=', value: 5}
      - {type: stat_check, stat: missing_stat, operator: '>>=', value: 3}
      - {type: location, value: a_location_that_exists_nowhere}
  actions:
    - {type: present_choices, choices: [{label: A, action: no_such_event_id}]}
    - {type: add_choice, label: Go, action: also_missing_event}
- id: dangling_event_ref
  name: References an event that does not exist
  trigger: {mode: AND, conditions: [{type: flag_set, value: never_defined_flag}]}
  actions: [{type: set_flag, value: never_defined_flag}]
""")

m = StoryManager(SP, EP)
r = m.validate_story("broken_story")
print("is_valid:", r.is_valid)
print("errors  :", r.errors)
print("warnings:", r.warnings)

# ---- now prove the engine actually chokes on it
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console

story, player = load_story_and_player("broken_story", SP)
gs = GameState(current_story=story, player=player,
               current_location=story.starting_location)
gsm = GameStateManager(gs)
em = EventManager(story.events, Console(quiet=True))
print("\n-- story_start forced execution --")
print(gsm.get_inventory(), "  <- add_item wrote 'None', not 'rusty key'")
print(gsm.get_stats())
print(gsm.get_current_location())
print("\n-- trigger evaluation with mode XOR / bogus types --")
print("bad_triggers met?", em._evaluate_trigger(
    next(e for e in story.events if e.id == "bad_triggers").trigger,
    gsm, "hello", "explore"))
print("\n-- present_choices action referencing missing event id --")
out = em.execute_event_actions("bad_triggers", gsm, [])
print("added_choices:", out["added_choices"])

print("\n-- checkpoint turn 2, flag never set --")
turn = gsm.get_turn_count()
print("current turn:", turn)

print("\ntmpdir:", tmp)

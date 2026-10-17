"""LOAD-9: YAML null values for optional keys pass straight through the loader
and explode later inside EventManager."""
import tempfile, textwrap, traceback
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Player

root = Path(tempfile.mkdtemp(prefix="loadprobe9-"))
st = root / "story_parts"; ev = root / "events"; st.mkdir(); ev.mkdir()
ev.joinpath("general_events.yaml").write_text("- id: gen\n  name: G\n")
st.joinpath("nulls_story_arc.yaml").write_text('title: "N"\nstarting_location: "start"\n')

CASES = {
    "trigger: (null)": "- id: story_start\n  name: S\n  trigger:\n  actions: []\n",
    "actions: (null)": "- id: story_start\n  name: S\n  trigger: {mode: AND, conditions: []}\n  actions:\n",
    "options: (null)": "- id: story_start\n  name: S\n  trigger: {mode: AND, conditions: []}\n  actions: []\n  options:\n",
}
console = Console(quiet=True)
for label, body in CASES.items():
    ev.joinpath("nulls_story_events.yaml").write_text(body)
    print("=" * 64)
    print("CASE", label)
    story, player = load_story_and_player("nulls", st)
    e = story.events[-1]
    print(f"  loader produced: id={e.id!r} name={e.name!r} trigger={e.trigger!r} "
          f"actions={e.actions!r} options={e.options!r}")
    gsm = GameStateManager(GameState(current_story=story, player=player))
    em = EventManager(story.events, console)
    try:
        em.check_and_trigger_events(gsm, "hello", [])
        print("  EventManager.check_and_trigger_events: OK (no crash)")
    except Exception:
        print(textwrap.indent(traceback.format_exc().strip()[-500:], "    | "))

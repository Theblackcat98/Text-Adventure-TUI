"""Probe DATA-9: is the serialized Story authoritative on resume, or is the
copy on disk?  Simulates: save -> edit story on disk -> resume."""
import json, shutil, tempfile
from pathlib import Path
import sys

sys.path.insert(0, "/home/nick/Documents/Projects/Text-Adventure-TUI")
from text_adventure_tui_lib.data_structures import GameState
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

REAL = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    shutil.copytree(REAL / "story_parts", root / "story_parts")
    shutil.copytree(REAL / "events", root / "events")
    sp = root / "story_parts"

    story, player = load_story_and_player("the_clockwork_heist", sp)
    gs = GameState(current_story=story, player=player, turn_count=5,
                   current_location="vault", turns_in_location=2)
    gsm = GameStateManager(gs)
    gsm.set_flag("has_temporal_gear")

    save_data = {"game_state": gsm.game_state,
                 "event_manager_state": {"triggered_event_ids": []}}
    saved_state = json.loads(json.dumps(save_data, default=lambda o: o.__dict__))

    print("SAVED  story.checkpoints[0].turn =",
          saved_state["game_state"]["current_story"]["checkpoints"][0]["turn"])
    print("SAVED  player.stats['stealth'] =",
          saved_state["game_state"]["player"]["stats"]["stealth"])
    gsm.update_stat("stealth", 99)
    gsm.add_item("lucky_coin")

    # --- now the "resume" path, verbatim from game.py:237-251
    story2, player2 = load_story_and_player("the_clockwork_heist", sp)
    gs2 = GameState(
        current_story=story2, player=player2,
        flags=saved_state["game_state"]["flags"],
        turn_count=saved_state["game_state"]["turn_count"],
        current_location=saved_state["game_state"]["current_location"],
        turns_in_location=saved_state["game_state"]["turns_in_location"],
    )
    print("\nRESUMED story.checkpoints[0].turn =", gs2.current_story.checkpoints[0]["turn"],
          "(from disk, NOT from the save)")
    print("RESUMED player.stats['stealth'] =", gs2.player.stats.get("stealth"),
          "(from YAML arc, NOT from the save)")
    print("RESUMED inventory =", gs2.player.inventory)
    print("RESUMED flags =", gs2.flags, "(this one DOES survive)")

    print("\n=== now edit the story on disk, then resume the same save ===")
    arc = sp / "the_clockwork_heist_story_arc.yaml"
    txt = arc.read_text()
    arc.write_text(txt + "\ncheckpoints:\n  - turn: 99\n    force_end_game: true\n"
                          "    prompt_injection: 'changed on disk'\n"
                          "initial_player_stats:\n  health: 100\n  stealth: 1\n"
                          "  cunning: 70\ninitial_inventory: [lockpicks, smoke_bomb]\n")
    story3, player3 = load_story_and_player("the_clockwork_heist", sp)
    print("reloaded checkpoints:", story3.checkpoints)
    print("-> the save file's story copy is never consulted; the only field of")
    print("   it used at all is ['current_story']['id'] at game.py:451")

    print("\n=== what if the story id no longer exists on disk? ===")
    shutil.rmtree(sp)
    shutil.copytree(REAL / "story_parts", sp)
    (sp / "the_clockwork_heist_story_arc.yaml").unlink()
    try:
        load_story_and_player("the_clockwork_heist", sp)
    except Exception as e:
        print(f"   -> {type(e).__name__}: {e}  (unhandled in game_loop)")

from pathlib import Path
import yaml, copy
from rich.console import Console
from text_adventure_tui_lib.data_structures import Player, Story, GameState
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

LIB = Path("/home/nick/Documents/Projects/Text-Adventure-TUI/text_adventure_tui_lib")
console = Console(quiet=True)

print("### A. end_game overwrites override_narrative (event_manager.py:148-154)")
for f in ("whispers_of_the_salted_crypt_story_events.yaml", "the_clockwork_heist_story_events.yaml"):
    d = yaml.safe_load((LIB / "events" / f).read_text(encoding="utf-8"))
    for e in d:
        if any(a.get("type") == "end_game" for a in e.get("actions", [])):
            eg = [a for a in e["actions"] if a["type"] == "end_game"][0]
            on = [a for a in e["actions"] if a["type"] == "override_narrative"]
            print(f"  {f}:{e['id']}  end_game keys={sorted(eg)}  "
                  f"prose_before_end_game={bool(on)} ({len(on[0].get('text','')) if on else 0} chars) "
                  f"-> override_narrative becomes event_manager.py:151 default")

print()
print("### B. checkpoint turn numbers vs total_turns_estimate")
for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    story, player = load_story_and_player(sid, LIB / "story_parts")
    print(f"  {sid}: total_turns_estimate={story.total_turns_estimate}")
    for cp in story.checkpoints:
        print(f"     turn={cp['turn']:3} force_end_game={cp.get('force_end_game', False)} "
              f"flag_messages={[fm.get('flag') for fm in cp.get('flag_messages', [])]}")
    print(f"     initial_inventory={player.inventory}  initial_stats={player.stats}")

print()
print("### C. is the flag_messages flag ever set?  grep the matching events file")
import subprocess
for sid, flag in (("whispers_of_the_salted_crypt", "elian_is_found"),
                  ("the_clockwork_heist", "has_temporal_gear")):
    out = subprocess.run(["grep", "-n", f'value: "{flag}"',
                          str(LIB / "events" / f"{sid}_story_events.yaml")],
                         capture_output=True, text=True).stdout.strip()
    print(f"  {flag}: {out or 'NOT SET ANYWHERE'}")
    arc = subprocess.run(["grep", "-n", f'flag: "{flag}"',
                          str(LIB / "story_parts" / f"{sid}_story_arc.yaml")],
                         capture_output=True, text=True).stdout.strip()
    print(f"      arc references it at: {arc}")

print()
print("### D. simulate the turn counter exactly as game.py:276-377 runs it")
for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    story, player = load_story_and_player(sid, LIB / "story_parts")
    gs = GameState(current_story=story, player=player, current_location=story.starting_location)
    gsm = GameStateManager(gs)
    em = EventManager(story.events, console)
    fired, forced = [], None
    for turn in range(1, 40):
        # events, no override_narrative, no end_game -> falls through to game.py:347-348
        gsm.increment_turn()
        gsm.increment_turns_in_location()
        ct = gsm.get_turn_count()
        for cp in story.checkpoints:
            if cp.get("turn") == ct:
                if cp.get("prompt_injection"): fired.append((ct, "prompt_injection"))
                if cp.get("force_end_game"):
                    forced = ct
                    msg = "The story reaches its conclusion."
                    for fm in cp.get("flag_messages", []):
                        if gsm.get_flags().get(fm.get("flag"), False):
                            msg = fm.get("message_if_set"); break
                        else:
                            msg = fm.get("message_if_not_set"); break
                    print(f"  {sid}: turn {ct} force_end_game, flags={gsm.get_flags()}")
                    print(f"      end_message = {msg[:90]}...")
        if forced: break
    print(f"  {sid}: checkpoints fired {fired}, forced end at turn {forced}")

print()
print("### E. checkpoint exact-equality: does a checkpoint at turn 15 survive turn 15?")
story, player = load_story_and_player("the_clockwork_heist", LIB / "story_parts")
gs = GameState(current_story=story, player=player, current_location="thieves_den")
gsm = GameStateManager(gs)
for turn in [9, 10, 11, 14, 15, 16]:
    gsm.game_state.turn_count = turn
    hit = [c["turn"] for c in story.checkpoints if c.get("turn") == gsm.get_turn_count()]
    print(f"  turn_count={turn:3} -> checkpoints matched: {hit}")

print()
print("### F. what if the story reaches its ending event first? (game.py:334-344 beats 352)")
story, player = load_story_and_player("whispers_of_the_salted_crypt", LIB / "story_parts")
gs = GameState(current_story=story, player=player, current_location="start")
gsm = GameStateManager(gs)
em = EventManager(story.events, console)
em.execute_event_actions("end_story_success_heroic", gsm, [])
print("  after end_game: game_ended =", gsm.get_flags().get("game_ended"),
      "-> game.py:334 breaks the loop; the turn-25 checkpoint at game.py:352 never runs")

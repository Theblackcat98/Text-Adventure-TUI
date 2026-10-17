"""Probe: (a) bare end_game with no success key, correctly triggered;
(b) exact line numbers + key names of every add_item / update_stat / remove_item
in ALL shipped YAML (events/ + story_parts/, both formats)."""
import io
from pathlib import Path
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import Event, GameState, Player, Story

# (a) bare end_game
story = Story(id="t", title="t")
gs = GameState(current_story=story, player=Player(), flags={}, turn_count=0,
               current_location="start", turns_in_location=0)
gsm = GameStateManager(gs)
trig = {"mode": "AND", "conditions": [{"type": "player_action", "value": "x"}]}
ev = Event(id="bare", name="", trigger=trig,
           actions=[{"type": "end_game"}], options={})
buf = io.StringIO()
em = EventManager([ev], Console(file=buf, width=120, no_color=True))
r = em.check_and_trigger_events(gsm, "x", [], "")
print("bare end_game (no success/message keys):")
print("  override_narrative ->", repr(r["override_narrative"]))
print("  flags ->", {k: v for k, v in gs.flags.items() if k.startswith("game_ended")})

# (b) YAML key-shape audit with line numbers
ROOT = Path("text_adventure_tui_lib")
targets = ("add_item", "remove_item", "update_stat", "present_choices",
           "end_game", "add_choice")
for yml in sorted(ROOT.rglob("*.yaml")):
    if "story_arc" in yml.name:
        continue
    lines = yml.read_text().splitlines()
    hits = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("- type: ") and s[8:].strip() in targets:
            t = s[8:].strip()
            block = []
            j = i + 1
            while j < len(lines):
                l2 = lines[j]
                if l2.startswith("  - ") or (l2 and not l2.startswith(" ")):
                    break
                block.append(l2.strip())
                j += 1
            hits.append((i + 1, t, block[:5]))
            i = j
        else:
            i += 1
    if hits:
        print(f"\n{yml}:")
        for ln, t, block in hits:
            print(f"  L{ln}: {t:16s} {block}")

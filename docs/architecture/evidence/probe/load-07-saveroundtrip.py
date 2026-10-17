"""LOAD-7: save/resume round-trip for both branches + event-key sanity."""
import json, datetime, collections, yaml
from pathlib import Path

from text_adventure_tui_lib.yaml_loader import load_story_and_player, _load_story_old_format

REPO = Path("/home/nick/Documents/Projects/Text-Adventure-TUI")
STORIES = REPO / "text_adventure_tui_lib/story_parts"
EVENTS = REPO / "text_adventure_tui_lib/events"

print("== save -> resume round trip (game.py:221 names the file, game.py:451 replays the id) ==")
for sid in ("whispers_of_the_salted_crypt", "the_clockwork_heist"):
    story, _ = load_story_and_player(sid, STORIES)
    ts = "20261012_101112"
    name = f"{story.id}_{ts}.json"
    payload = {"game_state": {"current_story": story.__dict__}}
    json.dumps(payload, default=lambda o: o.__dict__)  # game.py:229
    resumed_id = json.loads(json.dumps(payload, default=lambda o: o.__dict__))["game_state"]["current_story"]["id"]
    story2, _ = load_story_and_player(resumed_id, STORIES)
    print(f"  {sid}: save={name}  resume_id={resumed_id!r}  reload_ok={story2.id == story.id}")

story, _ = _load_story_old_format("Whispers_of_the_Salted_Crypt", STORIES)
name = f"{story.id}_20261012_101112.json"
print(f"  OLD branch: save={name}  resume_id={story.id!r}")
try:
    load_story_and_player(story.id, STORIES)
    print("    reload OK")
except Exception as e:
    print(f"    reload FAILS: {type(e).__name__}: {e}")

print()
print("== keys that _create_events_from_data silently discards ==")
gen = yaml.safe_load((EVENTS / "general_events.yaml").read_text())
se = yaml.safe_load((EVENTS / "whispers_of_the_salted_crypt_story_events.yaml").read_text())
allkeys = collections.Counter()
for e in gen + se:
    allkeys.update(e.keys())
print("  keys present in shipped events YAML:", dict(allkeys))
print("  keys read by yaml_loader.py:21-27   : {'id','name','trigger','actions','options'}")
print("  -> anything else in an event is dropped with no warning")

print()
print("== do any shipped events omit name / options? ==")
for fname in ("general_events.yaml", "whispers_of_the_salted_crypt_story_events.yaml",
              "the_clockwork_heist_story_events.yaml"):
    data = yaml.safe_load((EVENTS / fname).read_text())
    print(f"  {fname}: missing name={[e.get('name') for e in data if 'name' not in e]}")
    print(f"      missing options={[e['id'] for e in data if 'options' not in e]}")

print()
print("== duplicate ids inside shipped files? ==")
for fname in ("general_events.yaml", "whispers_of_the_salted_crypt_story_events.yaml",
              "the_clockwork_heist_story_events.yaml"):
    data = yaml.safe_load((EVENTS / fname).read_text())
    ids = [e["id"] for e in data]
    dups = [k for k, v in collections.Counter(ids).items() if v > 1]
    print(f"  {fname}: n={len(ids)} dups={dups or 'none'}")
gids = {e['id'] for e in gen}
for fname in ("whispers_of_the_salted_crypt_story_events.yaml", "the_clockwork_heist_story_events.yaml"):
    sids = {e['id'] for e in yaml.safe_load((EVENTS / fname).read_text())}
    print(f"  overlap general vs {fname}: {sorted(gids & sids) or 'none'}")

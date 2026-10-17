"""FLOW-2 probe: loader under a non-UTF-8 locale (error path, step 7)."""
import locale
from pathlib import Path
from text_adventure_tui_lib.yaml_loader import load_story_and_player

print("locale.getpreferredencoding(False):", locale.getpreferredencoding(False))
stories_path = Path(__file__).resolve().parents[0]  # placeholder, replaced below
import text_adventure_tui_lib as pkg
stories_path = Path(pkg.__file__).parent / "story_parts"
try:
    story, player = load_story_and_player("whispers_of_the_salted_crypt", stories_path)
    print("loaded OK:", len(story.events), "events")
except UnicodeDecodeError as e:
    print("UnicodeDecodeError:", e)

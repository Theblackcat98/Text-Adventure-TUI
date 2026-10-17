import traceback
from pathlib import Path
import text_adventure_tui_lib as pkg
from text_adventure_tui_lib.yaml_loader import load_story_and_player
try:
    load_story_and_player("whispers_of_the_salted_crypt", Path(pkg.__file__).parent / "story_parts")
except UnicodeDecodeError:
    traceback.print_exc()

from pathlib import Path
from text_adventure_tui_lib.yaml_loader import load_story_and_player
story, player = load_story_and_player("whispers_of_the_salted_crypt", Path("text_adventure_tui_lib/story_parts"))
print("loaded ok:", len(story.events))

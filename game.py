import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.theme import Theme

# Define a global console object with a custom theme for consistency
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "story": "white",
    "prompt": "cyan",
    "choice": "yellow",
    "debug": "dim blue"
})
console = Console(theme=custom_theme)

STORY_DIR = "story_parts"
GAME_TITLE = "Terminal Text Adventure"

def display_title():
    """Displays the game title."""
    console.print(Panel(Text(GAME_TITLE, justify="center", style="bold green on black")), style="green")

def load_story_part(part_name):
    """Loads a story part from the STORY_DIR."""
    file_path = os.path.join(STORY_DIR, part_name)
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        console.print(f"Error: Story file {file_path} not found.", style="danger")
        return None

def display_story(text_content):
    """Displays the story text within a panel."""
    console.print(Panel(Text(text_content, style="story"), title="Story", border_style="info", padding=(1, 2)))

def get_player_choice(choices):
    """Presents choices to the player and gets their input."""
    console.print("\nChoose your action:", style="prompt")
    for i, choice_text in enumerate(choices, 1):
        console.print(f"{i}. [choice]{choice_text}[/choice]")

    valid_choices_str = [str(i) for i in range(1, len(choices) + 1)]

    chosen_option_str = Prompt.ask(
        "\nEnter the number of your choice",
        choices=valid_choices_str,
        show_choices=False
    )
    chosen_index = int(chosen_option_str) - 1
    return choices[chosen_index]

def get_llm_choices(current_story_segment):
    """Placeholder function for LLM integration."""
    console.print(f"DEBUG: get_llm_choices called with story: '{current_story_segment[:50]}...'", style="debug")
    return [
        "Investigate the strange symbols on the table.",
        "Listen more closely at the locked door.",
        "Examine the crumpled piece of paper you found.",
        "Try to use the smooth stone on the lock or symbols."
    ] # Slightly rephrased for clarity

def game_loop():
    """Main game loop with TUI refinements."""
    display_title()

    current_story_segment_id = "01_intro.txt"
    story_text = load_story_part(current_story_segment_id)

    if story_text:
        display_story(story_text)

        choices = get_llm_choices(story_text)

        player_choice = get_player_choice(choices)
        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")

        # Placeholder progression
        outcome_text = "You ponder your next move..." # Default outcome
        if player_choice == choices[0]:
            outcome_text = "The symbols seem ancient, pulsing with a faint energy under your gaze."
        elif player_choice == choices[1]:
            outcome_text = "A faint whisper can be heard, too indistinct to understand, and a rhythmic scratching."
        elif player_choice == choices[2]:
            outcome_text = "Holding the paper to the candlelight, faint lines like a map begin to appear!"
        elif player_choice == choices[3]:
            outcome_text = "The stone feels strangely warm. Rubbing it on a symbol makes the symbol glow briefly."

        console.print(Panel(Text(outcome_text, style="italic story"), title="Outcome", border_style="info", padding=(1,2)))

        console.print("\nThanks for playing! The story ends here for now.", style="bold green")
    else:
        console.print(f"Game cannot start. Story part '{current_story_segment_id}' missing.", style="danger")

if __name__ == "__main__":
    game_loop()

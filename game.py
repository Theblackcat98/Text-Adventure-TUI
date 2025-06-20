import os
import json # Ensure json is imported
import requests # Ensure requests is imported
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
    "debug": "dim blue",
    "error": "bold red" # Added error style
})
console = Console(theme=custom_theme)

STORY_DIR = "story_parts"
GAME_TITLE = "Terminal Text Adventure"

# Ollama Configuration (currently in game.py)
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3" # Changed to llama3 as per previous subtask logs, was mistral

hardcoded_choices = [
    "Fallback: Look around the room more closely.",
    "Fallback: Try to open the only door.",
    "Fallback: Check your pockets for anything useful.",
    "Fallback: Shout to see if anyone is nearby."
]

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
    """Generates choices using Ollama LLM, with error handling and fallback."""
    prompt = (
        f"You are a helpful assistant for a text adventure game. "
        f"The current situation is: '{current_story_segment}'. "
        f"Provide exactly 4 distinct, actionable, and concise choices for the player. "
        f"Each choice should start with a verb. Format them as a numbered list (1. , 2. , etc.)."
        f"Do not add any other text before or after the list."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False # Get the full response at once
    }
    console.print(f"DEBUG: Sending prompt to Ollama: '{prompt}'", style="debug")
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=15) # 15s timeout
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        response_data = response.json()
        generated_text = response_data.get("response", "").strip()

        console.print(f"DEBUG: LLM raw response: {generated_text}", style="debug")

        # Process the generated text to extract choices
        # Assuming LLM returns a numbered list like "1. Do this.
        # 2. Do that."
        parsed_choices = []
        for line in generated_text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and ('.' in line or ')' in line): # Basic check for "1. " or "1) "
                # Remove the number prefix (e.g., "1. ", "2) ")
                choice_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                if choice_text:
                    parsed_choices.append(choice_text)

        if len(parsed_choices) == 4:
            console.print("DEBUG: Successfully parsed 4 choices from LLM.", style="debug")
            return parsed_choices
        else:
            console.print(f"WARNING: LLM did not return 4 choices as expected (got {len(parsed_choices)}). Content: '{generated_text}'", style="warning")
            return hardcoded_choices[:] # Return a copy

    except requests.exceptions.RequestException as e:
        console.print(f"ERROR: LLM API request failed: {e}", style="error")
    except json.JSONDecodeError:
        console.print(f"ERROR: Failed to decode JSON response from LLM. Response: {response.text if 'response' in locals() else 'N/A'}", style="error")
    except Exception as e:
        console.print(f"ERROR: An unexpected error occurred while getting LLM choices: {e}", style="error")

    return hardcoded_choices[:] # Return a copy on any failure

def game_loop():
    """Main game loop with dynamic choices and adapted outcome display."""
    display_title()

    current_story_segment_id = "01_intro.txt"
    story_text = load_story_part(current_story_segment_id)

    if story_text:
        display_story(story_text)

        choices = get_llm_choices(story_text) # Dynamic choices

        player_choice = get_player_choice(choices)
        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")

        # ADAPTED OUTCOME: Generic message for dynamic choices
        outcome_text = f"You decided to '{player_choice}'. The air crackles with anticipation as the consequences of your action begin to unfold..."

        console.print(Panel(Text(outcome_text, style="italic story"), title="Outcome", border_style="info", padding=(1,2)))

        console.print("\nThanks for playing! The adventure pauses here for now.", style="bold green")
    else:
        console.print(f"Game cannot start. Story part '{current_story_segment_id}' missing.", style="danger")

if __name__ == "__main__":
    game_loop()

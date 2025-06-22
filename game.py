import os
import sys # Added for path resolution
import ollama # Import the main ollama library (provides ollama.Client, ollama.chat, etc.)
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
    "error": "bold red"
})
console = Console(theme=custom_theme)

# Determine the base directory for resources (story_parts)
# This makes it work whether run as a script or an installed package
try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    BASE_DIR = sys._MEIPASS
except AttributeError:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

STORY_DIR = os.path.join(BASE_DIR, "story_parts")
GAME_TITLE = "Terminal Text Adventure"

# Ollama Configuration
OLLAMA_HOST = "http://localhost:11434" # Default Ollama host
OLLAMA_MODEL = "phi4:latest"

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

    valid_choices_numbers = [str(i) for i in range(1, len(choices) + 1)]
    prompt_text = "Enter the number of your choice (or type 'quit' to exit)"

    while True:
        chosen_option_str = Prompt.ask(
            prompt_text,
            show_choices=False  # Set to False to prevent Rich from listing choices when we handle validation manually
        ).strip()

        if chosen_option_str.lower() == "quit":
            return "USER_QUIT"

        if chosen_option_str in valid_choices_numbers:
            try:
                chosen_index = int(chosen_option_str) - 1
                # Additional check for index bounds, though `in valid_choices_numbers` should suffice
                if 0 <= chosen_index < len(choices):
                    return choices[chosen_index]
                else: # Should not be reached if valid_choices_numbers is correct
                    console.print(f"[prompt.invalid]Error: Choice number '{chosen_option_str}' is out of range. Please try again.[/prompt.invalid]")
            except ValueError: # Should not be reached if chosen_option_str in valid_choices_numbers
                console.print(f"[prompt.invalid]Error: Invalid input '{chosen_option_str}'. Please enter a number or 'quit'.[/prompt.invalid]")
        else:
            console.print(f"[prompt.invalid]'{chosen_option_str}' is not a valid choice. Please enter one of the available numbers or 'quit'.[/prompt.invalid]")

def get_llm_story_continuation(current_story_segment, player_choice):
    """
    Generates the next story segment using Ollama LLM based on the player's choice.
    Returns the new_story_text.
    """
    player_action_text = f"The player chose to: '{player_choice}'."

    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"Current situation: '{current_story_segment}'\n"
        f"{player_action_text}\n\n"
        f"Continue the story from this point based on the player's choice. Keep the story segment concise (1-3 paragraphs).\n"
        f"Do not add any other text or choices, only the next part of the story."
    )
    messages = [{'role': 'user', 'content': prompt_content}]

    console.print(f"DEBUG: Attempting to connect to Ollama host: {OLLAMA_HOST}", style="debug")
    console.print(f"DEBUG: Sending prompt to Ollama (client.chat) for story continuation: {{'role': 'user', 'content': '{prompt_content[:150]}...'}}", style="debug")

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get('message', {}).get('content', "").strip()

        console.print(f"DEBUG: LLM raw response (story continuation): {generated_text}", style="debug")

        if not generated_text:
            console.print(f"WARNING: LLM provided an empty story segment. Content: '{generated_text}'", style="warning")
            return "The story seems to have hit a snag, and the path forward is unclear." # Fallback story

        return generated_text

    except ollama.ResponseError as e:
        console.print(f"ERROR: Ollama API error (host: {OLLAMA_HOST}): {e.status_code} - {e.error}", style="error")
    except ollama.RequestError as e:
        console.print(f"ERROR: Ollama request error (host: {OLLAMA_HOST}): {e}", style="error")
    except Exception as e:
        console.print(f"ERROR: An unexpected error occurred while getting LLM story continuation (host: {OLLAMA_HOST}): {e}", style="error")
        console.print(f"Please ensure Ollama is running and accessible at {OLLAMA_HOST}. https://ollama.com/download", style="info")

    # Fallback if any exception occurs
    return "Error: The story could not be continued due to an unexpected issue."


def get_llm_options(current_story_segment):
    """
    Generates player choices using Ollama LLM based on the current story segment.
    Returns a list of parsed_choices.
    """
    prompt_content = (
        f"You are a helpful assistant for a text adventure game.\n"
        f"The current situation is: '{current_story_segment}'\n\n"
        f"Based on this situation, provide exactly 4 distinct, actionable, and concise choices for the player.\n"
        f"Each choice should start with a verb.\n"
        f"Format the choices as a numbered list (e.g., 1. Choice A, 2. Choice B, etc.).\n"
        f"Do not add any other text before or after the choices, only the numbered list of choices."
    )
    messages = [{'role': 'user', 'content': prompt_content}]

    console.print(f"DEBUG: Attempting to connect to Ollama host: {OLLAMA_HOST}", style="debug")
    console.print(f"DEBUG: Sending prompt to Ollama (client.chat) for options: {{'role': 'user', 'content': '{prompt_content[:150]}...'}}", style="debug")

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get('message', {}).get('content', "").strip()

        console.print(f"DEBUG: LLM raw response (options): {generated_text}", style="debug")

        parsed_choices = []
        if not generated_text:
            console.print("WARNING: LLM provided no options.", style="warning")
            return hardcoded_choices[:] # Fallback to hardcoded choices

        for line in generated_text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and ('.' in line or ')' in line):
                choice_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                if choice_text:
                    parsed_choices.append(choice_text)

        if len(parsed_choices) == 4:
            console.print(f"DEBUG: Successfully parsed 4 choices from LLM.", style="debug")
            return parsed_choices
        elif len(parsed_choices) > 0:
            console.print(f"WARNING: LLM returned {len(parsed_choices)} choices instead of 4. Using what was returned.", style="warning")
            return parsed_choices # Return what we got, even if not 4
        else:
            console.print(f"WARNING: LLM did not return any valid choices. Choices text: '{generated_text}'", style="warning")
            return hardcoded_choices[:] # Fallback

    except ollama.ResponseError as e:
        console.print(f"ERROR: Ollama API error (host: {OLLAMA_HOST}): {e.status_code} - {e.error}", style="error")
    except ollama.RequestError as e:
        console.print(f"ERROR: Ollama request error (host: {OLLAMA_HOST}): {e}", style="error")
    except Exception as e:
        console.print(f"ERROR: An unexpected error occurred while getting LLM options (host: {OLLAMA_HOST}): {e}", style="error")
        console.print(f"Please ensure Ollama is running and accessible at {OLLAMA_HOST}. https://ollama.com/download", style="info")

    # Fallback if any exception occurs
    return hardcoded_choices[:]


def game_loop():
    display_title()

    current_story_segment_id = "01_intro.txt"
    story_text = load_story_part(current_story_segment_id)

    if not story_text:
        console.print(f"Game cannot start. Initial story part '{current_story_segment_id}' missing.", style="danger")
        return

    # previous_player_choice = None # Not strictly needed here anymore with the new flow

    while True:
        display_story(story_text) # Display current story segment

        # Get choices for the current story
        choices = get_llm_options(story_text)
        if not choices: # Check if choices list is empty or None
            console.print("Warning: LLM did not provide choices. Using fallback choices.", style="warning")
            choices = hardcoded_choices[:] # Use a copy
            if not choices: # Should not happen if hardcoded_choices is populated
                console.print("Critical Error: No fallback choices available. Ending game.", style="danger")
                break

        # Player action
        player_choice = get_player_choice(choices)

        if player_choice == "USER_QUIT":
            console.print("\nExiting game. Thanks for playing!", style="bold green")
            break

        # Check if the LLM itself suggested a "quit" option that the player chose.
        if isinstance(player_choice, str) and player_choice.strip().lower() == "quit":
            console.print("\nExiting game based on chosen action. Thanks for playing!", style="bold green")
            break

        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")

        # Get the next story segment based on the player's choice
        new_story_segment = get_llm_story_continuation(story_text, player_choice)

        if not new_story_segment or new_story_segment.startswith("Error:") or new_story_segment.startswith("The story seems to have hit a snag"):
            console.print(f"Error: The story could not continue. LLM response: '{new_story_segment}'. Ending game.", style="danger")
            break

        story_text = new_story_segment # Update story_text with the new segment

        # The new story_text (which is the outcome) will be displayed at the start of the next loop iteration.

    # console.print("\nThanks for playing! The adventure pauses here for now.", style="bold green") # Removed as per subtask

if __name__ == "__main__":
    game_loop()

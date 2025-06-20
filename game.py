import os
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

STORY_DIR = "story_parts"
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

def get_llm_choices(current_story_segment, previous_player_choice):
    """
    Generates the next story segment and choices using Ollama LLM.
    Returns a tuple (new_story_text, parsed_choices).
    """
    player_action_text = f"The player chose to: '{previous_player_choice}'." if previous_player_choice else "This is the beginning of the adventure."

    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"Current situation: '{current_story_segment}'\n"
        f"{player_action_text}\n\n"
        f"Continue the story from this point. Keep the story segment concise (1-3 paragraphs).\n"
        f"After the story continuation, on a new line, write the exact separator '===CHOICES==='.\n"
        f"Then, on new lines, provide exactly 4 distinct, actionable, and concise choices for the player based on the new story. Each choice should start with a verb and be formatted as a numbered list (1. Choice A, 2. Choice B, etc.).\n"
        f"Do not add any other text before the story or after the choices."
    )
    messages = [{'role': 'user', 'content': prompt_content}]

    console.print(f"DEBUG: Attempting to connect to Ollama host: {OLLAMA_HOST}", style="debug")
    console.print(f"DEBUG: Sending prompt to Ollama (client.chat) for story and choices: {{'role': 'user', 'content': '{prompt_content[:150]}...'}}", style="debug")

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get('message', {}).get('content', "").strip()

        console.print(f"DEBUG: LLM raw response (story & choices): {generated_text}", style="debug")

        separator = "===CHOICES==="
        if separator not in generated_text:
            console.print(f"WARNING: LLM response did not contain the separator '{separator}'. Content: '{generated_text}'", style="warning")
            # Returning None for story will make the game loop end.
            return None, hardcoded_choices[:]

        new_story_text, choices_text = generated_text.split(separator, 1)
        new_story_text = new_story_text.strip()
        choices_text = choices_text.strip()

        if not new_story_text:
            console.print(f"WARNING: LLM provided an empty story segment. Content: '{generated_text}'", style="warning")
            # Fallback story or None, with choices
            return "The story seems to have hit a snag, and the path forward is unclear.", hardcoded_choices[:]


        parsed_choices = []
        for line in choices_text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and ('.' in line or ')' in line):
                choice_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                if choice_text:
                    parsed_choices.append(choice_text)

        if len(parsed_choices) == 4:
            console.print("DEBUG: Successfully parsed new story and 4 choices from LLM.", style="debug")
            return new_story_text, parsed_choices
        else:
            console.print(f"WARNING: LLM did not return 4 choices as expected (got {len(parsed_choices)}). Choices text: '{choices_text}'", style="warning")
            # Return the story, but with fallback choices
            return new_story_text, hardcoded_choices[:]

    except ollama.ResponseError as e:
        console.print(f"ERROR: Ollama API error (host: {OLLAMA_HOST}): {e.status_code} - {e.error}", style="error")
    except ollama.RequestError as e:
        console.print(f"ERROR: Ollama request error (host: {OLLAMA_HOST}): {e}", style="error")
    except Exception as e:
        console.print(f"ERROR: An unexpected error occurred while getting LLM story and choices (host: {OLLAMA_HOST}): {e}", style="error")
        console.print(f"Please ensure Ollama is running and accessible at {OLLAMA_HOST}. https://ollama.com/download", style="info")

    # Fallback if any exception occurs
    return None, hardcoded_choices[:]


def game_loop():
    """Main game loop with dynamic choices and adapted outcome display."""
    display_title()

    current_story_segment_id = "01_intro.txt"  # Initial story segment
    story_text = load_story_part(current_story_segment_id)

    if not story_text:
        console.print(f"Game cannot start. Initial story part '{current_story_segment_id}' missing.", style="danger")
        return

    previous_player_choice = None # Initialize before loop

    while True:
        display_story(story_text) # Display current story segment

        # Get new story segment and choices from LLM
        # Assumes get_llm_choices will be modified to return (new_story_segment, available_choices)
        # and to take previous_player_choice as an argument.
        new_story_segment, choices = get_llm_choices(story_text, previous_player_choice if 'previous_player_choice' in locals() else None)

        if not new_story_segment:
            console.print("Error: The story could not continue as the LLM did not provide a next segment. Ending game.", style="danger")
            break

        story_text = new_story_segment # Update story_text with the new segment from LLM

        # Player action
        player_choice = get_player_choice(choices)

        if player_choice == "USER_QUIT":
            console.print("\nExiting game. Thanks for playing!", style="bold green")
            break

        # Check if the LLM itself suggested a "quit" option that the player chose.
        # This is a secondary check; USER_QUIT is the primary way to exit via typing 'quit'.
        if isinstance(player_choice, str) and player_choice.strip().lower() == "quit":
            console.print("\nExiting game based on chosen action. Thanks for playing!", style="bold green")
            break

        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")
        previous_player_choice = player_choice # Store for the next iteration

        # The new story_text (which is the outcome) will be displayed at the start of the next loop iteration.

    # console.print("\nThanks for playing! The adventure pauses here for now.", style="bold green") # Removed as per subtask

if __name__ == "__main__":
    game_loop()

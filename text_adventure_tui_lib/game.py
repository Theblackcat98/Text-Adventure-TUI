import os
import re  # For robust choice parsing
import sys  # Added for path resolution
import importlib.resources # For accessing package data

import ollama  # LLM library
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.theme import Theme

# Define a global console object with a custom theme for consistency
custom_theme = Theme(
    {
        "info": "dim cyan",
        "warning": "magenta",
        "danger": "bold red",
        "story": "white",
        "prompt": "cyan",
        "choice": "yellow",
        "debug": "dim blue",
        "error": "bold red",
    }
)
console = Console(theme=custom_theme)

# Ollama Configuration
OLLAMA_HOST = os.environ.get(
    "OLLAMA_HOST", "http://localhost:11434"
)  # Default Ollama host
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi4:latest")  # Default model

# Ollama Client Initialization
ollama_client = None
try:
    ollama_client = ollama.Client(host=OLLAMA_HOST)
    console.print(
        "DEBUG: Ollama client initialized for host: " + OLLAMA_HOST, style="debug"
    )
except Exception as e:
    console.print(
        "ERROR: Ollama client init for {} failed. Is it running? Err: {}".format(
            OLLAMA_HOST, e
        ),
        style="error",
    )

# STORY_DIR will now be determined by importlib.resources
GAME_TITLE = "Terminal Text Adventure"

hardcoded_choices = [
    "Fallback: Look around the room more closely.",
    "Fallback: Try to open the only door.",
    "Fallback: Check your pockets for anything useful.",
    "Fallback: Shout to see if anyone is nearby.",
]


def display_title():
    """Displays the game title."""
    console.print(
        Panel(Text(GAME_TITLE, justify="center", style="bold green on black")),
        style="green",
    )


def load_story_part(part_name):
    """Loads a story part using importlib.resources."""
    try:
        # Assuming 'text_adventure_tui_lib' is the package name
        # and 'story_parts' is a subdirectory within it.
        story_content = importlib.resources.read_text(
            "text_adventure_tui_lib.story_parts", part_name
        )
        return story_content.strip()
    except FileNotFoundError:
        # This specific exception might not be raised by read_text if the file isn't found,
        # it might raise ModuleNotFoundError or other import errors if the package/submodule isn't found.
        # However, if part_name is not found within the story_parts "resource container",
        # it will raise a FileNotFoundError.
        console.print(
            f"Error: Story file '{part_name}' not found within the package.",
            style="danger",
        )
        return None
    except Exception as e:
        console.print(
            f"Error loading story part '{part_name}': {e}", style="danger"
        )
        return None


def display_story(text_content):
    """Displays the story text within a panel."""
    console.print(
        Panel(
            Text(text_content, style="story"),
            title="Story",
            border_style="info",
            padding=(1, 2),
        )
    )


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
            show_choices=False,
        ).strip()

        if chosen_option_str.lower() == "quit":
            return "USER_QUIT"

        if chosen_option_str in valid_choices_numbers:
            chosen_index = int(chosen_option_str) - 1
            return choices[chosen_index]
        else:
            console.print(
                f"[prompt.invalid]'{chosen_option_str}' is not a valid choice. Please enter one of the available numbers or 'quit'.[/prompt.invalid]"  # noqa: E501
            )


def get_llm_story_continuation(current_story_segment, player_choice):
    """
    Generates the next story segment using Ollama LLM based on the player's choice.
    """
    player_action_text = f"The player chose to: '{player_choice}'."
    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"Current situation: '{current_story_segment}'\n"
        f"{player_action_text}\n\n"
        f"Continue the story from this point based on the player's choice. "
        f"Keep the story segment concise (1-3 paragraphs).\n"
        f"Do not add any other text or choices, only the next part of the story."
    )
    messages = [{"role": "user", "content": prompt_content}]

    console.print(
        f"DEBUG: Prompting LLM for story continuation (first 150 chars): "
        f"{prompt_content[:150]}...",
        style="debug",
    )

    if not ollama_client:
        console.print(
            "ERROR: Ollama client not available. Cannot get story continuation.",
            style="error",
        )
        return "Error: The story could not be continued because the Ollama connection is not working."

    try:
        response = ollama_client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get("message", {}).get("content", "").strip()
        console.print(
            f"DEBUG: LLM raw response for story (first 300 chars): {generated_text[:300]}...",  # noqa: E501
            style="debug",
        )
        if not generated_text:
            console.print(
                f"WARNING: LLM provided an empty story segment. Content: '{generated_text}'",  # noqa: E501
                style="warning",
            )
            return (
                "The story seems to have hit a snag, and the path forward is unclear."
            )
        return generated_text
    except ollama.ResponseError as e:
        console.print(
            f"ERR: Ollama API (host: {OLLAMA_HOST}): {e.status_code} - {e.error}",  # noqa: E501
            style="error",
        )
    except ollama.RequestError as e:
        console.print(
            f"ERR: Ollama request (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
    except Exception as e:
        console.print(
            f"ERR: Unexpected in LLM story (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
        console.print(
            f"Ensure Ollama is running at {OLLAMA_HOST}. See ollama.com/download",  # noqa: E501
            style="info",
        )
    return "Error: The story could not be continued due to an unexpected issue."


def _parse_llm_choices(generated_text):
    """Helper function to parse choices from LLM's raw text output."""
    parsed_choices = []
    if not generated_text:
        console.print(
            "WARNING: LLM provided no options (empty generated_text).", style="warning"
        )
        return []

    for line in generated_text.split("\n"):
        line = line.strip()
        match = re.match(r"^\s*\d+\s*[\.\)]\s*(.*)", line)
        if match:
            choice_text = match.group(1).strip()
            if choice_text:
                parsed_choices.append(choice_text)
    return parsed_choices


def get_llm_options(current_story_segment):
    """
    Generates player choices using Ollama LLM based on the current story segment.
    """
    prompt_content = (
        f"You are a helpful assistant for a text adventure game.\n"
        f"The current situation is: '{current_story_segment}'\n\n"
        f"Based on this situation, provide exactly 4 distinct, actionable, and "
        f"concise choices for the player.\n"
        f"Each choice should start with a verb.\n"
        f"Format the choices as a numbered list (e.g., 1. Choice A, 2. Choice B, etc.).\n"
        f"Do not add any other text before or after the choices, "
        f"only the numbered list of choices."
    )
    messages = [{"role": "user", "content": prompt_content}]

    console.print(
        f"DEBUG: Prompting LLM for options (first 150 chars): {prompt_content[:150]}...",
        style="debug",
    )

    if not ollama_client:
        console.print(
            "ERROR: Ollama client not available. Cannot get options.", style="error"
        )
        return hardcoded_choices[:]

    try:
        response = ollama_client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get("message", {}).get("content", "").strip()
        console.print(
            f"DEBUG: LLM raw response for options (first 300 chars): {generated_text[:300]}...",  # noqa: E501
            style="debug",
        )

        parsed_choices = _parse_llm_choices(generated_text)

        if not parsed_choices:
            if generated_text:
                console.print(
                    f"WARNING: Could not parse choices from LLM. Raw text (first 300): '{generated_text[:300]}...'",  # noqa: E501
                    style="warning",
                )
            return hardcoded_choices[:]

        if len(parsed_choices) == 4:
            console.print(
                f"DEBUG: Successfully parsed {len(parsed_choices)} choices from LLM (aimed for 4).",  # noqa: E501
                style="debug",
            )
        elif len(parsed_choices) > 0:
            console.print(
                f"WARNING: LLM returned {len(parsed_choices)} choices instead of 4. Using what was returned.",  # noqa: E501
                style="warning",
            )

        return parsed_choices

    except ollama.ResponseError as e:
        console.print(
            f"ERR: Ollama API (host: {OLLAMA_HOST}): {e.status_code} - {e.error}",  # noqa: E501
            style="error",
        )
    except ollama.RequestError as e:
        console.print(
            f"ERR: Ollama request (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
    except Exception as e:
        console.print(
            f"ERR: Unexpected in LLM options (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
        console.print(
            f"Ensure Ollama is running at {OLLAMA_HOST}. See ollama.com/download",  # noqa: E501
            style="info",
        )
    return hardcoded_choices[:]


def game_loop():
    display_title()
    current_story_segment_id = "01_intro.txt"
    story_text = load_story_part(current_story_segment_id)

    if not story_text:
        console.print(
            f"Game cannot start. Initial story part '{current_story_segment_id}' missing.",  # noqa: E501
            style="danger",
        )
        return

    while True:
        display_story(story_text)
        choices = get_llm_options(story_text)
        if not choices:
            console.print(
                "Warning: LLM did not provide choices or parsing failed. Using fallback choices.",  # noqa: E501
                style="warning",
            )
            choices = hardcoded_choices[:]
            if not choices:
                console.print(
                    "Critical Error: No fallback choices available. Ending game.",
                    style="danger",
                )
                break

        player_choice = get_player_choice(choices)

        if player_choice == "USER_QUIT":
            console.print("\nExiting game. Thanks for playing!", style="bold green")
            break

        if isinstance(player_choice, str) and player_choice.strip().lower() == "quit":
            console.print(
                "\nExiting game based on chosen action. Thanks for playing!",
                style="bold green",
            )
            break

        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")
        new_story_segment = get_llm_story_continuation(story_text, player_choice)

        if (
            not new_story_segment
            or new_story_segment.startswith("Error:")
            or new_story_segment.startswith("The story seems to have hit a snag")
        ):
            console.print(
                f"Error: Story couldn't continue. LLM response (first 100): '{new_story_segment[:100]}...'. Game over.",  # noqa: E501
                style="danger",
            )
            break
        story_text = new_story_segment


if __name__ == "__main__":
    game_loop()

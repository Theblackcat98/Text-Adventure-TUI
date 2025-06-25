import os
import re  # For robust choice parsing
import sys  # Added for path resolution
import importlib.resources # For accessing package data
import yaml # For parsing story_arc.yaml

import ollama  # LLM library
from .event_manager import EventManager # Import EventManager
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


def get_llm_story_continuation(current_story_segment, player_choice, turn_number, story_arc, llm_prompt_instructions=None):
    """
    Generates the next story segment using Ollama LLM, incorporating checkpoints and event prompt modifications.
    """
    if llm_prompt_instructions is None:
        llm_prompt_instructions = []

    player_action_text = f"The player chose to: '{player_choice}'."
    story_context_for_llm = f"Current situation: '{current_story_segment}'\n{player_action_text}\n"

    # Legacy Checkpoint (story_arc.yaml) injection
    if story_arc and 'checkpoints' in story_arc:
        for checkpoint in story_arc['checkpoints']:
            if checkpoint.get('turn') == turn_number:
                injection = checkpoint.get('prompt_injection', '')
                if injection:
                    console.print(f"DEBUG: Legacy Checkpoint for turn {turn_number} triggered: '{injection[:100]}...'", style="debug")
                    story_context_for_llm += f"\nA significant event from the main arc occurs: {injection}\n"
                if checkpoint.get('force_end_game'):
                    console.print("INFO: Legacy Story arc indicates game should end here (not yet fully handled in LLM prompt).", style="info")
                break

    # Add instructions from the new EventManager
    if llm_prompt_instructions:
        story_context_for_llm += "\nImportant context or events to consider for the story continuation:\n"
        for instruction in llm_prompt_instructions:
            story_context_for_llm += f"- {instruction}\n"
            console.print(f"DEBUG: Adding event instruction to LLM prompt: {instruction[:100]}...", style="dim blue")

    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"{story_context_for_llm}\n"
        f"Continue the story from this point, weaving in any significant events or context seamlessly. Keep the story segment concise (1-3 paragraphs).\n"
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
            f"Ensure Ollama is running at {OLLAMA_HOST}. See ollama.com/download",
            style="info",
        )
    # Return a generic continuation to allow testing of game flow without LLM
    return "The story path unfolds before you, marked by the choices you've made and the events that transpire..."


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


def load_story_arc(arc_file_name="story_arc.yaml"):
    """Loads and parses the story arc YAML file."""
    try:
        yaml_content = importlib.resources.read_text(
            "text_adventure_tui_lib.story_parts", arc_file_name
        )
        story_arc_data = yaml.safe_load(yaml_content)
        console.print(f"DEBUG: Story arc '{story_arc_data.get('title', 'Untitled Arc')}' loaded.", style="debug")
        return story_arc_data
    except FileNotFoundError:
        console.print(f"Warning: Story arc file '{arc_file_name}' not found. Proceeding without structured arc.", style="warning")
        return None
    except yaml.YAMLError as e:
        console.print(f"Error parsing story arc file '{arc_file_name}': {e}", style="danger")
        return None
    except Exception as e:
        console.print(f"Unexpected error loading story arc '{arc_file_name}': {e}", style="danger")
        return None


def game_loop(selected_story_name="short"): # Reverted default to short
    display_title()

    console.print(f"INFO: Loading story: {selected_story_name.upper()}", style="info")

    # Determine filenames based on selection
    story_arc_filename = f"{selected_story_name}_story_arc.yaml"
    events_filename = f"{selected_story_name}_story_events.yaml" # Corrected filename construction

    # Ensure general_events.yaml is also loaded if it contains common events
    # For now, let's assume each story's event file is self-contained or we load only one.
    # If we want common + specific, event_files_to_load would need adjustment.
    # Let's load general_events.yaml AND story-specific events for now.
    event_files_to_load = [
        ("text_adventure_tui_lib.events", "general_events.yaml"), # Common events
        ("text_adventure_tui_lib.events", events_filename)       # Story-specific events
    ]
    # Filter out general_events if the selected story IS general_events to prevent double loading
    if events_filename == "general_events.yaml":
        event_files_to_load = [("text_adventure_tui_lib.events", "general_events.yaml")]


    story_arc_data = load_story_arc(story_arc_filename) # Load the specific story arc
    event_manager = EventManager(event_files_to_load, console_instance=console)

    # Initialize game_state
    game_state = {
        'flags': {},
        'current_location': "eldoria_town_square", # Default starting location for event testing
        'inventory': [],
        'player_stats': {'health': 100},
        'turn_counter': 1, # Moved turn_counter into game_state
    }
    # Potentially override starting location from story_arc_data if defined
    if story_arc_data and story_arc_data.get('starting_location'):
        game_state['current_location'] = story_arc_data['starting_location']

    console.print(f"DEBUG: Initial game state: {game_state}", style="dim blue")

    current_story_segment_id = "01_intro.txt" # This could also come from story_arc_data or an event
    story_text = load_story_part(current_story_segment_id)

    if not story_text:
        console.print(
            f"Game cannot start. Initial story part '{current_story_segment_id}' missing.",
            style="danger",
        )
        return

    while True: # Main game loop
        console.print(f"\n--- Turn {game_state['turn_counter']} ---", style="bold magenta")

        # Initialize containers for event effects for this turn
        llm_prompt_instructions_for_turn = [] # For modify_prompt from events

        # --- PRE-LLM EVENT CHECK ---
        # Note: For player_action triggers, we'd ideally pass raw player input here *before* it's parsed into a choice.
        # For now, player_choice (which is the chosen text) can be a proxy, or we can defer player_action triggers.
        # Let's assume player_choice is available for now, even if it means events trigger *after* choice selection for this iteration.
        # A more advanced loop would get raw input -> process events -> then map to choice or LLM.

        # Display current story before player makes a choice for this turn.
        # If an event last turn resulted in an override, story_text would be that override.
        display_story(story_text)

        # Get player's choice based on the current story_text
        player_choice_text = get_player_choice(get_llm_options(story_text)) # Assuming get_llm_options is still primary for now

        if player_choice_text == "USER_QUIT":
            console.print("\nExiting game. Thanks for playing!", style="bold green")
            break
        if isinstance(player_choice_text, str) and player_choice_text.strip().lower() == "quit":
             console.print("\nExiting game based on chosen action. Thanks for playing!", style="bold green")
             break

        console.print(f"\nYou chose: [italic choice]{player_choice_text}[/italic choice]")

        # Now, check events based on the current game_state and the choice made.
        # Pass the current story_text as context.
        # Player_input_text for event checking can be player_choice_text.
        event_results = event_manager.check_and_trigger_events(
            game_state,
            player_input_text=player_choice_text,
            current_story_segment=story_text,
            llm_prompt_instructions=llm_prompt_instructions_for_turn
        )

        override_narrative = event_results.get("override_narrative")
        llm_prompt_instructions_for_turn = event_results.get("modified_prompt_instructions", [])

        if override_narrative is not None:
            story_text = override_narrative # This will be displayed at the start of the next loop
            console.print("DEBUG: Game loop received override_narrative. Story updated.", style="dim blue")
            # If narrative is overridden, we might skip LLM story continuation for this turn,
            # or the override_narrative becomes the new 'current_story_segment' for the LLM.
            # For simplicity, let's assume the override_narrative IS the story for this turn's end.
            # The LLM will then be called next turn based on this new story_text.
        else:
            # No override, so get story continuation from LLM
            # Pass any accumulated llm_prompt_instructions from events
            new_story_segment = get_llm_story_continuation(
                current_story_segment=story_text, # The story before player action and event processing
                player_choice=player_choice_text,
                turn_number=game_state['turn_counter'],
                story_arc=story_arc_data, # Legacy checkpoint system
                llm_prompt_instructions=llm_prompt_instructions_for_turn # From new event system
            )

            if (
                not new_story_segment
                or new_story_segment.startswith("Error:")
                or new_story_segment.startswith("The story seems to have hit a snag")
            ):
                console.print(
                    f"Error: Story couldn't continue. LLM response (first 100): '{new_story_segment[:100]}...'. Game over.",
                    style="danger",
                )
                break
            # If we reach here, LLM call was successful and new_story_segment is valid
            story_text = new_story_segment

        # Check for forced game end from checkpoint (from story_arc.yaml)
        if story_arc_data and 'checkpoints' in story_arc_data:
            for checkpoint in story_arc_data['checkpoints']:
                if checkpoint.get('turn') == game_state['turn_counter'] and checkpoint.get('force_end_game'):
                    final_message = checkpoint.get('prompt_injection', "The story comes to an end.")

                    # Customize final message based on flags for "short" story
                    if selected_story_name == "short":
                        if game_state['flags'].get('locket_retrieved'):
                            final_message = (
                                "Returning to the village, you find the elderly woman. Her eyes light up as you present the locket. "
                                "'Oh, bless you, kind traveler!' she exclaims, tears of joy streaming down her face. 'I... I don't have much, but please, take this as a token of my immense gratitude.' "
                                "She hands you a small, intricately carved wooden bird. You feel a sense of warmth and accomplishment."
                            )
                        else:
                            final_message = (
                                "You return to the village, but the locket remains lost. The elderly woman's face falls when you tell her. "
                                "'Oh, dear,' she sighs, her shoulders slumping. 'Well, thank you for trying, young one. Some things are just not meant to be found again.' "
                                "A sense of melancholy hangs in the air."
                            )
                    # Add more customizations for other stories here if needed.
                    # For medium/long, the generic prompt_injection from the checkpoint might be sufficient, or they might have their own event-driven endings.

                    console.print("\n--- The story arc has reached its conclusion ---", style="bold yellow")
                    # Display the last piece of story text (which might be an override or LLM generated)
                    display_story(story_text)
                    # Then display the customized or default final message from the checkpoint
                    console.print(Panel(Text(final_message, style="italic yellow"), border_style="yellow"),)
                    console.print("Thanks for playing!", style="bold green")
                    return # End the game_loop

        # Event-driven game end could also be handled here if an event sets a specific flag

        game_state['turn_counter'] += 1 # Increment turn counter


if __name__ == "__main__":
    # Example of how to run a specific story when executing the module directly.
    # In a real application, this might come from command-line arguments.
    selected_story = "medium" # Can be "short", "medium", or "long"
    console.print(f"Running story: {selected_story} (from __main__)", style="bold blue")
    game_loop(selected_story_name=selected_story)

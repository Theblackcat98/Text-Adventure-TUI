import os
import re  # For robust choice parsing
import sys  # Added for path resolution
import importlib.resources # For accessing package data
import yaml # For parsing story_arc.yaml
import json # For saving and loading game state
from pathlib import Path # For handling save paths
import datetime # For timestamping save files

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

# Debug Mode Configuration
DEBUG_MODE_ENABLED = False # Default to False

# Ollama Client Initialization
ollama_client = None

# Helper function for debug printing
def debug_print(message, style="debug", **kwargs):
    """Prints a message to the console only if DEBUG_MODE_ENABLED is True."""
    if DEBUG_MODE_ENABLED:
        console.print(message, style=style, **kwargs)

try:
    ollama_client = ollama.Client(host=OLLAMA_HOST)
    debug_print( # Already using debug_print here, this is fine
        "Ollama client initialized for host: " + OLLAMA_HOST
    )
except Exception as e:
    console.print(
        "ERROR: Ollama client init for {} failed. Is it running? Err: {}".format(
            OLLAMA_HOST, e
        ),
        style="error",
    )

# Save Game Configuration
SAVE_DIR_NAME = ".text_adventure_tui_saves"
USER_HOME_DIR = Path.home()
SAVE_GAME_PATH = USER_HOME_DIR / SAVE_DIR_NAME

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


def save_game_state(game_state, current_story_text, selected_story_id, event_manager_state):
    """Saves the current game state to a file."""
    try:
        SAVE_GAME_PATH.mkdir(parents=True, exist_ok=True) # Ensure save directory exists

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{selected_story_id}_{timestamp}.json"
        save_file_path = SAVE_GAME_PATH / filename

        # Prepare the data to save
        data_to_save = {
            "game_state": game_state,
            "current_story_text": current_story_text,
            "selected_story_id": selected_story_id,
            "event_manager_state": event_manager_state,
            "save_format_version": "1.0" # For future compatibility
        }

        with open(save_file_path, "w") as f:
            json.dump(data_to_save, f, indent=4)

        console.print(f"Game saved successfully as '{filename}'", style="bold green")
        return True
    except Exception as e:
        console.print(f"Error saving game: {e}", style="danger")
        return False


def list_save_files():
    """Lists available save files."""
    if not SAVE_GAME_PATH.exists():
        console.print("No save directory found. Nothing to load.", style="info")
        return []

    save_files = sorted(
        [f for f in SAVE_GAME_PATH.iterdir() if f.is_file() and f.suffix == '.json'],
        key=lambda f: f.stat().st_mtime, reverse=True # Show newest first
    )

    if not save_files:
        console.print("No save files found.", style="info")
        return []

    display_saves = []
    for i, f_path in enumerate(save_files):
        try:
            # Attempt to read story_id and timestamp from filename or content for better display
            parts = f_path.name.replace(".json", "").split("_")
            story_id_display = parts[0]
            timestamp_display = parts[1] if len(parts) > 1 else "UnknownTime"
            # Convert YYYYMMDD to YYYY-MM-DD and HHMMSS to HH:MM:SS for readability
            if len(timestamp_display) == 8 and timestamp_display.isdigit(): # YYYYMMDD
                 # This part is if timestamp is just date, which is not current format.
                 # Current format is YYYYMMDD_HHMMSS
                 pass # Not handling this specific case, as current format is different.
            elif len(parts) > 2 and len(parts[1]) == 8 and len(parts[2]) == 6 : # storyid_YYYYMMDD_HHMMSS
                story_id_display = parts[0]
                date_str = parts[1]
                time_str = parts[2]
                timestamp_display = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"


            display_saves.append({
                "path": f_path,
                "name": f_path.name,
                "display_text": f"{i+1}. {story_id_display.replace('_', ' ').title()} ({timestamp_display})"
            })
        except Exception: # Fallback if parsing filename fails
             display_saves.append({
                "path": f_path,
                "name": f_path.name,
                "display_text": f"{i+1}. {f_path.name}"
            })
    return display_saves


def load_game_state(save_file_path):
    """Loads game state from a file."""
    try:
        with open(save_file_path, "r") as f:
            data = json.load(f)

        # Basic validation
        if "game_state" not in data or "current_story_text" not in data \
           or "selected_story_id" not in data or "event_manager_state" not in data:
            console.print(f"Error: Save file '{save_file_path.name}' is corrupted or in an old format.", style="danger")
            return None

        # Restore EventManager first
        # We need to know the story_id to load the correct event files for that story.
        selected_story_id = data["selected_story_id"]

        # Construct event_files_config based on the loaded story_id
        # This logic should mirror how it's done in game_loop's initialization
        events_filename_for_load = f"{selected_story_id}_story_events.yaml"
        event_files_to_load_for_resume = [
            ("text_adventure_tui_lib.events", "general_events.yaml"),
            ("text_adventure_tui_lib.events", events_filename_for_load)
        ]
        if events_filename_for_load == "general_events.yaml": # Avoid double load
            event_files_to_load_for_resume = [("text_adventure_tui_lib.events", "general_events.yaml")]

        loaded_event_manager = EventManager(event_files_to_load_for_resume, console_instance=console)
        loaded_event_manager.load_state(data["event_manager_state"])

        console.print(f"Game state loaded successfully from '{save_file_path.name}'", style="bold green")
        return {
            "game_state": data["game_state"],
            "current_story_text": data["current_story_text"],
            "selected_story_id": data["selected_story_id"],
            "event_manager": loaded_event_manager # Return the rehydrated EventManager
        }
    except FileNotFoundError:
        console.print(f"Error: Save file '{save_file_path.name}' not found.", style="danger")
        return None
    except json.JSONDecodeError:
        console.print(f"Error: Save file '{save_file_path.name}' is not valid JSON.", style="danger")
        return None
    except Exception as e:
        console.print(f"Error loading game from '{save_file_path.name}': {e}", style="danger")
        return None


def get_player_choice(choices, game_state_for_save, current_story_text_for_save, selected_story_id_for_save, event_manager_for_save):
    """
    Presents choices to the player and gets their input.
    Also handles special commands like /save, /debug state, /force_event.
    """
    prompt_message = "\nChoose your action (type number, or /save, /quit, /debug state, /force_event <id> ):"
    console.print(prompt_message, style="prompt")

    for i, choice_text in enumerate(choices, 1):
        console.print(f"{i}. [choice]{choice_text}[/choice]")

    valid_choices_numbers = [str(i) for i in range(1, len(choices) + 1)]
    # Prompt text updated to reflect new commands
    prompt_text_ask = "Enter choice" # Rich prompt will show this

    while True:
        # Re-display choices if a debug command was handled and we are re-prompting
        # This is implicitly handled by looping and re-printing prompt_message + choices if `continue` is hit.

        chosen_option_str = Prompt.ask(
            prompt_text_ask, # Short text for the actual input line
            show_choices=False,
        ).strip()

        # Handle special commands first
        if chosen_option_str.lower().startswith("/debug state"):
            console.print("\n--- DEBUG: Current Game State ---", style="bold magenta")
            console.print(f"Current Location: {game_state_for_save.get('current_location')}", style="debug")
            console.print(f"Flags: {game_state_for_save.get('flags')}", style="debug")
            console.print(f"Inventory: {game_state_for_save.get('inventory')}", style="debug")
            console.print(f"Player Stats: {game_state_for_save.get('player_stats')}", style="debug")
            console.print(f"Turn Counter: {game_state_for_save.get('turn_counter')}", style="debug")
            console.print(f"Turns in Location: {game_state_for_save.get('location_turn_count')}", style="debug")

            if event_manager_for_save:
                console.print(f"All Event IDs: {list(event_manager_for_save.events.keys())}", style="debug")
                console.print(f"Triggered 'once' Event IDs: {list(event_manager_for_save.triggered_event_ids)}", style="debug")
            console.print("--- END DEBUG ---", style="bold magenta")
            # Re-prompt for action
            console.print(prompt_message, style="prompt")
            for i, choice_text in enumerate(choices, 1):
                console.print(f"{i}. [choice]{choice_text}[/choice]")
            continue

        elif chosen_option_str.lower().startswith("/force_event"):
            parts = chosen_option_str.split()
            if len(parts) > 1:
                event_id_to_force = parts[1]
                if event_manager_for_save:
                    # We need llm_prompt_instructions_for_turn for the event manager to potentially modify.
                    # This is tricky as it's usually initialized fresh each turn in game_loop.
                    # Forcing an event outside that context means its modify_prompt might not have the desired effect
                    # or could pollute a later one. For now, let's pass a dummy list.
                    # The primary use of /force_event is for state changes (flags, items, loc).
                    dummy_llm_instructions = []
                    force_results = event_manager_for_save.execute_event_actions(
                        event_id_to_force,
                        game_state_for_save, # Modifies game_state directly
                        dummy_llm_instructions
                    )
                    console.print(f"DEBUG: Forced event '{event_id_to_force}'. Results: {force_results}", style="debug")
                    # Game state is modified. What about narrative?
                    # If forced_override_narrative is returned, we could potentially use it,
                    # but it might make the next turn's flow weird.
                    # For now, the main impact is state change. Player will take their normal turn after this.
                else:
                    console.print("DEBUG: Event manager not available to force event.", style="warning")
            else:
                console.print("DEBUG: Usage: /force_event <event_id>", style="warning")
            # Re-prompt
            console.print(prompt_message, style="prompt")
            for i, choice_text in enumerate(choices, 1):
                console.print(f"{i}. [choice]{choice_text}[/choice]")
            continue

        elif chosen_option_str.lower() == "/quit" or chosen_option_str.lower() == "quit":
            return "USER_QUIT"
        elif chosen_option_str.lower() == "/save":
            event_manager_state_to_save = event_manager_for_save.get_state()
            save_game_state(
                game_state_for_save,
                current_story_text_for_save,
                selected_story_id_for_save,
                event_manager_state_to_save
            )
            # After saving, re-prompt for action, so the player doesn't lose a turn.
            console.print("\nChoose your action (or type /save, /quit):", style="prompt") # Re-show prompt header
            for i, choice_text in enumerate(choices, 1): # Re-list choices
                console.print(f"{i}. [choice]{choice_text}[/choice]")
            continue # Loop back to ask for input again

        if chosen_option_str in valid_choices_numbers:
            chosen_index = int(chosen_option_str) - 1
            return choices[chosen_index]
        else:
            console.print(
                f"[prompt.invalid]'{chosen_option_str}' is not a valid choice. Please enter one of the available numbers or a command like '/save' or '/quit'.[/prompt.invalid]"
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
                    debug_print(f"Legacy Checkpoint for turn {turn_number} triggered: '{injection[:100]}...'")
                    story_context_for_llm += f"\nA significant event from the main arc occurs: {injection}\n"
                if checkpoint.get('force_end_game'):
                    # INFO level might be desired even if debug is off, so keeping console.print
                    console.print("INFO: Legacy Story arc indicates game should end here (not yet fully handled in LLM prompt).", style="info")
                break

    # Add instructions from the new EventManager
    if llm_prompt_instructions:
        story_context_for_llm += "\nImportant context or events to consider for the story continuation:\n"
        for instruction in llm_prompt_instructions:
            story_context_for_llm += f"- {instruction}\n"
            debug_print(f"Adding event instruction to LLM prompt: {instruction[:100]}...", style="dim blue")

    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"{story_context_for_llm}\n"
        f"Continue the story from this point, weaving in any significant events or context seamlessly. Keep the story segment concise (1-3 paragraphs).\n"
        f"Do not add any other text or choices, only the next part of the story."
    )
    messages = [{"role": "user", "content": prompt_content}]

    debug_print(
        f"Prompting LLM for story continuation (first 150 chars): {prompt_content[:150]}..."
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
        debug_print(
            f"LLM raw response for story (first 300 chars): {generated_text[:300]}..."
        )
        if not generated_text:
            # WARNING is likely important enough to show regardless of debug mode
            console.print(
                f"WARNING: LLM provided an empty story segment. Content: '{generated_text}'",
                style="warning",
            )
            return (
                "The story seems to have hit a snag, and the path forward is unclear."
            )
        return generated_text
    except ollama.ResponseError as e:
        # ERRORS are important, show regardless of debug mode
        console.print(
            f"ERR: Ollama API (host: {OLLAMA_HOST}): {e.status_code} - {e.error}",
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
        # INFO might be useful even if debug is off
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

    debug_print(
        f"Prompting LLM for options (first 150 chars): {prompt_content[:150]}..."
    )

    if not ollama_client:
        console.print( # Error - show always
            "ERROR: Ollama client not available. Cannot get options.", style="error"
        )
        return hardcoded_choices[:]

    try:
        response = ollama_client.chat(model=OLLAMA_MODEL, messages=messages)
        generated_text = response.get("message", {}).get("content", "").strip()
        debug_print(
            f"LLM raw response for options (first 300 chars): {generated_text[:300]}..."
        )

        parsed_choices = _parse_llm_choices(generated_text)

        if not parsed_choices:
            if generated_text: # Warning - show always
                console.print(
                    f"WARNING: Could not parse choices from LLM. Raw text (first 300): '{generated_text[:300]}...'",
                    style="warning",
                )
            return hardcoded_choices[:]

        if len(parsed_choices) == 4:
            debug_print(
                f"Successfully parsed {len(parsed_choices)} choices from LLM (aimed for 4)."
            )
        elif len(parsed_choices) > 0: # Warning - show always
            console.print(
                f"WARNING: LLM returned {len(parsed_choices)} choices instead of 4. Using what was returned.",
                style="warning",
            )

        return parsed_choices

    except ollama.ResponseError as e: # Error - show always
        console.print(
            f"ERR: Ollama API (host: {OLLAMA_HOST}): {e.status_code} - {e.error}",
            style="error",
        )
    except ollama.RequestError as e: # Error - show always
        console.print(
            f"ERR: Ollama request (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
    except Exception as e: # Error - show always
        console.print(
            f"ERR: Unexpected in LLM options (host: {OLLAMA_HOST}): {e}",
            style="error",
        )
        console.print( # Info - show always
            f"Ensure Ollama is running at {OLLAMA_HOST}. See ollama.com/download",
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
        debug_print(f"Story arc '{story_arc_data.get('title', 'Untitled Arc')}' loaded.")
        return story_arc_data
    except FileNotFoundError: # Warning - show always
        console.print(f"Warning: Story arc file '{arc_file_name}' not found. Proceeding without structured arc.", style="warning")
        return None
    except yaml.YAMLError as e:
        console.print(f"Error parsing story arc file '{arc_file_name}': {e}", style="danger")
        return None
    except Exception as e:
        console.print(f"Unexpected error loading story arc '{arc_file_name}': {e}", style="danger")
        return None


def game_loop(selected_story_name="short", initial_game_state=None, initial_story_text=None, initial_event_manager=None):
    display_title()

    if initial_game_state: # Resuming game
        game_state = initial_game_state
        story_text = initial_story_text
        event_manager = initial_event_manager
        # selected_story_name is already correctly set from the loaded data (passed into game_loop)
        story_arc_filename = f"{selected_story_name}_story_arc.yaml" # Need this for legacy checkpoints
        story_arc_data = load_story_arc(story_arc_filename)
        console.print(f"INFO: Resuming story: {selected_story_name.upper()} at turn {game_state.get('turn_counter', 'N/A')}", style="info")

    else: # Starting a new game
        console.print(f"INFO: Loading new story: {selected_story_name.upper()}", style="info")
        story_arc_filename = f"{selected_story_name}_story_arc.yaml"
        events_filename = f"{selected_story_name}_story_events.yaml"

        event_files_to_load = [
            ("text_adventure_tui_lib.events", "general_events.yaml"),
            ("text_adventure_tui_lib.events", events_filename)
        ]
        if events_filename == "general_events.yaml":
            event_files_to_load = [("text_adventure_tui_lib.events", "general_events.yaml")]

        story_arc_data = load_story_arc(story_arc_filename)
        event_manager = EventManager(event_files_to_load, console_instance=console)

        game_state = {
            'flags': {},
            'current_location': "eldoria_town_square",
            'inventory': [],
            'player_stats': {'health': 100}, # Example stat
            'turn_counter': 1,
            'location_turn_count': 1 # Turns spent in the current location, starts at 1
        }
        if story_arc_data and story_arc_data.get('starting_location'):
            game_state['current_location'] = story_arc_data['starting_location']

        # Initialize inventory and player_stats if defined in story_arc_data (for new game)
        if story_arc_data and story_arc_data.get('initial_inventory'):
            game_state['inventory'] = list(story_arc_data['initial_inventory'])
        if story_arc_data and story_arc_data.get('initial_player_stats'):
            game_state['player_stats'] = dict(story_arc_data['initial_player_stats'])

        # For new game, load initial story text (e.g. intro)
        # This might also come from story_arc_data or an event in a more complex setup
        initial_story_part_id = "01_intro.txt"
        if story_arc_data and story_arc_data.get('initial_story_part'):
            initial_story_part_id = story_arc_data['initial_story_part']
        story_text = load_story_part(initial_story_part_id)

        if not story_text:
            console.print( # Error - show always
                f"Game cannot start. Initial story part '{initial_story_part_id}' missing.",
                style="danger",
            )
            return
        debug_print(f"Initial game state (new game): {game_state}", style="dim blue")


    # Main game loop starts here, common for new or resumed games
    while True:
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

        # Check for location change from previous turn's events to reset location_turn_count
        # This internal flag is set by EventManager if 'change_location' action occurred.
        previous_location_for_turn_count = game_state.get("_previous_location_for_turn_count", None)
        current_location = game_state['current_location']

        if current_location != previous_location_for_turn_count or game_state.pop("__location_changed_by_event", False):
            game_state['location_turn_count'] = 1
            debug_print(f"Location changed or event override, location_turn_count reset to 1 for '{current_location}'.", style="dim blue")
        elif not initial_game_state and game_state['turn_counter'] == 1 : # Very first turn of a new game
             game_state['location_turn_count'] = 1 # Already set at init, but ensure it is 1
        else: # Same location, not first turn of game, not just loaded
            game_state['location_turn_count'] = game_state.get('location_turn_count', 0) + 1

        game_state["_previous_location_for_turn_count"] = current_location # Store for next turn's comparison


        # Display injected narratives (pre-LLM call, from previous turn's events if any)
        # This assumes injected_narratives are stored in game_state or passed around if not immediately displayed
        # For now, event_results are processed in the same turn, so pre-injections are before current story display

        display_story(story_text) # Displays the main narrative text for the current turn

        # Get player's choice based on the current story_text
        # Pass necessary game state components for the /save command
        player_choice_text = get_player_choice(
            choices=get_llm_options(story_text),
            game_state_for_save=game_state,
            current_story_text_for_save=story_text,
            selected_story_id_for_save=selected_story_name, # This is the story ID
            event_manager_for_save=event_manager
        )

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
            player_input_text=player_choice_text, # This is the text of the chosen option
            current_story_segment=story_text, # Story text before this turn's LLM call
            llm_prompt_instructions=llm_prompt_instructions_for_turn # Initially empty, populated by events
        )

        override_narrative = event_results.get("override_narrative")
        llm_prompt_instructions_for_turn = event_results.get("modified_prompt_instructions", [])
        injected_narratives_pre = event_results.get("injected_narratives_pre", [])
        injected_narratives_post = event_results.get("injected_narratives_post", [])

        # Display any "pre" injected narratives from events
        for text_block in injected_narratives_pre:
            display_story(text_block) # Or a different panel style for injected text

        if override_narrative is not None:
            story_text = override_narrative
            debug_print("Game loop received override_narrative. Story updated.", style="dim blue")
            # If narrative is overridden, this becomes the main story text for the end of this turn.
            # The LLM was not called to generate story continuation this turn.
        else:
            # No override, so get story continuation from LLM
            new_story_segment = get_llm_story_continuation(
                current_story_segment=story_text,
                player_choice=player_choice_text,
                turn_number=game_state['turn_counter'],
                story_arc=story_arc_data,
                llm_prompt_instructions=llm_prompt_instructions_for_turn
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
            story_text = new_story_segment # This is the LLM-generated continuation

        # Display any "post" injected narratives from events
        for text_block in injected_narratives_post:
            display_story(text_block) # Or a different panel style

        # Check for forced game end from checkpoint (from story_arc.yaml)
        # This check should happen AFTER all narrative for the turn (override or LLM + injections) is determined.
        # The 'story_text' at this point is the final narrative piece of the turn before choices for next turn.

        active_checkpoint = None
        if story_arc_data and 'checkpoints' in story_arc_data:
            for cp in story_arc_data['checkpoints']:
                if cp.get('turn') == game_state['turn_counter'] and cp.get('force_end_game'):
                    active_checkpoint = cp
                    break

        if active_checkpoint:
            final_message = active_checkpoint.get('prompt_injection', "The story comes to an end.")

            # Generic mechanism for flag-based message customization
            # Checkpoints can have a 'flag_messages' list:
            # flag_messages:
            #   - flag: "locket_retrieved"
            #     message_if_set: "Positive outcome..."
            #     message_if_not_set: "Negative outcome..."
            #   - flag: "another_condition"
            #     message_if_set: "..."

            custom_messages = active_checkpoint.get("flag_messages", [])
            for fm_config in custom_messages:
                flag_name = fm_config.get("flag")
                if flag_name:
                    if game_state['flags'].get(flag_name, False): # Flag is set
                        final_message = fm_config.get("message_if_set", final_message)
                    else: # Flag is not set
                        final_message = fm_config.get("message_if_not_set", final_message)
                    # Note: This simplistic approach takes the message from the *last* matching flag_messages entry.
                    # More complex logic could be added if multiple flag conditions need to combine.
                    break # Assuming one primary flag condition dictates the final message modification for now.


            console.print("\n--- The story arc has reached its conclusion ---", style="bold yellow")
            # Display the final narrative segment of the turn (which could be an override or LLM generated)
            # This is the 'story_text' that was determined just before this end-game check.
            display_story(story_text)

            # Then display the (potentially customized) final message from the checkpoint
            console.print(Panel(Text(final_message, style="italic yellow"), border_style="yellow"),)
            console.print("Thanks for playing!", style="bold green")
            return # End the game_loop

        # Event-driven game end could also be handled here if an event sets a specific flag like 'GAME_OVER_EVENT'

        game_state['turn_counter'] += 1 # Increment turn counter


def list_available_stories():
    """Scans the story_parts directory for available stories."""
    stories = []
    try:
        story_files = importlib.resources.contents("text_adventure_tui_lib.story_parts")
        for item in story_files:
            if item.endswith("_story_arc.yaml"):
                story_name = item.replace("_story_arc.yaml", "")
                # Attempt to load the YAML to get a display title if present
                try:
                    arc_content = importlib.resources.read_text("text_adventure_tui_lib.story_parts", item)
                    arc_data = yaml.safe_load(arc_content)
                    title = arc_data.get("title", story_name.replace("_", " ").title())
                except Exception:
                    title = story_name.replace("_", " ").title() # Fallback title
                stories.append({"id": story_name, "title": title})

        # Sort stories by title for consistent display
        stories.sort(key=lambda x: x['title'])

    except Exception as e:
        console.print(f"Error listing available stories: {e}", style="danger")

    if not stories:
        # Fallback in case no stories are found or an error occurs,
        # this ensures the menu can still show something or quit.
        console.print("Warning: No story arc files found or error listing them. Check story_parts.", style="warning")
        # Example: Add a dummy or error story entry if needed for testing or graceful failure
        # stories.append({"id": "error_story", "title": "Error: No Stories Available"})
    return stories


def main_menu():
    """Displays the main menu and handles user selection."""
    global DEBUG_MODE_ENABLED
    while True: # Loop for the main menu, allows returning to menu after a game
        display_title()
        console.print(Panel(Text("Main Menu", justify="center")), style="bold cyan")

        available_stories = list_available_stories()
        menu_options_display = [] # For display
        action_map = {} # To map menu index back to an action or story_id

        current_menu_idx = 1

        if available_stories:
            menu_options_display.append(Text("\n--- Start a New Adventure ---", style="yellow"))
            for story in available_stories:
                menu_options_display.append(Text(f"{current_menu_idx}. Start: {story['title']}"))
                action_map[str(current_menu_idx)] = {"type": "start_story", "story_id": story['id'], "title": story['title']}
                current_menu_idx += 1
        else:
            menu_options_display.append(Text("No stories found. Please check your installation.", style="warning"))

        menu_options_display.append(Text("\n--- Game Options ---", style="yellow"))
        # Add Resume Game option
        menu_options_display.append(Text(f"{current_menu_idx}. Resume Game"))
        action_map[str(current_menu_idx)] = {"type": "resume_game"}
        current_menu_idx += 1

        # Add Toggle Debug Output option
        debug_status = "ON" if DEBUG_MODE_ENABLED else "OFF"
        menu_options_display.append(Text(f"{current_menu_idx}. Toggle Debug Output: [{debug_status}]"))
        action_map[str(current_menu_idx)] = {"type": "toggle_debug"}
        current_menu_idx += 1

        # Add Quit option
        menu_options_display.append(Text(f"{current_menu_idx}. Quit Game"))
        action_map[str(current_menu_idx)] = {"type": "quit"}

        for option_text in menu_options_display:
            console.print(option_text, style="prompt") # Assuming 'prompt' style is suitable

        user_input_valid = False
        while not user_input_valid: # Loop for current menu display until valid choice or quit
            choice_str = Prompt.ask("\nEnter your choice", show_choices=False).strip().lower()
            action = action_map.get(choice_str)

            if action:
                user_input_valid = True # Valid choice received
                if action["type"] == "start_story":
                    console.print(f"\nStarting story: '{action['title']}'...", style="info")
                    game_loop(selected_story_name=action['story_id'])
                    # After game_loop finishes, it will break this inner loop and the outer loop will reiterate,
                    # re-displaying the main menu.
                elif action["type"] == "toggle_debug":
                    DEBUG_MODE_ENABLED = not DEBUG_MODE_ENABLED
                    console.print(f"Debug output {'enabled' if DEBUG_MODE_ENABLED else 'disabled'}.", style="info")
                    user_input_valid = False # Stay in menu, re-display with updated toggle status
                    break # Break from choice processing, main_menu loop will re-render
                elif action["type"] == "resume_game":
                    saved_games = list_save_files()
                    if not saved_games:
                        console.print("No saved games found to resume. Returning to menu.", style="info")
                        # No valid input yet, stay in input loop, which will then break to outer menu loop
                        user_input_valid = False # Re-prompt in current menu session
                        break # Break from the choice processing, will go to outer loop of main_menu

                    console.print("\n--- Select a Game to Resume ---", style="yellow")
                    for save_info in saved_games:
                        console.print(save_info["display_text"], style="prompt")

                    console.print(f"{len(saved_games) + 1}. Back to Main Menu", style="prompt")

                    while True: # Loop for save selection
                        resume_choice_str = Prompt.ask("Enter number of save to load, or back to menu", show_choices=False).strip()
                        try:
                            resume_choice_idx = int(resume_choice_str)
                            if 1 <= resume_choice_idx <= len(saved_games):
                                selected_save_path = saved_games[resume_choice_idx - 1]["path"]
                                loaded_data = load_game_state(selected_save_path)
                                if loaded_data:
                                    console.print(f"Attempting to resume: {selected_save_path.name}", style="info")
                                    # Pass loaded data to game_loop
                                    game_loop(
                                        selected_story_name=loaded_data["selected_story_id"],
                                        initial_game_state=loaded_data["game_state"],
                                        initial_story_text=loaded_data["current_story_text"],
                                        initial_event_manager=loaded_data["event_manager"]
                                    )
                                    # After game_loop (resumed) finishes, break to outer main_menu loop
                                    user_input_valid = True # To exit the main_menu's input loop correctly
                                    return # Exit main_menu, effectively, as game_loop finished
                                else:
                                    console.print("Failed to load game. Returning to main menu.", style="error")
                                    user_input_valid = False # Re-prompt in current menu session
                                    break # Break from save selection, back to main menu display
                            elif resume_choice_idx == len(saved_games) + 1: # Back to Main Menu
                                user_input_valid = False # Re-prompt in current menu session
                                break # Break from save selection, back to main menu display
                            else:
                                console.print("Invalid selection. Please try again.", style="error")
                        except ValueError:
                            console.print("Invalid input. Please enter a number.", style="error")
                    # If we broke from save selection to go back to menu, user_input_valid might be false
                    # This will cause the main menu to re-display.
                    if not user_input_valid: # Ensure we break the outer input loop if returning to menu
                        break

                elif action["type"] == "quit":
                    console.print("Exiting. Goodbye!", style="bold green")
                    sys.exit(0) # Clean exit
            else:
                console.print(f"Invalid choice '{choice_str}'. Please select a valid number from the menu.", style="error")
        # If game_loop finished or resume was chosen, the outer while True in main_menu will re-display the menu.


if __name__ == "__main__":
    main_menu() # Call the main menu

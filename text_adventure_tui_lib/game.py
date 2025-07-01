import os
import re
import sys
import json
from pathlib import Path
import datetime

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.theme import Theme

from .data_structures import GameState, Player
from .event_manager import EventManager
from .yaml_loader import load_story_and_player
from .game_state_manager import GameStateManager

# --- Configuration ---
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

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi4:latest")
DEBUG_MODE_ENABLED = False
SAVE_DIR_NAME = ".text_adventure_tui_saves"
SAVE_GAME_PATH = Path.home() / SAVE_DIR_NAME
GAME_TITLE = "Terminal Text Adventure"

# --- Global Variables ---
ollama_client = None


# --- Helper Functions ---
def debug_print(message, style="debug", **kwargs):
    if DEBUG_MODE_ENABLED:
        console.print(message, style=style, **kwargs)


def display_title():
    console.print(
        Panel(Text(GAME_TITLE, justify="center", style="bold green on black")),
        style="green",
    )


def display_story(text_content):
    console.print(
        Panel(
            Text(text_content, style="story"),
            title="Story",
            border_style="info",
            padding=(1, 2),
        )
    )


# --- Core Game Logic ---
def get_llm_story_continuation(
    current_narrative: str, player_choice: str, instructions: list[str]
) -> str:
    prompt = (
        f"You are a storyteller for a text adventure game.\n"
        f"Current situation: '{current_narrative}'\n"
        f"The player chose to: '{player_choice}'.\n"
        f"Important context:\n- {'\n- '.join(instructions)}\n"
        f"Continue the story concisely (1-3 paragraphs)."
    )
    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        console.print(f"Error getting story continuation: {e}", style="danger")
        return "The story path is unclear..."


def get_llm_options(current_narrative: str) -> list[str]:
    prompt = (
        f"You are an assistant for a text adventure game.\n"
        f"Current situation: '{current_narrative}'\n"
        f"Provide 4 distinct, actionable choices for the player, starting with a verb.\n"
        f"Format as a numbered list (e.g., 1. Choice)."
    )
    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}]
        )
        raw_text = response["message"]["content"].strip()
        return [
            match.group(1).strip()
            for match in re.finditer(r"^\s*\d+\s*[\.\)]\s*(.*)", raw_text, re.MULTILINE)
        ]
    except Exception as e:
        console.print(f"Error getting options: {e}", style="danger")
        return ["Look around.", "Check inventory.", "Wait.", "Leave."]


def get_player_choice(
    choices: list[str],
    added_choices: list[dict],
    game_state_manager: GameStateManager,
    event_manager: EventManager,
) -> str:
    all_choices = choices + [c["label"] for c in added_choices]

    while True:
        console.print("\nChoose your action:", style="prompt")
        for i, choice in enumerate(all_choices, 1):
            console.print(f"{i}. [choice]{choice}[/choice]")

        user_input = Prompt.ask("Enter choice number or command").strip().lower()

        if user_input.startswith("/"):
            handle_command(user_input, game_state_manager, event_manager)
            continue

        if user_input.isdigit() and 1 <= int(user_input) <= len(all_choices):
            chosen_index = int(user_input) - 1
            if chosen_index < len(choices):
                return all_choices[chosen_index]
            else:
                action = added_choices[chosen_index - len(choices)]["action"]
                if action.startswith("trigger:"):
                    event_id = action.split(":")[1]
                    event_manager.execute_event_actions(
                        event_id, game_state_manager, []
                    )
                    return "EVENT_TRIGGERED"
                else:
                    return action

        console.print("Invalid choice.", style="error")


def handle_command(
    command: str, game_state_manager: GameStateManager, event_manager: EventManager
):
    parts = command.split()
    cmd = parts[0]

    if cmd == "/save":
        save_game_state(game_state_manager, event_manager)
    elif cmd == "/debug":
        debug_print(f"State: {game_state_manager.game_state}", "info")
    elif cmd == "/force_event" and len(parts) > 1:
        event_manager.execute_event_actions(parts[1], game_state_manager, [])
    elif cmd == "/quit":
        raise SystemExit("Exiting game.")


def save_game_state(game_state_manager: GameStateManager, event_manager: EventManager):
    SAVE_GAME_PATH.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{game_state_manager.get_story().id}_{timestamp}.json"
    save_file_path = SAVE_GAME_PATH / filename

    with open(save_file_path, "w") as f:
        save_data = {
            "game_state": game_state_manager.game_state,
            "event_manager_state": event_manager.get_state(),
        }
        json.dump(save_data, f, indent=4, default=lambda o: o.__dict__)
    console.print(f"Game saved as '{filename}'", style="bold green")


def game_loop(story_name: str, saved_state=None):
    display_title()

    stories_path = Path(__file__).parent / "story_parts"

    if saved_state:
        story, player = load_story_and_player(story_name, stories_path)
        game_state = GameState(
            current_story=story,
            player=player,
            flags=saved_state["game_state"]["flags"],
            turn_count=saved_state["game_state"]["turn_count"],
        )
        event_manager = EventManager(story.events, console)
        event_manager.load_state(saved_state["event_manager_state"])
        game_state_manager = GameStateManager(game_state)
    else:
        story, player = load_story_and_player(story_name, stories_path)
        game_state = GameState(
            current_story=story,
            player=player,
        )
        event_manager = EventManager(story.events, console)
        game_state_manager = GameStateManager(game_state)
        event_manager.execute_event_actions("story_start", game_state_manager, [])

    narrative = game_state_manager.get_flags().get(
        "override_narrative", "The story begins..."
    )

    while True:
        console.print(f"\n--- Turn {game_state.turn_count} ---", style="bold magenta")
        display_story(narrative)

        llm_instructions = []
        event_results = event_manager.check_and_trigger_events(
            game_state_manager, "", llm_instructions
        )

        if event_results.get("override_narrative"):
            narrative = event_results["override_narrative"]

        for text in event_results.get("injected_narratives_pre", []):
            display_story(text)

        choices = get_llm_options(narrative)
        added_choices = event_results.get("added_choices", [])
        player_choice = get_player_choice(
            choices, added_choices, game_state_manager, event_manager
        )

        if player_choice == "EVENT_TRIGGERED":
            narrative = game_state_manager.get_flags().get(
                "override_narrative", narrative
            )
            continue

        console.print(f"\nYou chose: [italic choice]{player_choice}[/italic choice]")

        event_results = event_manager.check_and_trigger_events(
            game_state_manager, player_choice, llm_instructions
        )

        if event_results.get("override_narrative"):
            narrative = event_results["override_narrative"]
        else:
            narrative = get_llm_story_continuation(
                narrative, player_choice, llm_instructions
            )

        for text in event_results.get("injected_narratives_post", []):
            display_story(text)

        game_state.turn_count += 1


def main_menu():
    global DEBUG_MODE_ENABLED, ollama_client
    try:
        ollama_client = ollama.Client(host=OLLAMA_HOST)
    except Exception as e:
        console.print(f"Ollama client init failed: {e}", style="error")
        sys.exit(1)

    while True:
        display_title()
        console.print("1. Start New Game (Whispers of the Salted Crypt)")
        console.print("2. Resume Game")
        console.print("3. Toggle Debug")
        console.print("4. Quit")

        choice = Prompt.ask("Choose an option").strip()

        if choice == "1":
            game_loop("Whispers_of_the_Salted_Crypt")
        elif choice == "2":
            saves = sorted(
                SAVE_GAME_PATH.glob("*.json"), key=os.path.getmtime, reverse=True
            )
            if not saves:
                console.print("No saves found.", "warning")
                continue
            for i, s in enumerate(saves):
                console.print(f"{i + 1}. {s.name}")
            save_choice = Prompt.ask("Select a save").strip()
            if save_choice.isdigit() and 1 <= int(save_choice) <= len(saves):
                with open(saves[int(save_choice) - 1], "r") as f:
                    saved_data = json.load(f)
                game_loop(saved_data["game_state"]["current_story"]["id"], saved_data)
        elif choice == "3":
            DEBUG_MODE_ENABLED = not DEBUG_MODE_ENABLED
            console.print(
                f"Debug mode is now {'ON' if DEBUG_MODE_ENABLED else 'OFF'}", "info"
            )
        elif choice == "4":
            break


if __name__ == "__main__":
    main_menu()

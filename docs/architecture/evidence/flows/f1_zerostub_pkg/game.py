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
from .story_manager import StoryManager

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
        f"This is the current situation: '{current_narrative}'.\n"
        f"The player chose to: '{player_choice}'.\n"
        f"Describe the immediate outcome of this action. Do not advance the story beyond this single action.\n"
        f"Keep it brief and focused on the result of the choice."
    )
    if instructions:
        prompt += f"\nImportant context to consider:\n- {'\n- '.join(instructions)}"

    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.5},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        console.print(f"Error getting story continuation: {e}", style="danger")
        return "The path forward is hazy..."


def get_player_intent(player_input: str, game_state_manager: GameStateManager) -> str:
    """
    Uses an LLM to determine the player's underlying intent from their action.
    """
    narrative_context = "The player is in a text-based adventure game."
    prompt = (
        f"Analyze the player's action and classify it into a single, concise intent keyword.\n"
        f"The context is: {narrative_context}\n"
        f"Player's action: '{player_input}'\n"
        f"Possible intents include, but are not limited to: 'search_desk', 'read_journal', 'go_to_bluffs', 'attack', 'flee', 'talk_to_npc', 'use_item'.\n"
        f"Respond with only the single intent keyword (e.g., 'search_desk')."
    )
    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        intent = response["message"]["content"].strip().lower().replace(" ", "_")
        debug_print(f"Player intent classified as: '{intent}'", "info")
        return intent
    except Exception as e:
        console.print(f"Error getting player intent: {e}", style="danger")
        return "unknown_intent"

def get_llm_options(current_narrative: str, game_state_manager: GameStateManager) -> tuple[str, list[str]]:
    player_stats = game_state_manager.get_stats()
    inventory = game_state_manager.get_inventory()
    location = game_state_manager.get_current_location()

    prompt = (
        f"You are the narrator for a text adventure game. Your job is to describe the current scene and provide clear choices for the player.\n\n"
        f"**Current Situation:**\n{current_narrative}\n\n"
        f"**Player Status:**\n- Location: {location}\n- Health: {player_stats.get('health', 'N/A')}\n- Inventory: {', '.join(inventory) if inventory else 'Empty'}\n\n"
        f"**Instructions:**\n"
        f"1.  Write a brief, one-paragraph summary of the current scene to remind the player what's happening. This will be the main narrative text.\n"
        f"2.  Then, provide exactly 4 distinct, actionable choices for the player. Each choice must start with a verb.\n"
        f"3.  Format your entire response as a single JSON object with two keys: 'narrative_summary' (a string) and 'choices' (a list of strings).\n\n"
        f"Example Response:\n"
        f'{{"narrative_summary": "You are standing at the edge of a dark forest, the wind whispering through the trees. A narrow path leads deeper into the woods, and an old, gnarled tree seems to watch you with silent judgment.", "choices": ["Enter the forest path.", "Examine the gnarled tree.", "Search the area for other paths.", "Rest for a moment."]}}'
    )

    try:
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},
            format="json",
        )
        raw_json_str = response["message"]["content"].strip()

        # Basic cleanup for common LLM formatting mistakes
        cleaned_json_str = raw_json_str.replace("```json", "").replace("```", "").strip()

        data = json.loads(cleaned_json_str)

        narrative_summary = data.get("narrative_summary", current_narrative)
        choices = data.get("choices", [])

        if not choices or len(choices) > 4:
             raise ValueError("LLM returned an invalid number of choices.")

        return narrative_summary, choices

    except Exception as e:
        console.print(f"Error getting LLM options: {e}", style="danger")
        console.print(f"LLM Raw Response was: {raw_json_str}", style="debug")
        # Fallback to a generic set of options
        return current_narrative, ["Look around.", "Check inventory.", "Wait.", "Leave."]


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
                return all_choices[chosen_index], None
            else:
                action = added_choices[chosen_index - len(choices)]["action"]
                if action.startswith("trigger:"):
                    event_id = action.split(":")[1]
                    return "EVENT_TRIGGERED", event_id
                else:
                    return action, None

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
        # Load game from save
        story, player = load_story_and_player(story_name, stories_path)
        game_state = GameState(
            current_story=story,
            player=player,
            flags=saved_state["game_state"]["flags"],
            turn_count=saved_state["game_state"]["turn_count"],
            current_location=saved_state["game_state"]["current_location"],
            turns_in_location=saved_state["game_state"]["turns_in_location"],
        )
        game_state_manager = GameStateManager(game_state)
        event_manager = EventManager(story.events, console)
        event_manager.load_state(saved_state["event_manager_state"])
        narrative = saved_state.get("narrative", "Your story continues...")
    else:
        # Start a new game
        story, player = load_story_and_player(story_name, stories_path)
        game_state = GameState(
            current_story=story, 
            player=player,
            current_location=story.starting_location
        )
        game_state_manager = GameStateManager(game_state)
        event_manager = EventManager(story.events, console)
        
        # Get the intro text from the story definition
        intro_part_path = stories_path / story.initial_story_part
        try:
            with open(intro_part_path, "r") as f:
                narrative = f.read()
        except FileNotFoundError:
            narrative = "The story begins..."
        
        # Trigger the story_start event manually
        story_start_results = event_manager.execute_event_actions("story_start", game_state_manager, [])
        if story_start_results.get("override_narrative"):
            narrative = story_start_results["override_narrative"]

    while True:
        console.rule(f"Turn {game_state_manager.get_turn_count()}", style="bold magenta")

        # --- 1. Get Scene Description and Choices from LLM ---
        narrative, choices = get_llm_options(narrative, game_state_manager)
        display_story(narrative)

        # --- 2. Check for pre-choice events (e.g., location-based triggers) ---
        llm_instructions = []
        event_results = event_manager.check_and_trigger_events(
            game_state_manager, "", llm_instructions
        )

        # Display pre-narrative injections from events
        for text in event_results.get("injected_narratives_pre", []):
            display_story(text)

        # --- 3. Get Player's Choice ---
        added_choices = event_results.get("added_choices", [])
        player_choice, event_to_trigger = get_player_choice(
            choices, added_choices, game_state_manager, event_manager
        )

        # If the choice triggers a specific event, handle it and restart the loop
        if player_choice == "EVENT_TRIGGERED":
            event_results = event_manager.execute_event_actions(
                event_to_trigger, game_state_manager, llm_instructions
            )
            # Update narrative if the event overrides it, otherwise keep current
            narrative = event_results.get("override_narrative", narrative)
            continue

        # --- 4. Process Player's Choice ---
        console.print(f"\n> You chose: [italic choice]{player_choice}[/italic choice]")

        # Check for events triggered by the player's action
        player_intent = get_player_intent(player_choice, game_state_manager)
        event_results = event_manager.check_and_trigger_events(
            game_state_manager, player_choice, llm_instructions, player_intent
        )

        # If an event overrides the narrative, it takes precedence
        if event_results.get("override_narrative"):
            narrative = event_results["override_narrative"]
        else:
            # Otherwise, get the outcome of the action from the LLM
            action_outcome = get_llm_story_continuation(
                narrative, player_choice, llm_instructions
            )
            # The outcome becomes the starting point for the next turn's narrative
            narrative = action_outcome
            display_story(action_outcome)

        # Display post-narrative injections from events
        for text in event_results.get("injected_narratives_post", []):
            display_story(text)

        # --- 5. Check for Game End Conditions ---
        if game_state_manager.get_flags().get("game_ended", False):
            console.print("\n" + "="*50, style="bold magenta")
            if game_state_manager.get_flags().get("game_ended_success", False):
                console.print("🎉 STORY COMPLETED SUCCESSFULLY! 🎉", style="bold green")
            else:
                console.print("💀 STORY ENDED 💀", style="bold red")
            console.print("="*50, style="bold magenta")
            
            console.print("\nThank you for playing!", style="info")
            input("\nPress Enter to return to the main menu...")
            break

        # --- 6. Advance Game State ---
        game_state_manager.increment_turn()
        game_state_manager.increment_turns_in_location()
        
        # Check for story checkpoints
        current_turn = game_state_manager.get_turn_count()
        for checkpoint in story.checkpoints:
            if checkpoint.get("turn") == current_turn:
                if checkpoint.get("prompt_injection"):
                    llm_instructions.append(checkpoint["prompt_injection"])
                if checkpoint.get("force_end_game"):
                    # Handle checkpoint ending
                    end_message = "The story reaches its conclusion."
                    flag_messages = checkpoint.get("flag_messages", [])
                    for flag_msg in flag_messages:
                        flag_name = flag_msg.get("flag")
                        if game_state_manager.get_flags().get(flag_name, False):
                            if flag_msg.get("message_if_set"):
                                end_message = flag_msg["message_if_set"]
                                break
                        else:
                            if flag_msg.get("message_if_not_set"):
                                end_message = flag_msg["message_if_not_set"]
                                break
                    
                    display_story(end_message)
                    console.print("\n" + "="*50, style="bold magenta")
                    console.print("📖 STORY CONCLUDED 📖", style="bold cyan")
                    console.print("="*50, style="bold magenta")
                    console.print("\nThank you for playing!", style="info")
                    input("\nPress Enter to return to the main menu...")
                    return


def main_menu():
    global DEBUG_MODE_ENABLED, ollama_client
    try:
        ollama_client = ollama.Client(host=OLLAMA_HOST)
    except Exception as e:
        console.print(f"Ollama client init failed: {e}", style="error")
        sys.exit(1)

    # Initialize story manager
    stories_path = Path(__file__).parent / "story_parts"
    events_path = Path(__file__).parent / "events"
    story_manager = StoryManager(stories_path, events_path)

    while True:
        display_title()
        
        # Discover available stories
        available_stories = story_manager.discover_stories()
        
        if available_stories:
            console.print("Available Stories:", style="bold cyan")
            for i, story in enumerate(available_stories, 1):
                difficulty_color = {
                    "beginner": "green",
                    "medium": "yellow", 
                    "hard": "red",
                    "expert": "bold red"
                }.get(story.difficulty, "white")
                
                console.print(f"{i}. [bold]{story.title}[/bold] by {story.author}")
                console.print(f"   [{difficulty_color}]{story.difficulty.title()}[/{difficulty_color}] • ~{story.total_turns_estimate} turns")
                if story.tags:
                    console.print(f"   Tags: {', '.join(story.tags)}")
                console.print(f"   {story.description[:100]}{'...' if len(story.description) > 100 else ''}")
                console.print()
            
            console.print(f"{len(available_stories) + 1}. Resume Game")
            console.print(f"{len(available_stories) + 2}. Toggle Debug Output ({'ON' if DEBUG_MODE_ENABLED else 'OFF'})")
            console.print(f"{len(available_stories) + 3}. Quit")
        else:
            console.print("No stories found!", style="error")
            console.print("1. Toggle Debug Output")
            console.print("2. Quit")

        choice = Prompt.ask("Choose an option").strip()

        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_stories):
                selected_story = available_stories[choice_num - 1]
                console.print(f"\nStarting: [bold]{selected_story.title}[/bold]")
                if selected_story.content_warnings:
                    console.print(f"Content warnings: {', '.join(selected_story.content_warnings)}", style="warning")
                    if not Prompt.ask("Continue? (y/n)", default="y").lower().startswith('y'):
                        continue
                game_loop(selected_story.id)
            elif choice_num == len(available_stories) + 1:
                # Resume Game
                saves = sorted(
                    SAVE_GAME_PATH.glob("*.json"), key=os.path.getmtime, reverse=True
                )
                if not saves:
                    console.print("No saves found.", style="warning")
                    continue
                console.print("\nAvailable saves:")
                for i, s in enumerate(saves):
                    console.print(f"{i + 1}. {s.name}")
                save_choice = Prompt.ask("Select a save").strip()
                if save_choice.isdigit() and 1 <= int(save_choice) <= len(saves):
                    with open(saves[int(save_choice) - 1], "r") as f:
                        saved_data = json.load(f)
                    game_loop(saved_data["game_state"]["current_story"]["id"], saved_data)
            elif choice_num == len(available_stories) + 2:
                # Toggle Debug
                DEBUG_MODE_ENABLED = not DEBUG_MODE_ENABLED
                console.print(
                    f"Debug mode is now {'ON' if DEBUG_MODE_ENABLED else 'OFF'}", style="info"
                )
            elif choice_num == len(available_stories) + 3:
                # Quit
                break
        else:
            console.print("Invalid choice.", style="error")


if __name__ == "__main__":
    main_menu()

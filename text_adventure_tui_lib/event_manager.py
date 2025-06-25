import importlib.resources
import yaml
from rich.console import Console

# Removed console = Console() here, will be passed in.

class EventManager:
    def __init__(self, event_files_config, console_instance):
        """
        Initializes the EventManager.
        event_files_config: A list of tuples, where each tuple is (package_path, file_name).
                            Example: [("text_adventure_tui_lib.events", "general_events.yaml")]
        console_instance: An instance of rich.console.Console.
        """
        self.events = {}
        self.triggered_event_ids = set() # To track events for options: {once: true}
        self.console = console_instance # Use the passed-in console

        for package_path, file_name in event_files_config:
            self._load_events_from_file(package_path, file_name)

    def _load_events_from_file(self, package_path, file_name):
        """Loads and parses a single YAML event file."""
        try:
            yaml_content = importlib.resources.read_text(package_path, file_name)
            loaded_data = yaml.safe_load(yaml_content)
            if loaded_data: # Ensure file is not empty
                for event_data in loaded_data:
                    if "id" in event_data:
                        if event_data["id"] in self.events:
                            self.console.print(f"Warning: Duplicate event ID '{event_data['id']}' found in '{file_name}'. Overwriting.", style="warning")
                        self.events[event_data["id"]] = event_data
                        # self.console.print(f"DEBUG: Loaded event '{event_data['id']}'.", style="dim blue")
                    else:
                        self.console.print(f"Warning: Event data in '{file_name}' missing 'id'. Skipping.", style="warning")
            self.console.print(f"DEBUG: Successfully loaded events from '{package_path}/{file_name}'. Found {len(loaded_data if loaded_data else [])} event(s).", style="debug")

        except FileNotFoundError:
            self.console.print(f"Error: Event file '{file_name}' not found in package '{package_path}'.", style="danger")
        except yaml.YAMLError as e:
            self.console.print(f"Error parsing YAML in event file '{file_name}': {e}", style="danger")
        except Exception as e:
            self.console.print(f"Unexpected error loading event file '{file_name}': {e}", style="danger")

    def check_and_trigger_events(self, game_state, player_input_text, current_story_segment, llm_prompt_instructions):
        """
        Checks all events and triggers any whose conditions are met.
        Returns a dictionary with potential 'override_narrative' and 'modified_prompt_instructions'.
        """
        triggered_override_narrative = None
        # llm_prompt_instructions will be populated by 'modify_prompt' actions

        # Sort events by priority if defined, higher numbers first. Default to 0 if not specified.
        # For now, not implementing priority, just iterating.
        # sorted_event_ids = sorted(self.events.keys(), key=lambda k: self.events[k].get('options', {}).get('priority', 0), reverse=True)

        for event_id, event_data in self.events.items():
            if event_data.get("options", {}).get("once", False) and event_id in self.triggered_event_ids:
                continue # Skip already triggered 'once' events

            trigger_config = event_data.get("trigger")
            if not trigger_config:
                continue

            if self._evaluate_trigger(trigger_config, game_state, player_input_text):
                self.console.print(f"DEBUG: Event '{event_id}' triggered!", style="green")
                # Execute actions
                for action in event_data.get("actions", []):
                    action_type = action.get("type")
                    action_value = action.get("value")

                    if action_type == "set_flag":
                        game_state["flags"][action_value] = True
                        self.console.print(f"DEBUG: Action set_flag: '{action_value}' = True", style="debug")
                    elif action_type == "override_narrative":
                        triggered_override_narrative = action.get("text", "")
                        self.console.print(f"DEBUG: Action override_narrative: '{triggered_override_narrative[:50]}...'", style="debug")
                    elif action_type == "modify_prompt":
                        instruction = action.get("instruction", "")
                        if instruction:
                            llm_prompt_instructions.append(instruction) # Append to the list passed in
                            self.console.print(f"DEBUG: Action modify_prompt: '{instruction[:50]}...'", style="debug")
                    # Add more actions here as they are implemented (e.g., add_item, change_location)

                if event_data.get("options", {}).get("once", False):
                    self.triggered_event_ids.add(event_id)

                # If an event with override_narrative triggers, we might want to stop processing further events for this turn
                # depending on game design. For now, let's assume only one override_narrative per turn is expected if multiple events trigger.
                if triggered_override_narrative is not None:
                    break

        return {
            "override_narrative": triggered_override_narrative,
            "modified_prompt_instructions": llm_prompt_instructions
        }

    def _evaluate_trigger(self, trigger_config, game_state, player_input_text):
        """Evaluates if the trigger conditions are met."""
        conditions = trigger_config.get("conditions", [])
        mode = trigger_config.get("mode", "AND").upper()

        if not conditions:
            return False # No conditions means no trigger

        results = []
        for condition in conditions:
            condition_type = condition.get("type")
            condition_value = condition.get("value")
            # operator = condition.get("operator", "==") # For future numeric comparisons

            met = False
            if condition_type == "location":
                met = game_state.get("current_location") == condition_value
            elif condition_type == "flag_set":
                met = game_state.get("flags", {}).get(condition_value, False)
            elif condition_type == "flag_not_set":
                met = not game_state.get("flags", {}).get(condition_value, False)
            # Add more condition types here: turn_count, inventory_has, player_action (keyword/intent)
            # Example for player_action (simple keyword spotting):
            # elif condition_type == "player_action_keyword":
            #     keywords = condition.get("keywords", [])
            #     met = any(keyword.lower() in player_input_text.lower() for keyword in keywords)

            results.append(met)

        if mode == "AND":
            return all(results)
        elif mode == "OR":
            return any(results)
        return False


if __name__ == '__main__':
    # Example Usage (for testing EventManager independently)
    # This requires the file structure to be accessible, e.g., running from project root.
    # Adjust package_path as needed if running this directly for tests.

    # To make this testable, we'd need to ensure text_adventure_tui_lib is in PYTHONPATH
    # or run as `python -m text_adventure_tui_lib.event_manager`
    # For now, this __main__ block is more for conceptual testing.

    # Need a console instance for standalone testing
    standalone_console = Console() # Or create one with the theme if desired for test output
    standalone_console.print("Testing EventManager standalone...", style="bold yellow")
    # Assuming text_adventure_tui_lib.events.general_events.yaml exists
    # and text_adventure_tui_lib is in the Python path
    try:
        event_files = [("text_adventure_tui_lib.events", "general_events.yaml")]
        manager = EventManager(event_files, console_instance=standalone_console)
        standalone_console.print(f"Loaded {len(manager.events)} events.", style="info")
        for event_id, event_details in manager.events.items():
            standalone_console.print(f"Event ID: {event_id}, Name: {event_details.get('name', 'N/A')}", style="info")

        # Dummy game_state for conceptual testing
        dummy_game_state = {
            'flags': {},
            'current_location': 'eldoria_town_square',
            'inventory': []
        }
        dummy_input = "look around"
        dummy_story_segment = "You are standing."
        dummy_instructions = []

        results = manager.check_and_trigger_events(dummy_game_state, dummy_input, dummy_story_segment, dummy_instructions)
        console.print(f"check_and_trigger_events results: {results}", style="info")

    except Exception as e:
        console.print(f"Error during standalone EventManager test: {e}", style="bold red")

# Example game_state structure (will be initialized in game.py)
# game_state = {
#     'flags': {}, # e.g., {'met_hermit': True, 'found_key': False}
#     'current_location': 'start_area', # A string identifier
#     'inventory': [], # List of item IDs or objects
#     'player_stats': {'health': 100, 'mana': 50}, # Example
#     # Potentially other dynamic state variables
# }

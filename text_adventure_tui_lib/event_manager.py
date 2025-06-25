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
        self.event_files_config = event_files_config # Store for re-initialization if needed, or state saving

        for package_path, file_name in event_files_config:
            self._load_events_from_file(package_path, file_name)

    def get_state(self):
        """Returns the serializable state of the EventManager."""
        return {
            "triggered_event_ids": list(self.triggered_event_ids) # Convert set to list for JSON
        }

    def load_state(self, state_data):
        """Loads the state of the EventManager from a dictionary."""
        self.triggered_event_ids = set(state_data.get("triggered_event_ids", []))
        # Events themselves are reloaded from files based on initial config,
        # so we don't need to save/load the self.events dictionary if it's static post-init.
        # If events could be dynamically added/removed during gameplay and need saving,
        # this would need to be more complex. For now, only triggered_event_ids are dynamic.
        # This debug message should use the game's debug_print, but EventManager doesn't have access to it.
        # For now, let EventManager print its own debugs, or pass the debug_print function.
        # To keep it simple, EventManager's internal debugs will always show if console is used.
        # Or, we can make EventManager accept DEBUG_MODE_ENABLED.
        # Let's assume for now its internal debugs are okay, or rely on game.py to debug its calls.
        # The console.print here is about state *loading*, which is a significant event.
        if self.console: # Check if console was passed
            self.console.print(f"DEBUG: EventManager state loaded. Triggered IDs: {self.triggered_event_ids}", style="debug")


    def execute_event_actions(self, event_id, game_state, llm_prompt_instructions):
        """
        Manually executes the actions of a specific event, bypassing its triggers.
        This is primarily for debugging.
        Returns similar results to check_and_trigger_events for consistency if needed,
        though override_narrative might be less meaningful here.
        """
        event_data = self.events.get(event_id)
        if not event_data:
            self.console.print(f"DEBUG: Event '{event_id}' not found for force execution.", style="warning")
            return {}

        self.console.print(f"DEBUG: Forcing execution of actions for event '{event_id}'!", style="bold magenta")

        # Similar structure to check_and_trigger_events action loop
        # Initialize results specific to this forced execution
        forced_override_narrative = None
        forced_injected_pre = []
        forced_injected_post = []
        # llm_prompt_instructions is passed in and can be modified directly

        for action in event_data.get("actions", []):
            action_type = action.get("type")
            action_value = action.get("value") # For simple value actions

            # Re-using the action logic from check_and_trigger_events
            if action_type == "set_flag":
                game_state["flags"][action_value] = True
                self.console.print(f"DEBUG (force): Action set_flag: '{action_value}' = True", style="debug")
            elif action_type == "clear_flag":
                if action_value in game_state["flags"]:
                    del game_state["flags"][action_value]
                    self.console.print(f"DEBUG (force): Action clear_flag: '{action_value}'", style="debug")
            elif action_type == "add_item":
                if "inventory" not in game_state: game_state["inventory"] = []
                game_state["inventory"].append(action_value)
                self.console.print(f"DEBUG (force): Action add_item: '{action_value}' to inventory.", style="debug")
            elif action_type == "remove_item":
                if "inventory" in game_state and action_value in game_state["inventory"]:
                    game_state["inventory"].remove(action_value)
                    self.console.print(f"DEBUG (force): Action remove_item: '{action_value}' from inventory.", style="debug")
            elif action_type == "change_location":
                old_location = game_state.get("current_location")
                game_state["current_location"] = action_value
                game_state["__location_changed_by_event"] = True # Signal for location_turn_count reset
                self.console.print(f"DEBUG (force): Action change_location: from '{old_location}' to '{action_value}'", style="debug")
            elif action_type == "update_stat":
                stat_name = action.get("stat")
                change_by = action.get("change_by")
                if "player_stats" not in game_state: game_state["player_stats"] = {}
                if stat_name and isinstance(change_by, int):
                    game_state["player_stats"][stat_name] = game_state["player_stats"].get(stat_name, 0) + change_by
                    self.console.print(f"DEBUG (force): Action update_stat: '{stat_name}' by {change_by}", style="debug")
            elif action_type == "override_narrative":
                forced_override_narrative = action.get("text", "")
                self.console.print(f"DEBUG (force): Action override_narrative captured: '{forced_override_narrative[:50]}...'", style="debug")
            elif action_type == "modify_prompt":
                instruction = action.get("instruction", "")
                if instruction:
                    llm_prompt_instructions.append(instruction)
                    self.console.print(f"DEBUG (force): Action modify_prompt: '{instruction[:50]}...'", style="debug")
            elif action_type == "inject_narrative":
                text_to_inject = action.get("text", "")
                position = action.get("position", "post").lower()
                if position == "pre": forced_injected_pre.append(text_to_inject)
                else: forced_injected_post.append(text_to_inject)
                self.console.print(f"DEBUG (force): Action inject_narrative ({position}) captured: '{text_to_inject[:50]}...'", style="debug")

        # Unlike normal trigger, don't add to triggered_event_ids for 'once' events here,
        # as this is a manual override for testing actions.
        # If we wanted /force_trigger, that would be a separate command/logic.

        return {
            "override_narrative": forced_override_narrative, # Caller (game.py) will decide what to do with this
            "modified_prompt_instructions": llm_prompt_instructions, # Modified in place
            "injected_narratives_pre": forced_injected_pre,
            "injected_narratives_post": forced_injected_post,
        }

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
        injected_narratives_pre = []  # For text injected before LLM output
        injected_narratives_post = [] # For text injected after LLM output
        # llm_prompt_instructions is already passed in and modified by 'modify_prompt'

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
                    elif action_type == "clear_flag":
                        if action_value in game_state["flags"]:
                            del game_state["flags"][action_value]
                            self.console.print(f"DEBUG: Action clear_flag: '{action_value}'", style="debug")
                    elif action_type == "add_item":
                        if "inventory" not in game_state: game_state["inventory"] = []
                        game_state["inventory"].append(action_value)
                        self.console.print(f"DEBUG: Action add_item: '{action_value}' to inventory.", style="debug")
                    elif action_type == "remove_item":
                        if "inventory" in game_state and action_value in game_state["inventory"]:
                            game_state["inventory"].remove(action_value)
                            self.console.print(f"DEBUG: Action remove_item: '{action_value}' from inventory.", style="debug")
                        else:
                            self.console.print(f"DEBUG: Action remove_item: '{action_value}' not found in inventory.", style="dim blue")
                    elif action_type == "change_location":
                        old_location = game_state.get("current_location")
                        game_state["current_location"] = action_value
                        # Signal to game.py that location_turn_count should be reset
                        game_state["__location_changed_by_event"] = True
                        self.console.print(f"DEBUG: Action change_location: from '{old_location}' to '{action_value}'", style="debug")
                    elif action_type == "update_stat":
                        stat_name = action.get("stat")
                        change_by = action.get("change_by") # Can be positive or negative integer
                        if "player_stats" not in game_state: game_state["player_stats"] = {}
                        if stat_name and isinstance(change_by, int):
                            game_state["player_stats"][stat_name] = game_state["player_stats"].get(stat_name, 0) + change_by
                            self.console.print(f"DEBUG: Action update_stat: '{stat_name}' changed by {change_by}, new value: {game_state['player_stats'][stat_name]}", style="debug")
                    elif action_type == "inject_narrative":
                        text_to_inject = action.get("text", "")
                        position = action.get("position", "post").lower() # "pre" or "post"
                        if position == "pre":
                            injected_narratives_pre.append(text_to_inject)
                        else: # Default to post
                            injected_narratives_post.append(text_to_inject)
                        self.console.print(f"DEBUG: Action inject_narrative ({position}): '{text_to_inject[:50]}...'", style="debug")
                    # Add more actions here as they are implemented

                if event_data.get("options", {}).get("once", False):
                    self.triggered_event_ids.add(event_id)

                # If an event with override_narrative triggers, we might want to stop processing further events for this turn
                # depending on game design. For now, let's assume only one override_narrative per turn is expected if multiple events trigger.
                if triggered_override_narrative is not None:
                    break

        return {
            "override_narrative": triggered_override_narrative,
            "modified_prompt_instructions": llm_prompt_instructions,
            "injected_narratives_pre": injected_narratives_pre,
            "injected_narratives_post": injected_narratives_post,
            # game_state is modified in-place, no need to return it unless we change that paradigm
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
            elif condition_type == "player_action_keyword":
                # Value is expected to be a list of keywords
                keywords = condition.get("keywords", []) if isinstance(condition.get("keywords"), list) else [condition.get("keywords")]
                if player_input_text: # Ensure player_input_text is not None
                    met = any(str(keyword).lower() in player_input_text.lower() for keyword in keywords)
                else:
                    met = False
            elif condition_type == "inventory_has":
                # Value is the item_id to check
                met = condition_value in game_state.get("inventory", [])
            elif condition_type == "inventory_not_has":
                met = condition_value not in game_state.get("inventory", [])
            elif condition_type == "turn_count_global":
                # Value is the turn number to check, operator specifies comparison
                op = condition.get("operator", "==")
                target_turn = int(condition_value)
                current_turn = game_state.get("turn_counter", 0)
                if op == "==": met = current_turn == target_turn
                elif op == ">=": met = current_turn >= target_turn
                elif op == "<=": met = current_turn <= target_turn
                elif op == ">": met = current_turn > target_turn
                elif op == "<": met = current_turn < target_turn
                else: met = False # Unknown operator
            elif condition_type == "turn_count_in_location":
                # Value is turn number, operator for comparison
                # Assumes game_state['location_turn_count'] is managed by game.py
                op = condition.get("operator", "==")
                target_turn = int(condition_value)
                # Check if the condition specifies a location, otherwise use current.
                # This allows checking turns in a *specific* location, not just current.
                # However, game_state.location_turn_count is for *current* loc.
                # For simplicity, this trigger will only work for the *current* location's turn count.
                # A more complex setup would need location_specific_turn_counts in game_state.
                loc_to_check = condition.get("location_context", game_state.get("current_location"))
                if loc_to_check == game_state.get("current_location"): # Only applies if current location matches
                    current_loc_turn = game_state.get("location_turn_count", 0)
                    if op == "==": met = current_loc_turn == target_turn
                    elif op == ">=": met = current_loc_turn >= target_turn
                    elif op == "<=": met = current_loc_turn <= target_turn
                    elif op == ">": met = current_loc_turn > target_turn
                    elif op == "<": met = current_loc_turn < target_turn
                    else: met = False
                else: # Condition is for a different location than current
                    met = False


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

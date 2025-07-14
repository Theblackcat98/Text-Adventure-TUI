from rich.console import Console
from .data_structures import Event
from .game_state_manager import GameStateManager


class EventManager:
    def __init__(self, events: list[Event], console_instance: Console):
        self.events = {event.id: event for event in events}
        self.triggered_event_ids = set()
        self.console = console_instance

    def get_state(self):
        return {"triggered_event_ids": list(self.triggered_event_ids)}

    def load_state(self, state_data):
        self.triggered_event_ids = set(state_data.get("triggered_event_ids", []))

    def execute_event_actions(
        self,
        event_id: str,
        game_state_manager: GameStateManager,
        llm_prompt_instructions: list[str],
    ):
        event = self.events.get(event_id)
        if not event:
            self.console.print(
                f"DEBUG: Event '{event_id}' not found for force execution.",
                style="warning",
            )
            return {}

        self.console.print(
            f"DEBUG: Forcing execution of actions for event '{event_id}'!",
            style="bold magenta",
        )
        return self._perform_actions(event, game_state_manager, llm_prompt_instructions)

    def check_and_trigger_events(
        self,
        game_state_manager: GameStateManager,
        player_input_text: str,
        llm_prompt_instructions: list[str],
    ):
        triggered_override_narrative = None
        injected_narratives_pre = []
        injected_narratives_post = []
        added_choices = []

        for event_id, event in self.events.items():
            if (
                event.options.get("once", False)
                and event_id in self.triggered_event_ids
            ):
                continue

            if self._evaluate_trigger(
                event.trigger, game_state_manager, player_input_text
            ):
                self.console.print(
                    f"DEBUG: Event '{event_id}' triggered!", style="green"
                )
                results = self._perform_actions(
                    event, game_state_manager, llm_prompt_instructions
                )

                if results.get("override_narrative") is not None:
                    triggered_override_narrative = results["override_narrative"]
                injected_narratives_pre.extend(
                    results.get("injected_narratives_pre", [])
                )
                injected_narratives_post.extend(
                    results.get("injected_narratives_post", [])
                )
                added_choices.extend(results.get("added_choices", []))

                if event.options.get("once", False):
                    self.triggered_event_ids.add(event_id)

                if triggered_override_narrative is not None:
                    break

        return {
            "override_narrative": triggered_override_narrative,
            "modified_prompt_instructions": llm_prompt_instructions,
            "injected_narratives_pre": injected_narratives_pre,
            "injected_narratives_post": injected_narratives_post,
            "added_choices": added_choices,
        }

    def _perform_actions(
        self,
        event: Event,
        game_state_manager: GameStateManager,
        llm_prompt_instructions: list[str],
    ):
        override_narrative = None
        injected_pre = []
        injected_post = []
        added_choices = []

        for action in event.actions:
            action_type = action.get("type")
            action_value = action.get("value")

            if action_type == "set_flag":
                game_state_manager.set_flag(action_value)
            elif action_type == "clear_flag":
                game_state_manager.clear_flag(action_value)
            elif action_type == "add_item":
                game_state_manager.add_item(action.get("item_id"))
            elif action_type == "remove_item":
                game_state_manager.remove_item(action_value)
            elif action_type == "change_location":
                game_state_manager.set_current_location(action_value)
            elif action_type == "update_stat":
                stat_name = action.get("stat")
                change_by = action.get("change_by")
                current_value = game_state_manager.get_stats().get(stat_name, 0)
                game_state_manager.update_stat(stat_name, current_value + change_by)
            elif action_type == "override_narrative":
                override_narrative = action.get("text", "")
            elif action_type == "modify_prompt":
                llm_prompt_instructions.append(action.get("instruction", ""))
            elif action_type == "inject_narrative":
                text_to_inject = action.get("text", "")
                position = action.get("position", "post").lower()
                if position == "pre":
                    injected_pre.append(text_to_inject)
                else:
                    injected_post.append(text_to_inject)
            elif action_type == "add_choice":
                added_choices.append(action)
            elif action_type == "present_choices":
                added_choices.extend(action.get("choices", []))

        return {
            "override_narrative": override_narrative,
            "injected_narratives_pre": injected_pre,
            "injected_narratives_post": injected_post,
            "added_choices": added_choices,
        }

    def _evaluate_trigger(
        self,
        trigger_config,
        game_state_manager: GameStateManager,
        player_input_text: str,
    ):
        conditions = trigger_config.get("conditions", [])
        mode = trigger_config.get("mode", "AND").upper()

        if mode == "MANUAL":
            return False

        if not conditions:
            return False

        results = []
        for condition in conditions:
            condition_type = condition.get("type")
            condition_value = condition.get("value")

            met = False
            if condition_type == "location":
                met = game_state_manager.get_current_location() == condition_value
            elif condition_type == "flag_set":
                met = game_state_manager.get_flags().get(condition_value, False)
            elif condition_type == "flag_not_set":
                met = not game_state_manager.get_flags().get(condition_value, False)
            elif condition_type == "player_action_keyword":
                keywords = condition.get("keywords", [])
                if player_input_text:
                    met = any(
                        str(keyword).lower() in player_input_text.lower()
                        for keyword in keywords
                    )
            elif condition_type == "player_action":
                met = player_input_text.lower() == condition_value.lower()
            elif condition_type == "player_action_keyword":
                keywords = condition.get("keywords", [])
                if player_input_text:
                    met = any(
                        str(keyword).lower() in player_input_text.lower()
                        for keyword in keywords
                    )
            elif condition_type == "inventory_has":
                met = condition.get("value") in game_state_manager.get_inventory()
            elif condition_type == "inventory_not_has":
                met = condition.get("value") not in game_state_manager.get_inventory()
            elif condition_type == "game_start":
                met = game_state_manager.game_state.turn_count == 0
            elif condition_type == "turn_count_in_location":
                operator = condition.get("operator", "==")
                target_turns = condition.get("value")
                current_turns = game_state_manager.game_state.turns_in_location
                if operator == "==":
                    met = current_turns == target_turns
                elif operator == ">=":
                    met = current_turns >= target_turns
                elif operator == "<=":
                    met = current_turns <= target_turns
                elif operator == ">":
                    met = current_turns > target_turns
                elif operator == "<":
                    met = current_turns < target_turns

            results.append(met)

        if mode == "AND":
            return all(results)
        elif mode == "OR":
            return any(results)
        return False

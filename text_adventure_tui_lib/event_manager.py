import re

from rich.console import Console
from .data_structures import Event
from .game_state_manager import GameStateManager


def _keyword_matches(keyword: str, lowered_input: str, match_mode: str) -> bool:
    """Match one keyword against lowered input.

    ``match_mode='word'`` (opt-in per condition) matches whole words only,
    so e.g. the keyword ``status`` does not fire on the word ``statue``.
    The default ``'substring'`` preserves the historical behavior.
    """
    if match_mode == "word":
        return re.search(rf"\b{re.escape(keyword)}\b", lowered_input) is not None
    return keyword in lowered_input


class EventManager:
    """Evaluates YAML-defined events against game state and executes actions.

    Execution guards live in an event's ``options`` block:

    * ``once: true`` — fires at most once per playthrough.
    * ``once_per_location: true`` — fires at most once per location, so
      location-description events re-arm when the player travels.

    The turn loop evaluates events twice per turn (a pre-choice pass with
    empty input, then the choice pass). Events are deduplicated per turn so
    input-independent events (location ambiance, restlessness, ...) fire once
    per turn instead of twice.
    """

    def __init__(self, events: list[Event], console_instance: Console):
        self.events = {event.id: event for event in events}
        self.triggered_event_ids = set()
        self.fired_event_locations = set()
        self._fired_in_turn = {}
        # Tracks every event that actually fires (including repeatable ones),
        # so the game can report "events fired vs. total" on the ending
        # screen. ``triggered_event_ids`` only grows for ``once`` events.
        self.fired_ids = set()
        self.fire_counts = {}
        self.console = console_instance

    def get_state(self):
        return {
            "triggered_event_ids": list(self.triggered_event_ids),
            "fired_event_locations": [
                [event_id, location]
                for event_id, location in sorted(self.fired_event_locations)
            ],
        }

    def load_state(self, state_data):
        self.triggered_event_ids = set(state_data.get("triggered_event_ids", []))
        self.fired_event_locations = {
            tuple(pair) for pair in state_data.get("fired_event_locations", [])
        }

    def check_and_trigger_events(
        self,
        game_state_manager: GameStateManager,
        player_input_text: str,
        llm_prompt_instructions: list[str],
        player_intent: str = "",
    ):
        triggered_override_narrative = None
        injected_narratives_pre = []
        injected_narratives_post = []
        added_choices = []
        turn_count = game_state_manager.get_turn_count()

        for event_id, event in self.events.items():
            if self._should_skip(event_id, event, game_state_manager, turn_count):
                continue

            if self._evaluate_trigger(
                event.trigger, game_state_manager, player_input_text, player_intent
            ):
                self.console.print(
                    f"DEBUG: Event '{event_id}' triggered!", style="green"
                )
                results = self._perform_actions(
                    event, game_state_manager, llm_prompt_instructions
                )

                # First override in load order wins; later events still run so
                # their state changes are never silently dropped.
                if (
                    results.get("override_narrative") is not None
                    and triggered_override_narrative is None
                ):
                    triggered_override_narrative = results["override_narrative"]
                injected_narratives_pre.extend(
                    results.get("injected_narratives_pre", [])
                )
                injected_narratives_post.extend(
                    results.get("injected_narratives_post", [])
                )
                added_choices.extend(results.get("added_choices", []))

                self._mark_fired(event_id, event, game_state_manager)

        return {
            "override_narrative": triggered_override_narrative,
            "modified_prompt_instructions": llm_prompt_instructions,
            "injected_narratives_pre": injected_narratives_pre,
            "injected_narratives_post": injected_narratives_post,
            "added_choices": added_choices,
        }

    def execute_event_actions(
        self,
        event_id: str,
        game_state_manager: GameStateManager,
        llm_prompt_instructions: list[str],
    ):
        """Execute a specific event's actions by ID.

        Used for the story's ``story_start`` event and the ``/force_event``
        debug command. Guarded events are idempotent: forcing an event that
        already fired (per its ``once`` / ``once_per_location`` guard) does
        not re-apply its state-changing actions.
        """
        empty_result = {
            "override_narrative": None,
            "modified_prompt_instructions": llm_prompt_instructions,
            "injected_narratives_pre": [],
            "injected_narratives_post": [],
            "added_choices": [],
        }
        event = self.events.get(event_id)
        if not event:
            self.console.print(
                f"DEBUG: Event '{event_id}' not found for force execution.",
                style="warning",
            )
            return empty_result

        if self._guard_already_fired(event_id, event, game_state_manager):
            self.console.print(
                f"DEBUG: Event '{event_id}' already fired here; skipping.",
                style="warning",
            )
            return empty_result

        self.console.print(
            f"DEBUG: Forcing execution of actions for event '{event_id}'!",
            style="bold magenta",
        )
        results = self._perform_actions(
            event, game_state_manager, llm_prompt_instructions
        )
        self._mark_fired(event_id, event, game_state_manager)
        return results

    def _should_skip(
        self,
        event_id: str,
        event: Event,
        game_state_manager: GameStateManager,
        turn_count: int,
    ) -> bool:
        if self._guard_already_fired(event_id, event, game_state_manager):
            return True
        return self._fired_in_turn.get(event_id) == turn_count

    def _guard_already_fired(
        self, event_id: str, event: Event, game_state_manager: GameStateManager
    ) -> bool:
        options = event.options or {}
        if options.get("once", False) and event_id in self.triggered_event_ids:
            return True
        if options.get("once_per_location", False):
            location = game_state_manager.get_current_location()
            return (event_id, location) in self.fired_event_locations
        return False

    def _mark_fired(
        self, event_id: str, event: Event, game_state_manager: GameStateManager
    ) -> None:
        options = event.options or {}
        self._fired_in_turn[event_id] = game_state_manager.get_turn_count()
        if options.get("once", False):
            self.triggered_event_ids.add(event_id)
        if options.get("once_per_location", False):
            self.fired_event_locations.add(
                (event_id, game_state_manager.get_current_location())
            )

    def _perform_actions(
        self,
        event: Event,
        game_state_manager: GameStateManager,
        llm_prompt_instructions: list[str],
    ):
        # Record the firing before running actions so force-executed and
        # auto-triggered events share one tracking path.
        self.fired_ids.add(event.id)
        self.fire_counts[event.id] = self.fire_counts.get(event.id, 0) + 1

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
                # Shipped YAML writes add_item with `value:`; also accept
                # `item_id:` for hand-written events. Skip malformed actions
                # instead of appending None to the inventory.
                item_id = action.get("value", action.get("item_id"))
                if item_id:
                    game_state_manager.add_item(item_id)
                else:
                    self.console.print(
                        "DEBUG: add_item action without 'value'/'item_id' skipped.",
                        style="warning",
                    )
            elif action_type == "remove_item":
                game_state_manager.remove_item(action_value)
            elif action_type == "change_location":
                game_state_manager.set_current_location(action_value)
            elif action_type == "update_stat":
                stat_name = action.get("stat")
                change_by = action.get("change_by")
                current_value = game_state_manager.get_stats().get(stat_name, 0)
                if not isinstance(current_value, (int, float)):
                    self.console.print(
                        f"DEBUG: stat '{stat_name}' is non-numeric; using 0.",
                        style="warning",
                    )
                    current_value = 0
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
                # Single choice addition
                choice_data = {
                    "label": action.get("label", "Unknown Choice"),
                    "action": action.get("action", "")
                }
                added_choices.append(choice_data)
            elif action_type == "present_choices":
                # Multiple choice presentation
                choices = action.get("choices", [])
                for choice in choices:
                    choice_data = {
                        "label": choice.get("label", "Unknown Choice"),
                        "action": choice.get("action", "")
                    }
                    added_choices.append(choice_data)
            elif action_type == "end_game":
                # End the game with success/failure
                success = action.get("success", True)
                message = action.get("message", "The story ends here.")
                outcome = "success" if success else "failure"
                game_state_manager.set_flag("game_ended")
                game_state_manager.set_flag(f"game_ended_{outcome}")
                override_narrative = message

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
        player_intent: str,
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
                match_mode = condition.get("match", "substring")
                if player_input_text:
                    lowered = player_input_text.lower()
                    met = any(
                        _keyword_matches(str(keyword).lower(), lowered, match_mode)
                        for keyword in keywords
                    )
            elif condition_type == "player_intent":
                met = player_intent == condition_value
            elif condition_type == "player_action":
                met = player_input_text.lower() == condition_value.lower()
            elif condition_type == "inventory_has":
                met = condition.get("value") in game_state_manager.get_inventory()
            elif condition_type == "inventory_not_has":
                met = condition.get("value") not in game_state_manager.get_inventory()
            elif condition_type == "inventory_count":
                operator = condition.get("operator", ">=")
                target = condition.get("value", 0)
                current = len(game_state_manager.get_inventory())
                if operator == "==":
                    met = current == target
                elif operator == ">=":
                    met = current >= target
                elif operator == "<=":
                    met = current <= target
                elif operator == ">":
                    met = current > target
                elif operator == "<":
                    met = current < target
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
            elif condition_type == "turn_count_global":
                operator = condition.get("operator", "==")
                target_turns = condition.get("value")
                current_turns = game_state_manager.game_state.turn_count
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
            elif condition_type == "stat_check":
                stat_name = condition.get("stat")
                operator = condition.get("operator", ">=")
                target_value = condition.get("value")
                current_value = game_state_manager.get_stats().get(stat_name, 0)
                if operator == "==":
                    met = current_value == target_value
                elif operator == ">=":
                    met = current_value >= target_value
                elif operator == "<=":
                    met = current_value <= target_value
                elif operator == ">":
                    met = current_value > target_value
                elif operator == "<":
                    met = current_value < target_value

            results.append(met)

        if mode == "AND":
            return all(results)
        elif mode == "OR":
            return any(results)
        return False

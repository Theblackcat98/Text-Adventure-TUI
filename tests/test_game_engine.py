import pytest
from pathlib import Path
from text_adventure_tui_lib.data_structures import (
    GameState,
    Player,
    Story,
    Event,
)
from text_adventure_tui_lib.yaml_loader import load_story_and_player
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console


def test_player_action_trigger():
    event = Event(
        id="test_event",
        name="Test",
        trigger={"mode": "AND", "conditions": [{"type": "player_action", "value": "search desk"}]},
        actions=[{"type": "set_flag", "value": "event_triggered"}],
        options={},
    )
    story = Story(id="test", title="Test", events=[event])
    player = Player()
    game_state = GameState(
        current_story=story,
        player=player,
    )
    gsm = GameStateManager(game_state)
    console = Console()
    event_manager = EventManager(story.events, console)

    event_manager.check_and_trigger_events(gsm, "search desk", [])

    assert gsm.get_flags().get("event_triggered")


def test_turn_count_in_location_trigger():
    """
    Test that an event with a turn count in location trigger activates when the player has spent the required number of turns in the location.
    
    Verifies that the event manager correctly evaluates the trigger condition based on turns spent in the current location and sets the appropriate flag in the game state when the condition is met.
    """
    event = Event(
        id="test_event",
        name="Test",
        trigger={"mode": "AND", "conditions": [{"type": "turn_count_in_location", "value": 3, "operator": ">="}]},
        actions=[{"type": "set_flag", "value": "event_triggered"}],
        options={},
    )
    story = Story(id="test", title="Test", events=[event])
    player = Player()
    game_state = GameState(
        current_story=story,
        player=player,
        turns_in_location=3
    )
    gsm = GameStateManager(game_state)
    console = Console()
    event_manager = EventManager(story.events, console)

    event_manager.check_and_trigger_events(gsm, "", [])

    assert gsm.get_flags().get("event_triggered")


def test_add_choice_action():
    event = Event(
        id="test_event",
        name="Test",
        trigger={"mode": "AND", "conditions": [{"type": "location", "value": "start"}]},
        actions=[{"type": "add_choice", "label": "New Choice", "action": "trigger:new_event"}],
        options={},
    )
    story = Story(id="test", title="Test", events=[event])
    player = Player()
    game_state = GameState(
        current_story=story,
        player=player,
    )
    game_state.flags["current_location"] = "start"
    gsm = GameStateManager(game_state)
    console = Console()
    event_manager = EventManager(story.events, console)

    results = event_manager.check_and_trigger_events(gsm, "", [])

    assert len(results["added_choices"]) == 1
    assert results["added_choices"][0]["label"] == "New Choice"
    assert results["added_choices"][0]["action"] == "trigger:new_event"

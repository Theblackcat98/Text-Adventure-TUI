import pytest
from pathlib import Path
from text_adventure_tui_lib.data_structures import (
    GameState,
    Player,
    Story,
    Event,
)
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.event_manager import EventManager
from rich.console import Console


def test_player_action_keyword_trigger():
    event = Event(
        id="test_event",
        name="Test",
        trigger={"mode": "AND", "conditions": [{"type": "player_action_keyword", "keywords": ["search", "desk"]}]},
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

    event_manager.check_and_trigger_events(gsm, "I want to search the desk", [])

    assert gsm.get_flags().get("event_triggered")

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


@pytest.fixture
def story_path(tmp_path: Path) -> Path:
    story_dir = tmp_path / "test_story"
    story_dir.mkdir(parents=True)

    game_setup_yaml = """
- id: story_start
  name: "Test Story"
  trigger:
    mode: MANUAL
  actions: []
  initial_player_stats:
    health: 100
  initial_inventory:
    - "a rusty key"
"""
    (story_dir / "game_setup.yaml").write_text(game_setup_yaml)

    return tmp_path


def test_load_story(story_path: Path):
    story, player = load_story_and_player("test_story", story_path)
    assert story.id == "story_start"
    assert story.title == "Test Story"
    assert len(story.events) > 0
    assert player.stats["health"] == 100
    assert "a rusty key" in player.inventory


def test_game_state_manager():
    story = Story(id="test", title="Test", events=[])
    player = Player(stats={"health": 100}, inventory=["key"])
    game_state = GameState(
        current_story=story,
        player=player,
    )
    gsm = GameStateManager(game_state)

    assert gsm.get_stats()["health"] == 100
    gsm.update_stat("health", 90)
    assert gsm.get_stats()["health"] == 90

    assert "key" in gsm.get_inventory()
    gsm.add_item("coin")
    assert "coin" in gsm.get_inventory()
    gsm.remove_item("key")
    assert "key" not in gsm.get_inventory()

    assert not gsm.get_flags().get("test_flag")
    gsm.set_flag("test_flag")
    assert gsm.get_flags().get("test_flag")
    gsm.clear_flag("test_flag")
    assert not gsm.get_flags().get("test_flag")


def test_event_manager():
    event = Event(
        id="test_event",
        name="Test",
        trigger={"mode": "AND", "conditions": [{"type": "location", "value": "start"}]},
        actions=[{"type": "set_flag", "value": "event_triggered"}],
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

    event_manager.check_and_trigger_events(gsm, "", [])

    assert gsm.get_flags().get("event_triggered")

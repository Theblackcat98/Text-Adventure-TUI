import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .data_structures import Story, Event, Player


def _load_yaml(file_path: Path) -> Any:
    """Loads a YAML file from the given path."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def _create_events_from_data(event_data: List[Dict[str, Any]]) -> List[Event]:
    """Creates a list of Event objects from raw event data."""
    events = []
    if not event_data:
        return events
    for data in event_data:
        events.append(
            Event(
                id=data["id"],
                name=data.get("name", ""),
                trigger=data.get("trigger", {}),
                actions=data.get("actions", []),
                options=data.get("options", {}),
            )
        )
    return events


def load_story_and_player(story_name: str, stories_path: Path) -> Tuple[Story, Player]:
    """
    Loads all story components from YAML files and returns a complete Story object
    and the initial Player object.
    """
    story_path = stories_path / story_name

    all_events = []
    for yaml_file in story_path.glob("*.yaml"):
        events_data = _load_yaml(yaml_file)
        if events_data:
            all_events.extend(events_data)

    if not all_events:
        raise ValueError(f"No events found for story '{story_name}'.")

    try:
        setup_info = next(e for e in all_events if e["id"] == "story_start")
    except StopIteration:
        raise ValueError(
            f"Could not find 'story_start' event in any YAML file for '{story_name}'."
        )

    player = Player(
        stats=setup_info.get("initial_player_stats", {}),
        inventory=setup_info.get("initial_inventory", []),
    )

    story_id = setup_info["id"]
    story_title = setup_info.get("title", setup_info.get("name", "Untitled Story"))

    events = _create_events_from_data(all_events)

    story = Story(id=story_id, title=story_title, events=events)

    return story, player

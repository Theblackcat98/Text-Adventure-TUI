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
    Loads story components from story arc YAML and events YAML files.
    Returns a complete Story object and the initial Player object.
    """
    # First, try to load the story arc file
    story_arc_file = stories_path / f"{story_name}_story_arc.yaml"
    story_arc_data = None
    
    if story_arc_file.exists():
        story_arc_data = _load_yaml(story_arc_file)
    else:
        # Fallback to old format for backward compatibility
        return _load_story_old_format(story_name, stories_path)
    
    # Load events from the events directory
    events_path = stories_path.parent / "events"
    all_events = []
    
    # Load general events
    general_events_file = events_path / "general_events.yaml"
    if general_events_file.exists():
        general_events_data = _load_yaml(general_events_file)
        if general_events_data:
            all_events.extend(general_events_data)
    
    # Load story-specific events
    story_events_file = events_path / f"{story_name}_story_events.yaml"
    if story_events_file.exists():
        story_events_data = _load_yaml(story_events_file)
        if story_events_data:
            all_events.extend(story_events_data)
    
    # Create player from story arc data
    player = Player(
        stats=story_arc_data.get("initial_player_stats", {}),
        inventory=story_arc_data.get("initial_inventory", []),
    )
    
    # Create story object
    story_title = story_arc_data.get("title", "Untitled Story")
    events = _create_events_from_data(all_events)
    
    story = Story(
        id=story_name, 
        title=story_title, 
        events=events
    )
    
    # Add story arc data to story object for reference
    story.starting_location = story_arc_data.get("starting_location", "start")
    story.initial_story_part = story_arc_data.get("initial_story_part", "01_intro.txt")
    story.total_turns_estimate = story_arc_data.get("total_turns_estimate", 20)
    story.description = story_arc_data.get("description", "")
    story.checkpoints = story_arc_data.get("checkpoints", [])
    story.tags = story_arc_data.get("tags", [])
    story.difficulty = story_arc_data.get("difficulty", "medium")
    story.content_warnings = story_arc_data.get("content_warnings", [])
    story.author = story_arc_data.get("author", "Unknown")
    story.version = story_arc_data.get("version", "1.0")
    
    return story, player


def _load_story_old_format(story_name: str, stories_path: Path) -> Tuple[Story, Player]:
    """
    Fallback loader for the old story format (for backward compatibility).
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
    
    # Set default values for new story arc fields
    story.starting_location = "start"
    story.initial_story_part = "01_intro.txt"
    story.total_turns_estimate = 20
    story.description = ""
    story.checkpoints = []
    story.tags = []
    story.difficulty = "medium"
    story.content_warnings = []
    story.author = "Unknown"
    story.version = "1.0"

    return story, player

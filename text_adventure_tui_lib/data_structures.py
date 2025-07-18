from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Player:
    stats: Dict[str, Any] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)


@dataclass
class Event:
    id: str
    name: str
    trigger: Dict[str, Any]
    actions: List[Dict[str, Any]]
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Story:
    id: str
    title: str
    events: List[Event] = field(default_factory=list)
    # Story arc metadata
    starting_location: str = "start"
    initial_story_part: str = "01_intro.txt"
    total_turns_estimate: int = 20
    description: str = ""
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    content_warnings: List[str] = field(default_factory=list)
    author: str = "Unknown"
    version: str = "1.0"


@dataclass
class GameState:
    current_story: Story
    player: Player
    flags: Dict[str, bool] = field(default_factory=dict)
    turn_count: int = 0
    current_location: str = "start"
    turns_in_location: int = 0

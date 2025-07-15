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


@dataclass
class GameState:
    current_story: Story
    player: Player
    flags: Dict[str, bool] = field(default_factory=dict)
    turn_count: int = 0
    current_location: str = "start"
    turns_in_location: int = 0

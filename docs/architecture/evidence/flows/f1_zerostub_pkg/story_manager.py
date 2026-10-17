"""
Story management utilities for discovering, validating, and managing stories.
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .data_structures import Story
from .yaml_loader import load_story_and_player


@dataclass
class StoryInfo:
    """Metadata about a story for display in menus."""
    id: str
    title: str
    description: str
    author: str
    difficulty: str
    tags: List[str]
    content_warnings: List[str]
    total_turns_estimate: int
    version: str


@dataclass
class ValidationResult:
    """Result of story validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class StoryManager:
    """Manages story discovery, validation, and metadata."""
    
    def __init__(self, stories_path: Path, events_path: Path):
        self.stories_path = stories_path
        self.events_path = events_path
    
    def discover_stories(self) -> List[StoryInfo]:
        """Discover all available stories by scanning for story arc files."""
        stories = []
        
        # Look for story arc files
        for story_arc_file in self.stories_path.glob("*_story_arc.yaml"):
            try:
                with open(story_arc_file, 'r') as f:
                    story_data = yaml.safe_load(f)
                
                # Extract story ID from filename
                story_id = story_arc_file.stem.replace("_story_arc", "")
                
                story_info = StoryInfo(
                    id=story_id,
                    title=story_data.get("title", "Untitled Story"),
                    description=story_data.get("description", "No description available."),
                    author=story_data.get("author", "Unknown"),
                    difficulty=story_data.get("difficulty", "medium"),
                    tags=story_data.get("tags", []),
                    content_warnings=story_data.get("content_warnings", []),
                    total_turns_estimate=story_data.get("total_turns_estimate", 20),
                    version=story_data.get("version", "1.0")
                )
                stories.append(story_info)
                
            except Exception as e:
                print(f"Warning: Could not load story arc {story_arc_file}: {e}")
                continue
        
        return sorted(stories, key=lambda s: s.title)
    
    def validate_story(self, story_id: str) -> ValidationResult:
        """Validate a story's structure and content."""
        errors = []
        warnings = []
        
        # Check if story arc file exists
        story_arc_file = self.stories_path / f"{story_id}_story_arc.yaml"
        if not story_arc_file.exists():
            errors.append(f"Story arc file not found: {story_arc_file}")
            return ValidationResult(False, errors, warnings)
        
        try:
            # Load and validate story arc
            with open(story_arc_file, 'r') as f:
                story_arc_data = yaml.safe_load(f)
            
            # Required fields
            required_fields = ["title", "starting_location"]
            for field in required_fields:
                if field not in story_arc_data:
                    errors.append(f"Missing required field in story arc: {field}")
            
            # Check if initial story part exists
            initial_story_part = story_arc_data.get("initial_story_part", "01_intro.txt")
            story_part_file = self.stories_path / initial_story_part
            if not story_part_file.exists():
                warnings.append(f"Initial story part file not found: {story_part_file}")
            
            # Check if events file exists
            events_file = self.events_path / f"{story_id}_story_events.yaml"
            if not events_file.exists():
                warnings.append(f"Story events file not found: {events_file}")
            else:
                # Validate events structure
                try:
                    with open(events_file, 'r') as f:
                        events_data = yaml.safe_load(f)
                    
                    if not isinstance(events_data, list):
                        errors.append("Events file must contain a list of events")
                    else:
                        # Check for story_start event
                        has_story_start = any(
                            event.get("id") == "story_start" 
                            for event in events_data 
                            if isinstance(event, dict)
                        )
                        if not has_story_start:
                            errors.append("Events file must contain a 'story_start' event")
                        
                        # Validate individual events
                        for i, event in enumerate(events_data):
                            if not isinstance(event, dict):
                                errors.append(f"Event {i} is not a dictionary")
                                continue
                            
                            if "id" not in event:
                                errors.append(f"Event {i} missing required 'id' field")
                            
                            if "trigger" not in event:
                                warnings.append(f"Event {event.get('id', i)} missing 'trigger' field")
                            
                            if "actions" not in event:
                                warnings.append(f"Event {event.get('id', i)} missing 'actions' field")
                
                except yaml.YAMLError as e:
                    errors.append(f"Invalid YAML in events file: {e}")
            
            # Try to actually load the story
            try:
                story, player = load_story_and_player(story_id, self.stories_path)
            except Exception as e:
                errors.append(f"Failed to load story: {e}")
        
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in story arc file: {e}")
        except Exception as e:
            errors.append(f"Unexpected error validating story: {e}")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def create_story_template(self, story_id: str, title: str, author: str = "Unknown") -> None:
        """Create template files for a new story."""
        # Create story arc file
        story_arc_data = {
            "title": title,
            "starting_location": "start",
            "initial_story_part": f"{story_id}_intro.txt",
            "total_turns_estimate": 20,
            "initial_inventory": [],
            "initial_player_stats": {
                "health": 100
            },
            "description": f"A new adventure: {title}",
            "checkpoints": [
                {
                    "turn": 20,
                    "force_end_game": True,
                    "prompt_injection": "The story reaches its natural conclusion.",
                    "flag_messages": [
                        {
                            "flag": "success",
                            "message_if_set": "You have succeeded in your quest!",
                            "message_if_not_set": "Your adventure ends, but perhaps not as you hoped."
                        }
                    ]
                }
            ],
            "tags": ["adventure"],
            "difficulty": "medium",
            "content_warnings": [],
            "author": author,
            "version": "1.0"
        }
        
        story_arc_file = self.stories_path / f"{story_id}_story_arc.yaml"
        with open(story_arc_file, 'w') as f:
            yaml.dump(story_arc_data, f, default_flow_style=False, sort_keys=False)
        
        # Create intro text file
        intro_text = f"""Welcome to {title}!

This is the beginning of your adventure. You find yourself in a new and mysterious place, 
ready to embark on an epic journey. What will you discover? What challenges await?

The story begins now..."""
        
        intro_file = self.stories_path / f"{story_id}_intro.txt"
        with open(intro_file, 'w') as f:
            f.write(intro_text)
        
        # Create events file
        events_data = [
            {
                "id": "story_start",
                "name": f"Beginning of {title}",
                "trigger": {
                    "mode": "MANUAL",
                    "conditions": [{"type": "game_start"}]
                },
                "actions": [
                    {"type": "change_location", "value": "start"},
                    {
                        "type": "override_narrative",
                        "text": f"Welcome to {title}! Your adventure begins here."
                    },
                    {
                        "type": "modify_prompt",
                        "instruction": "The player is starting a new adventure. Present them with interesting choices to begin their journey."
                    }
                ]
            },
            {
                "id": "example_event",
                "name": "Example Event",
                "options": {"once": True},
                "trigger": {
                    "mode": "AND",
                    "conditions": [
                        {"type": "location", "value": "start"},
                        {"type": "player_action_keyword", "keywords": ["look around", "examine"]}
                    ]
                },
                "actions": [
                    {"type": "set_flag", "value": "looked_around"},
                    {
                        "type": "inject_narrative",
                        "text": "You notice something interesting about your surroundings...",
                        "position": "post"
                    }
                ]
            }
        ]
        
        events_file = self.events_path / f"{story_id}_story_events.yaml"
        with open(events_file, 'w') as f:
            yaml.dump(events_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"Created story template for '{title}' (ID: {story_id})")
        print(f"Files created:")
        print(f"  - {story_arc_file}")
        print(f"  - {intro_file}")
        print(f"  - {events_file}")
    
    def get_story_info(self, story_id: str) -> Optional[StoryInfo]:
        """Get detailed information about a specific story."""
        stories = self.discover_stories()
        for story in stories:
            if story.id == story_id:
                return story
        return None
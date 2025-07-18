#!/usr/bin/env python3
"""
Story management CLI tool for Text Adventure TUI.
"""
import argparse
import sys
from pathlib import Path
from text_adventure_tui_lib.story_manager import StoryManager


def main():
    parser = argparse.ArgumentParser(description="Text Adventure TUI Story Management Tool")
    parser.add_argument("--stories-path", type=Path, 
                       default=Path("text_adventure_tui_lib/story_parts"),
                       help="Path to stories directory")
    parser.add_argument("--events-path", type=Path,
                       default=Path("text_adventure_tui_lib/events"),
                       help="Path to events directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all available stories")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate stories")
    validate_parser.add_argument("story_id", nargs="?", help="Specific story to validate")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new story template")
    create_parser.add_argument("story_id", help="Story ID (used for filenames)")
    create_parser.add_argument("title", help="Story title")
    create_parser.add_argument("--author", default="Unknown", help="Story author")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show detailed story information")
    info_parser.add_argument("story_id", help="Story ID to show info for")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize story manager
    manager = StoryManager(args.stories_path, args.events_path)
    
    if args.command == "list":
        stories = manager.discover_stories()
        if not stories:
            print("No stories found.")
            return
        
        print("Available Stories:")
        print("=" * 50)
        for story in stories:
            print(f"📖 {story.title}")
            print(f"   ID: {story.id}")
            print(f"   Author: {story.author}")
            print(f"   Difficulty: {story.difficulty}")
            print(f"   Tags: {', '.join(story.tags) if story.tags else 'None'}")
            print(f"   Estimated turns: {story.total_turns_estimate}")
            if story.content_warnings:
                print(f"   Content warnings: {', '.join(story.content_warnings)}")
            print(f"   Description: {story.description}")
            print()
    
    elif args.command == "validate":
        if args.story_id:
            # Validate specific story
            result = manager.validate_story(args.story_id)
            print(f"Validating story: {args.story_id}")
            print("=" * 50)
            if result.is_valid:
                print("✅ Story is valid!")
            else:
                print("❌ Story has errors:")
                for error in result.errors:
                    print(f"   • {error}")
            
            if result.warnings:
                print("⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"   • {warning}")
        else:
            # Validate all stories
            stories = manager.discover_stories()
            if not stories:
                print("No stories found to validate.")
                return
            
            print("Validating all stories...")
            print("=" * 50)
            all_valid = True
            for story in stories:
                result = manager.validate_story(story.id)
                status = "✅" if result.is_valid else "❌"
                print(f"{status} {story.title} ({story.id})")
                
                if not result.is_valid:
                    all_valid = False
                    for error in result.errors:
                        print(f"     Error: {error}")
                
                if result.warnings:
                    for warning in result.warnings:
                        print(f"     Warning: {warning}")
            
            print()
            if all_valid:
                print("🎉 All stories are valid!")
            else:
                print("⚠️  Some stories have validation errors.")
                sys.exit(1)
    
    elif args.command == "create":
        try:
            manager.create_story_template(args.story_id, args.title, args.author)
            print(f"✅ Created story template: {args.title}")
            print(f"   Story ID: {args.story_id}")
            print(f"   Author: {args.author}")
            print()
            print("Next steps:")
            print(f"1. Edit the story arc file: {args.stories_path}/{args.story_id}_story_arc.yaml")
            print(f"2. Edit the events file: {args.events_path}/{args.story_id}_story_events.yaml")
            print(f"3. Edit the intro file: {args.stories_path}/{args.story_id}_intro.txt")
            print("4. Run 'python story_tool.py validate' to check your story")
        except Exception as e:
            print(f"❌ Error creating story template: {e}")
            sys.exit(1)
    
    elif args.command == "info":
        story_info = manager.get_story_info(args.story_id)
        if not story_info:
            print(f"❌ Story '{args.story_id}' not found.")
            sys.exit(1)
        
        print(f"Story Information: {story_info.title}")
        print("=" * 50)
        print(f"ID: {story_info.id}")
        print(f"Author: {story_info.author}")
        print(f"Version: {story_info.version}")
        print(f"Difficulty: {story_info.difficulty}")
        print(f"Estimated turns: {story_info.total_turns_estimate}")
        print(f"Tags: {', '.join(story_info.tags) if story_info.tags else 'None'}")
        if story_info.content_warnings:
            print(f"Content warnings: {', '.join(story_info.content_warnings)}")
        print()
        print("Description:")
        print(story_info.description)
        print()
        
        # Show validation status
        result = manager.validate_story(args.story_id)
        if result.is_valid:
            print("✅ Story validation: PASSED")
        else:
            print("❌ Story validation: FAILED")
            for error in result.errors:
                print(f"   • {error}")
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"   • {warning}")


if __name__ == "__main__":
    main()
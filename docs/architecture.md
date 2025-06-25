# Architecture Overview

This document provides an overview of the technical architecture of the Terminal Text Adventure game.

## Core Components

1.  **Game Engine (`game.py`)**:
    *   This is the central script that orchestrates the game.
    *   **Responsibilities**:
        *   Initializing the game environment (console, theme).
        *   Displaying the game title and story segments.
        *   Managing the main game loop.
        *   Loading initial story content from `story_parts/`.
        *   Interacting with the Ollama LLM for dynamic content generation.
        *   Handling player input and choices.
        *   Managing basic error handling and fallbacks.

2.  **Ollama LLM Integration**:
    *   The game leverages an Ollama-hosted Large Language Model (LLM) to generate:
        *   **Story Continuations**: Based on the current story segment and the player's chosen action.
        *   **Player Choices**: Based on the current story segment.
    *   **Connection**: Uses the `ollama` Python library to communicate with a running Ollama instance (default: `http://localhost:11434`).
    *   **Model**: Configured to use a specific model (default: `phi4:latest`), which can be changed via the `OLLAMA_MODEL` environment variable.
    *   **Prompting**: Carefully crafted prompts are sent to the LLM to guide its responses for storytelling and choice generation. Debug logs in `game.py` show the exact prompts being used.

3.  **Story Content (`story_parts/`)**:
    *   This directory holds plain text files that serve as starting points or predefined segments of the story.
    *   `01_intro.txt` is the default initial segment loaded by the game.
    *   The system is designed to be extensible, allowing for more story files to be added.

4.  **User Interface (Rich Library)**:
    *   The `rich` Python library is used to create a more engaging and readable terminal interface.
    *   **Features Used**:
        *   `Console` for themed output.
        *   `Panel` for displaying story text and titles.
        *   `Text` for styled text.
        *   `Prompt` for handling player input securely.
        *   Custom themes for consistent styling of information, warnings, story, choices, etc.

## Game Flow

1.  **Initialization**:
    *   The game starts, displays the title.
    *   Loads the initial story segment (e.g., `story_parts/01_intro.txt`).

2.  **Main Loop**:
    *   **Display Story**: The current story segment is displayed to the player in a panel.
    *   **Generate Choices**:
        *   The current story segment is sent to the LLM.
        *   The LLM generates a list of ~4 actionable choices for the player.
        *   If the LLM fails, hardcoded fallback choices are used.
    *   **Get Player Input**:
        *   The choices are displayed to the player.
        *   The player enters the number of their chosen action or types `quit`.
    *   **Process Choice**:
        *   If `quit`, the game ends.
        *   Otherwise, the chosen action and the current story segment are sent to the LLM.
    *   **Generate Story Continuation**:
        *   The LLM generates the next part of the story based on the player's action.
        *   If the LLM fails or returns an error, the game may end or display an error message.
    *   **Update Story**: The newly generated segment becomes the current story segment.
    *   The loop repeats.

## Configuration

*   **Ollama Host**: `OLLAMA_HOST` environment variable (defaults to `http://localhost:11434`).
*   **Ollama Model**: `OLLAMA_MODEL` environment variable (defaults to `phi4:latest`).

## Future Considerations

*   **State Management**: Currently, the game is stateless between sessions. Saving/loading game state would require a persistent storage mechanism.
*   **Advanced LLM Interaction**: More sophisticated prompt engineering, error recovery, and potentially fine-tuning models could enhance the experience.
*   **Content Management**: For larger games, a more structured way to manage story arcs, character development, and world-building might be needed beyond simple text files.

## Diagram (Simplified Flow)

```
[Start] --> Display Title
           |
           v
[Load Initial Story (01_intro.txt)] --> [current_story_text]
           |
           v
+---------------------------------------+
| Game Loop:                            |
|   Display [current_story_text]        |
|           |                           |
|           v                           |
|   [LLM: Generate Choices based on current_story_text] --> [choices_list] |
|           | (Fallback: hardcoded_choices) |
|           v                           |
|   Display [choices_list]              |
|   Get [player_selected_choice]        |
|           |                           |
|           v                           |
|   IF [player_selected_choice] == "quit" THEN --> [End Game] |
|           |                           |
|           v                           |
|   [LLM: Generate Next Story based on current_story_text + player_selected_choice] --> [new_story_segment] |
|           | (Fallback: error message/end) |
|           v                           |
|   [current_story_text] = [new_story_segment] |
|   Loop to "Display [current_story_text]" |
+---------------------------------------+
```

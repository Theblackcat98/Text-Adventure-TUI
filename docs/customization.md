# Customizing Your Adventure

This guide explains how you can customize various aspects of the Terminal Text Adventure game, from the Ollama model used to the initial story prompts.

## 1. Changing the LLM Model

The game defaults to using the `phi4:latest` model with Ollama. You can switch to any other model compatible with Ollama (e.g., `llama3:latest`, `mistral:latest`) by setting the `OLLAMA_MODEL` environment variable.

**Steps:**

1.  **Pull the desired model using Ollama:**
    ```bash
    ollama pull llama3:latest
    ```
    (Replace `llama3:latest` with your chosen model)

2.  **Set the environment variable when running the game:**
    *   On Linux/macOS:
        ```bash
        export OLLAMA_MODEL="llama3:latest"
        python game.py
        ```
    *   On Windows (Command Prompt):
        ```bash
        set OLLAMA_MODEL=llama3:latest
        python game.py
        ```
    *   On Windows (PowerShell):
        ```bash
        $env:OLLAMA_MODEL="llama3:latest"
        python game.py
        ```

**Note:** Different models may have varying tones, styles, and capabilities in generating story content and choices. Experiment to find one you like!

## 2. Changing the Ollama Host

If your Ollama server is running on a different host or port than the default (`http://localhost:11434`), you can specify it using the `OLLAMA_HOST` environment variable.

**Example:**
If Ollama is running on `http://192.168.1.100:11434`:

*   On Linux/macOS:
    ```bash
    export OLLAMA_HOST="http://192.168.1.100:11434"
    python game.py
    ```
*   On Windows (Command Prompt):
    ```bash
    set OLLAMA_HOST=http://192.168.1.100:11434
    python game.py
    ```

## 3. Modifying the Initial Story Prompt

The game starts with the story provided in `story_parts/01_intro.txt`. You can change the beginning of your adventure by:

*   **Editing `story_parts/01_intro.txt`**:
    Simply open this file in a text editor and change its content to your desired starting scenario.
*   **Creating a new story file and modifying `game.py`**:
    1.  Create a new text file in the `story_parts/` directory (e.g., `my_custom_intro.txt`).
    2.  Write your desired introductory story segment in this new file.
    3.  Open `game.py` and find the line where `current_story_segment_id` is initialized:
        ```python
        current_story_segment_id = "01_intro.txt"
        ```
    4.  Change it to point to your new file:
        ```python
        current_story_segment_id = "my_custom_intro.txt"
        ```

## 4. Adjusting LLM Prompting (Advanced)

If you have some experience with prompt engineering, you can modify the prompts sent to the LLM to influence its behavior. These prompts are located within `game.py`:

*   **Story Continuation Prompt**: Found in the `get_llm_story_continuation` function.
    ```python
    prompt_content = (
        f"You are a storyteller for a text adventure game.\n"
        f"Current situation: '{current_story_segment}'\n"
        f"{player_action_text}\n\n"
        f"Continue the story from this point based on the player's choice. Keep the story segment concise (1-3 paragraphs).\n"
        f"Do not add any other text or choices, only the next part of the story."
    )
    ```
*   **Choice Generation Prompt**: Found in the `get_llm_options` function.
    ```python
    prompt_content = (
        f"You are a helpful assistant for a text adventure game.\n"
        f"The current situation is: '{current_story_segment}'\n\n"
        f"Based on this situation, provide exactly 4 distinct, actionable, and concise choices for the player.\n"
        f"Each choice should start with a verb.\n"
        f"Format the choices as a numbered list (e.g., 1. Choice A, 2. Choice B, etc.).\n"
        f"Do not add any other text before or after the choices, only the numbered list of choices."
    )
    ```

**Considerations when modifying prompts:**

*   **Clarity and Conciseness**: LLMs generally perform better with clear and direct instructions.
*   **Desired Output Format**: For choices, the prompt specifies a numbered list. If you change this, you might need to adjust the parsing logic in `get_llm_options`.
*   **Story Tone and Style**: You can add instructions to the storyteller prompt to influence the narrative style (e.g., "Tell the story in a dark fantasy setting," or "Keep the tone lighthearted").
*   **Experimentation**: Prompt engineering often requires trial and error to achieve the desired results.

## 5. Changing Fallback Choices

If the LLM fails to generate choices, the game uses a hardcoded list from `game.py`:
```python
hardcoded_choices = [
    "Fallback: Look around the room more closely.",
    "Fallback: Try to open the only door.",
    "Fallback: Check your pockets for anything useful.",
    "Fallback: Shout to see if anyone is nearby."
]
```
You can modify this list directly in `game.py` to provide different or more contextually relevant fallback options if you prefer.

---

By adjusting these settings and content, you can tailor the Terminal Text Adventure game to your preferences and create unique narrative experiences.

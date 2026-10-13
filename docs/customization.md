# Customizing Your Adventure

This guide explains how to customize the game. Remember the engine's split:

- **The LLM (Ollama) writes the story** — scene summaries, choices, and action outcomes.
- **YAML manages the state** — flags, inventory, stats, locations, and pacing.

Almost all customization is editing YAML (or environment variables for the LLM), not Python.

## 1. Changing the LLM Model

The game defaults to `phi4:latest` with Ollama. You can switch to any other model compatible
with Ollama (e.g. `llama3.1:8b`, `mistral:latest`) by setting the `OLLAMA_MODEL` environment
variable.

**Steps:**

1.  **Pull the desired model using Ollama:**
    ```bash
    ollama pull llama3.1:8b
    ```
    (Replace `llama3.1:8b` with your chosen model)

2.  **Set the environment variable when running the game:**
    *   On Linux/macOS:
        ```bash
        export OLLAMA_MODEL="llama3.1:8b"
        python -m text_adventure_tui_lib.game
        ```
    *   On Windows (Command Prompt):
        ```cmd
        set OLLAMA_MODEL=llama3.1:8b
        python -m text_adventure_tui_lib.game
        ```
    *   On Windows (PowerShell):
        ```powershell
        $env:OLLAMA_MODEL="llama3.1:8b"
        python -m text_adventure_tui_lib.game
        ```

**Important:** `game.py` reads `OLLAMA_HOST`/`OLLAMA_MODEL` at **import time**, so the variables
must be set *before* you launch the game (setting them from inside a running session has no effect).

**Note:** Different models may have varying tones, styles, and reliability at following the
JSON output format. Models that return malformed JSON will make the game fall back to the generic
choice list (see section 5). Experiment to find one you like!

## 2. Changing the Ollama Host

If your Ollama server is running on a different host or port than the default
(`http://localhost:11434`), specify it with the `OLLAMA_HOST` environment variable.

**Example:**
If Ollama is running on `http://192.168.1.100:11434`:

*   On Linux/macOS:
    ```bash
    export OLLAMA_HOST="http://192.168.1.100:11434"
    python -m text_adventure_tui_lib.game
    ```
*   On Windows (Command Prompt):
    ```cmd
    set OLLAMA_HOST=http://192.168.1.100:11434
    python -m text_adventure_tui_lib.game
    ```

## 3. Changing the Opening Story

Each story's opening text is defined by its story arc file. For example, for
`Whispers of the Salted Crypt`:

1.  Open `text_adventure_tui_lib/story_parts/whispers_of_the_salted_crypt_story_arc.yaml`
    and check `initial_story_part` (e.g. `whispers_intro.txt`).
2.  Edit that file (e.g. `text_adventure_tui_lib/story_parts/whispers_intro.txt`) to change
    the opening scene, **or** point `initial_story_part` at a new text file you create in
    `story_parts/`.

Note: the `story_start` event in the story's events file can also override the opening
narrative with its `override_narrative` action — check there too if your edit doesn't appear.

## 4. Customizing Initial State (Story Arc YAML)

The story arc file defines the *starting* state and metadata — no game logic lives here:

`text_adventure_tui_lib/story_parts/<story_name>_story_arc.yaml`
```yaml
title: "Your Story Title"
starting_location: "initial_location"     # where the player begins
initial_story_part: "intro.txt"            # opening text file name
total_turns_estimate: 20                   # shown in the menu; used with checkpoints

initial_inventory: ["item1", "item2"]      # starting inventory
initial_player_stats:                      # starting stats (visible to the LLM each turn)
  health: 100
  mana: 50

description: "Story description"           # menu description
checkpoints:                               # pacing beats (see section 6)
  - turn: 15
    prompt_injection: "Time is running short..."
  - turn: 25
    force_end_game: true
    flag_messages:
      - flag: "success"
        message_if_set: "Victory!"
        message_if_not_set: "Defeat..."
tags: ["adventure", "mystery"]
difficulty: "medium"
content_warnings: ["mild violence"]        # shown as a warning before starting
author: "Your Name"
version: "1.0"
```

## 5. Customizing Game Logic (Events YAML)

Events are the trigger→action rules that drive the story. Each story has an events file at
`text_adventure_tui_lib/events/<story_name>_story_events.yaml`:

```yaml
- id: read_journal_clue
  name: "Reading the Critical Journal Entry"
  options:
    once: true                 # optional: fires at most once per playthrough
  trigger:                     # mode: AND, OR, or MANUAL (MANUAL never auto-fires)
    mode: AND
    conditions:
      - type: player_action_keyword
        keywords: ["read journal", "open journal"]
      - type: inventory_has
        value: "elians_journal"
      - type: flag_not_set
        value: "knows_about_bluffs"
  actions:
    - type: set_flag           # remember what happened
      value: "knows_about_bluffs"
    - type: override_narrative # replace the story beat
      text: "You open the journal to the marked page..."
```

The full list of trigger types, action types, and operators is in the
[README](README.md#event-system). A common pattern: one event's action (`add_item`, `set_flag`)
becomes another event's condition (`inventory_has`, `flag_set`) — that chain is how story
progress is authored.

### General Events

`text_adventure_tui_lib/events/general_events.yaml` contains reusable events that load for
**every** story: the help command, debug info, low-health warnings, and location ambiance.
Editing it changes behavior across all stories.

## 6. Influencing the LLM from YAML

You do not need to edit Python to steer the LLM. Two mechanisms feed instructions into the
LLM prompts:

*   **`modify_prompt` actions** — appended to the instructions passed to the story-continuation
    call for the current turn:
    ```yaml
    actions:
      - type: modify_prompt
        instruction: "The atmosphere should be tense and foreboding. The player is being watched."
    ```
*   **Checkpoint `prompt_injection`** — added when `turn_count` reaches the checkpoint's turn:
    ```yaml
    checkpoints:
      - turn: 10
        prompt_injection: "Security is tightening. You need to move quickly now."
      - turn: 15
        force_end_game: true                 # ends the story at this turn...
        flag_messages:                       # ...with a message chosen by flags
          - flag: "has_temporal_gear"
            message_if_set: "You escape into the night with the Temporal Gear..."
            message_if_not_set: "Alarms blare as you flee empty-handed..."
    ```

**Considerations when using these tools:**

*   **Clarity and conciseness**: LLMs perform better with clear, direct instructions.
*   **Scope**: `modify_prompt` only affects the current turn's continuation prompt; events fire
  every turn unless gated by `once: true` or `flag_not_set` conditions.
*   **Tone and style**: instructions can set tone ("dark fantasy setting", "lighthearted") or
  bias options ("the player should look for a way to heal").

## 7. Changing LLM Fallbacks (Python)

If the scene/choices LLM call fails or returns invalid JSON, `get_llm_options()` in
`text_adventure_tui_lib/game.py` falls back to a generic list you can edit:

```python
return current_narrative, ["Look around.", "Check inventory.", "Wait.", "Leave."]
```

If the story-continuation call fails, `get_llm_story_continuation()` returns
`"The path forward is hazy..."` — also editable in the same file.

## 8. Enabling Debug Output

From the main menu, choose **"Toggle Debug Output"**. With debug on you can see:

*   Which events triggered each turn
*   LLM prompt construction
*   Flag/inventory/stat changes
*   Turn counters

In-game commands (type them at the choice prompt):

*   `/save` — save the current game (to `~/.text_adventure_tui_saves/`)
*   `/debug` — dump current game state
*   `/force_event <event_id>` — force-execute an event's actions (useful for testing YAML)
*   `/quit` — exit

Resuming saves happens from the main menu (**"Resume Game"**).

## 9. Creating New Stories

The fastest way to start a new story is the template generator:

```bash
python story_tool.py create my_story "My Amazing Adventure" --author "Your Name"
```

This creates `<my_story>_story_arc.yaml`, `<my_story>_story_events.yaml`, and
`<my_story>_intro.txt`. Then validate:

```bash
python story_tool.py validate my_story   # this story only
python story_tool.py validate            # all stories
python story_tool.py list                # list discovered stories
```

Stories are discovered automatically from `story_parts/*_story_arc.yaml`, so the new story
appears in the main menu after creation. See
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for a full step-by-step authoring tutorial.

---

By adjusting these settings and content, you can tailor the Terminal Text Adventure to your
preferences and create unique narrative experiences.

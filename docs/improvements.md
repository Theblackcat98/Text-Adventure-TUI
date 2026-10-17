# Improvement Suggestions

A user's-eye review of the current engine, followed by 10 prioritized changes.
Compiled after fixing the engine edge cases surfaced by exhaustive YAML
playthrough testing (commit `31e2eb2`).

## User review

**Does it work?** Yes — after the engine fixes, both shipped stories run
end-to-end. The menu, resume, `/save`, `/debug`, `/force_event`, checkpoint
endings, and story validation all function. The remaining failure mode is
Ollama going down mid-session, which degrades to generic choices instead of
crashing.

**Is it fun?** Not yet, and the reason is design rather than engine quality.
Players can only pick numbered choices or type a `/command`. Story events
listen for phrases like `"search desk"`, but the choices each turn are whatever
the LLM happens to generate — often "Investigate the cluttered desk" (no
substring match) or generic "Look around." Progress through the authored YAML
therefore becomes a **keyword lottery**: when the LLM's phrasing drifts from
the authored keywords, the story stalls into a guessing game. The in-game help
text even says "Type your actions naturally (e.g., 'look around', 'take the
key')" — which is false today and makes the frustration worse.

**Replayability?** Low. Two stories of 15–25 turns each, essentially one
authored path with a couple of cosmetic forks, no fail states, no randomness,
nothing that carries between runs, and an ending that is just "return to menu."

## Suggestions (priority order)

### 1. Accept free-text actions at the prompt
Route anything the player types through the same intent/keyword event pass the
LLM choices already go through. The pass exists (`check_and_trigger_events`
with the choice text and a classified intent); only `get_player_choice` rejects
non-digit input today. This is the single highest-impact change: it removes the
keyword lottery and makes every YAML story playable as authored. It also makes
the help text true. Cost: one branch in `get_player_choice` plus keeping the
current numbered-choice path.

### 2. Feed the LLM the story's own vocabulary
Include the keywords/intents of reachable-but-unfired events in the
`get_llm_options` prompt so generated choices are guaranteed actionable (e.g.
"include one choice about searching the desk"). This doubles as a built-in hint
system with no new YAML syntax, and it stops the LLM from proposing choices the
story cannot respond to.

### 3. Make the inventory warning actionable (`/drop`, `/use`)
`inventory_full_warning` tells the player "You'll need to drop something
first," but there is no way to drop or use an item. Add `/drop <item>` and
`/use <item>` commands in `handle_command`; the engine's inventory actions
(`remove_item`) already support the consequences.

### 4. LLM-offline resilience
When the Ollama call fails, fall back to the events' `added_choices` (authored
YAML) before the generic `["Look around.", ...]` list, and show a banner like
"LLM offline — authored choices only." Stories stay playable and demoable
without a server, and the failure is honest instead of silent.

### 5. Persistent status HUD
Show location, turn number, health/stats, and inventory above every story
panel. Players currently cannot see their inventory without `/debug`, yet
`inventory_has` gates exist that they cannot reason about.

### 6. Real ending screen
At story end, show: turns taken, events fired vs. total, items held, flags
earned, and the checkpoint outcome message; persist a per-story "completed"
marker. Nearly free to build from `EventManager.fired_ids` + `story.events`,
and it makes finishing feel like finishing.

### 7. Consequences and fail states
Nothing damages health today, which is why the general `low_health_warning`
event is dead content and why choices have no cost. Add hazard events in YAML
(`update_stat` plus `end_game: success: false`). The engine already supports
all of it; the stories just haven't used it. Real failure states make each run
matter.

### 8. Save management
Saves are raw timestamped dumps in `~/.text_adventure_tui_saves/`, listed flat
in the resume menu. Group them by story, newest first, allow deletion, and
auto-save each turn into a single per-story "resume" slot so players never
manage files by hand.

### 9. Ship the test harness as a dev tool
`tests/yaml_sim.py` already plays any story offline through the real engine.
Expose it via `story_tool.py play <story>`: walk every keyword path, report
which events fire and which are dead. Authoring stories without replaying them
is how the `add_item` key-mismatch bug shipped in the first place; a dry-run
tool would catch that class of bug at authoring time.

### 10. Sources of variety for replay
Even small hooks work: seeded per-run variation (e.g. an arc field selecting
from alternate event sets), difficulty stat multipliers, or simply a third
story. A "which clue do you find first" shuffle beats a fixed chain for repeated
play. Pair with #7 so that different runs genuinely diverge.

## Suggested order of work

1 and 2 are a pair and change the game's core loop — do them together.
3 and 4 are small quality fixes. 5 and 6 are the cheapest "feels finished"
wins. 7 is content work but unlocks `low_health_warning` and gives weight to
choices. 8, 9, and 10 are about retention and authoring health.

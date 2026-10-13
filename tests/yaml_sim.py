"""Shared harness for LLM-free testing of the YAML-driven game state.

These helpers drive the real engine components (``EventManager``,
``GameStateManager``, ``yaml_loader``) exactly the way ``game.py`` drives them
during a turn, minus the LLM calls: the LLM only ever produces prose and
choice labels, so the entire state machine can be simulated deterministically.
"""

from rich.console import Console
from rich.theme import Theme
from pathlib import Path
from collections import deque

from text_adventure_tui_lib.data_structures import GameState, Player, Story, Event
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

STORIES_PATH = (
    Path(__file__).resolve().parent.parent / "text_adventure_tui_lib" / "story_parts"
)

WHISPERS = "whispers_of_the_salted_crypt"
CLOCKWORK = "the_clockwork_heist"


class TrackingEventManager(EventManager):
    """EventManager that records every event that actually fires.

    ``triggered_event_ids`` only ever grows for ``once: true`` events, so it
    cannot answer "did this event fire?" for repeatable events. This subclass
    hooks ``_perform_actions`` (the single execution path for both auto-trigger
    and forced execution) to record firings.
    """

    def __init__(self, events, console_instance):
        super().__init__(events, console_instance)
        self.fired_ids = set()
        self.fire_counts = {}

    def _perform_actions(self, event, game_state_manager, llm_prompt_instructions):
        self.fired_ids.add(event.id)
        self.fire_counts[event.id] = self.fire_counts.get(event.id, 0) + 1
        return super()._perform_actions(
            event, game_state_manager, llm_prompt_instructions
        )


def quiet_console() -> Console:
    """A console that swallows output but accepts game.py's theme styles."""
    theme = Theme(
        {
            "info": "dim cyan",
            "warning": "magenta",
            "danger": "bold red",
            "story": "white",
            "prompt": "cyan",
            "choice": "yellow",
            "debug": "dim blue",
            "error": "bold red",
        }
    )
    return Console(theme=theme, quiet=True)


def normalize_intent(action: str) -> str:
    """Mirror of game.py's ``get_player_intent`` post-processing (LLM call removed)."""
    return action.strip().lower().replace(" ", "_")


def make_event(event_id, trigger=None, actions=None, options=None) -> Event:
    """Convenience constructor for synthetic events."""
    return Event(
        id=event_id,
        name=event_id,
        trigger=trigger if trigger is not None else {},
        actions=list(actions or []),
        options=dict(options or {}),
    )


class SimulatedGame:
    """A headless playthrough of a story using the real engine components.

    ``step(action)`` mirrors one turn of ``game.py``'s loop:

    1. pre-choice event pass with empty player input (input "" is falsy, so
       keyword events cannot fire here — same as the real loop),
    2. choice/intent event pass with the action text and a normalized intent,
    3. end-of-turn counter advancement (unless the game already ended).
    """

    def __init__(
        self,
        story_name=None,
        events=None,
        stats=None,
        inventory=None,
        location="start",
        turn_count=0,
        turns_in_location=0,
        run_story_start=False,
    ):
        if story_name is not None:
            self.story, self.player = load_story_and_player(story_name, STORIES_PATH)
        else:
            self.story = Story(
                id="synthetic",
                title="Synthetic",
                events=list(events or []),
            )
            self.player = Player(
                stats=dict(stats or {}),
                inventory=list(inventory or []),
            )
        self.events = self.story.events
        self.state = GameState(
            current_story=self.story,
            player=Player(
                stats=dict(self.player.stats),
                inventory=list(self.player.inventory),
            ),
            flags={},
            turn_count=turn_count,
            current_location=(
                self.story.starting_location
                if story_name is not None
                else location
            ),
            turns_in_location=turns_in_location,
        )
        self.gsm = GameStateManager(self.state)
        self.em = TrackingEventManager(self.events, quiet_console())
        self.fired = set()
        self.instructions = []
        if story_name is not None and run_story_start:
            self.force("story_start")

    # -- actions -----------------------------------------------------------

    def force(self, event_id):
        """Equivalent of the /force_event command (and game.py's story_start)."""
        results = self.em.execute_event_actions(event_id, self.gsm, self.instructions)
        self.fired |= set(self.em.fired_ids)
        return results

    def step(self, action, intent=None):
        """Run one simulated turn for the given player action text."""
        if intent is None:
            intent = normalize_intent(action)
        self.instructions = []
        pre = self.em.check_and_trigger_events(self.gsm, "", self.instructions)
        main = self.em.check_and_trigger_events(
            self.gsm, action, self.instructions, intent
        )
        self.fired |= set(self.em.fired_ids)
        if not self.gsm.get_flags().get("game_ended", False):
            self.gsm.increment_turn()
            self.gsm.increment_turns_in_location()
        return pre, main

    # -- introspection -----------------------------------------------------

    def flags(self):
        return {k: v for k, v in self.gsm.get_flags().items() if v}

    def inventory(self):
        return list(self.gsm.get_inventory())

    def stats(self):
        return dict(self.gsm.get_stats())

    def location(self):
        return self.gsm.get_current_location()

    def signature(self):
        """Hashable state signature used to dedupe the exhaustive explorer."""
        return (
            frozenset(self.flags()),
            tuple(sorted(str(i) for i in self.inventory())),
            self.location(),
            self.gsm.get_turn_count(),
            self.gsm.game_state.turns_in_location,
            frozenset(self.em.triggered_event_ids),
            tuple(sorted((k, str(v)) for k, v in self.stats().items())),
        )

    def clone(self):
        """Return an independent copy of this game, sharing only the story data."""
        new = object.__new__(SimulatedGame)
        new.story = self.story
        new.player = self.player
        new.events = self.events
        new.state = GameState(
            current_story=self.story,
            player=Player(
                stats=dict(self.gsm.get_stats()),
                inventory=list(self.gsm.get_inventory()),
            ),
            flags=dict(self.gsm.get_flags()),
            turn_count=self.gsm.get_turn_count(),
            current_location=self.gsm.get_current_location(),
            turns_in_location=self.gsm.game_state.turns_in_location,
        )
        new.gsm = GameStateManager(new.state)
        new.em = TrackingEventManager(self.events, quiet_console())
        new.em.triggered_event_ids = set(self.em.triggered_event_ids)
        new.em.fired_ids = set(self.em.fired_ids)
        new.em.fire_counts = dict(self.em.fire_counts)
        new.fired = set(self.fired)
        new.instructions = []
        return new

    def ended(self):
        return self.gsm.get_flags().get("game_ended", False)


def check_invariants(game: SimulatedGame):
    """Cheap sanity checks that must hold in every reachable state."""
    state = game.state
    assert isinstance(state.current_location, str)
    assert isinstance(state.turn_count, int) and state.turn_count >= 0
    assert isinstance(state.turns_in_location, int) and state.turns_in_location >= 0
    for flag, value in state.flags.items():
        assert isinstance(flag, str)
        assert value is True or value is False
    for item in state.player.inventory:
        assert isinstance(item, (str, type(None)))
    assert game.em.triggered_event_ids <= set(game.em.events)
    for event_id in game.em.triggered_event_ids:
        assert isinstance(event_id, str)


def action_corpus(events, include_raw_actions=True):
    """Every player input the shipped YAML can react to.

    Built from the YAML itself: ``player_action_keyword`` keyword lists,
    ``player_action`` exact values, plus wrapped variants so substring-matching
    edge cases ("search desk" inside a longer sentence) get explored.

    ``include_raw_actions=False`` models only inputs a player could plausibly
    produce in normal play (LLM-written choice labels vs. raw internal action
    ids like ``end_story_success_heroic``, which only surface as choice labels
    if the event that adds them has already fired).
    """
    keywords = set()
    exact = set()
    intents = set()
    for event in events:
        conditions = event.trigger.get("conditions", []) or []
        for condition in conditions:
            ctype = condition.get("type")
            if ctype == "player_action_keyword":
                keywords.update(str(k) for k in condition.get("keywords", []) or [])
            elif ctype == "player_action":
                exact.add(str(condition.get("value")))
            elif ctype == "player_intent":
                intents.add(str(condition.get("value")))
    corpus = set(keywords) | {"wait", "look around", "zzz do nothing", "status"}
    corpus |= {f"i will {kw}" for kw in keywords}
    if include_raw_actions:
        corpus |= set(exact) | set(intents)
    return sorted(corpus)


def explore(
    game: SimulatedGame,
    max_depth=12,
    max_states=1200,
    corpus=None,
):
    """Breadth-first exploration of the reachable state space.

    Every reachable state is visited at most once (dedup by ``signature``), and
    from each state every corpus action is tried. ``check_invariants`` runs on
    every generated child state. Returns
    ``(states_visited, events_fired, terminal_signatures)`` where
    ``events_fired`` includes non-``once`` events (fire tracking, not just the
    ``triggered_event_ids`` set).
    """
    if corpus is None:
        corpus = action_corpus(game.events)
    seen = {game.signature(): game}
    frontier = deque([game])
    fired = set(game.fired)
    terminals = set()
    while frontier and len(seen) < max_states:
        node = frontier.popleft()
        if node.gsm.get_turn_count() >= max_depth:
            continue
        for action in corpus:
            child = node.clone()
            child.step(action)
            check_invariants(child)
            fired |= set(child.fired)
            if child.ended():
                terminals.add(child.signature())
            sig = child.signature()
            if sig not in seen:
                seen[sig] = child
                frontier.append(child)
    return seen, fired, terminals

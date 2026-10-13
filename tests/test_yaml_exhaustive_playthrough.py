"""Exhaustive playthrough tests over the shipped story YAMLs — no LLM needed.

Every test drives the real ``EventManager``/``GameStateManager`` through
``yaml_sim.SimulatedGame``. The LLM only ever generates prose and choice
labels, so the entire state machine (flags, inventory, stats, locations, turn
counters, event gating) is exercised deterministically here.

The explorer (``yaml_sim.explore``) tries *every* corpus action from every
reachable state, deduplicating states, and asserts engine invariants on every
generated child state. It is how the "every combination of choices" coverage is
obtained without an LLM in the loop.
"""

import json

import pytest

from text_adventure_tui_lib.data_structures import GameState, Player
from text_adventure_tui_lib.game_state_manager import GameStateManager

from text_adventure_tui_lib.yaml_loader import load_story_and_player

from yaml_sim import (
    CLOCKWORK,
    STORIES_PATH,
    WHISPERS,
    SimulatedGame,
    action_corpus,
    explore,
)

# The two ending events are `player_action` exact matches whose action ids
# surface as the choices rescue_elian offers via present_choices, so they only
# fire in the corpus that includes raw action ids (or after that choice is
# picked). low_health_warning stays dormant until a shipped story can deal
# enough damage to bring health <= 25 (best case today: 80).
WHISPERS_UNREACHABLE_PLAIN = {
    "end_story_success_cautious",
    "end_story_success_heroic",
    "low_health_warning",
}

LOW_HEALTH_ONLY = {"low_health_warning"}


# ---------------------------------------------------------------------------
# Fixtures: run each exhaustive exploration once per module
# ---------------------------------------------------------------------------


def _explore(story_name, include_raw_actions):
    game = SimulatedGame(story_name, run_story_start=True)
    corpus = action_corpus(game.events, include_raw_actions=include_raw_actions)
    return explore(game, max_depth=12, max_states=1200, corpus=corpus)


@pytest.fixture(scope="module")
def whispers_explored():
    return _explore(WHISPERS, include_raw_actions=False)


@pytest.fixture(scope="module")
def whispers_raw_explored():
    return _explore(WHISPERS, include_raw_actions=True)


@pytest.fixture(scope="module")
def clockwork_explored():
    return _explore(CLOCKWORK, include_raw_actions=True)


# ---------------------------------------------------------------------------
# Exhaustive state-space exploration
# ---------------------------------------------------------------------------


def test_whispers_exhaustive_reachability(whispers_explored):
    states, fired, terminals = whispers_explored
    assert len(states) >= 100, "explorer found suspiciously few states"
    assert set(SimulatedGame(WHISPERS).em.events) - fired == WHISPERS_UNREACHABLE_PLAIN
    # The whole journal -> journal-entry -> key -> bluffs -> crypt -> rescue
    # chain is reachable again now that add_item works.
    for event_id in ("read_journal_clue", "find_hidden_key", "arrive_at_bluffs",
                     "tide_recedes", "enter_the_crypt", "rescue_elian"):
        assert event_id in fired
    # Endings only fire via the raw action ids of rescue_elian's choices.
    assert terminals == set()


def test_whispers_reachable_inventory_contents(whispers_explored):
    states, _, _ = whispers_explored
    seen = set()
    for game in states.values():
        seen.update(str(i) for i in game.inventory())
    assert {"elians_journal", "runic_key"} <= seen
    assert None not in seen


def test_whispers_health_stays_full(whispers_explored):
    states, _, _ = whispers_explored
    for game in states.values():
        assert game.stats().get("health", 100) == 100


def test_clockwork_exhaustive_reachability(clockwork_explored):
    states, fired, terminals = clockwork_explored
    assert len(states) >= 400, "explorer found suspiciously few states"
    assert set(SimulatedGame(CLOCKWORK).em.events) - fired == LOW_HEALTH_ONLY
    # All three escape endings are reachable, so terminal states exist.
    assert terminals
    for signature in terminals:
        flags = set(signature[0])
        assert "game_ended" in flags


def test_clockwork_min_reachable_health(clockwork_explored):
    states, _, _ = clockwork_explored
    healths = [
        g.stats().get("health") for g in states.values() if "health" in g.stats()
    ]
    assert min(healths) == 80  # arc 100 minus desperate_escape's -20
    assert min(healths) > 25  # low_health_warning threshold is unreachable


def test_whispers_endings_reachable_via_choice_actions(whispers_raw_explored):
    """The ending events are `player_action` exact matches whose action ids are
    what rescue_elian's present_choices return when the player picks one, so
    they fire once those ids reach the event pass."""
    _, fired, terminals = whispers_raw_explored
    assert "rescue_elian" in fired
    assert "end_story_success_heroic" in fired
    assert "end_story_success_cautious" in fired
    assert terminals  # the story can actually be finished
    for signature in terminals:
        assert "game_ended" in set(signature[0])
    # low_health_warning remains dormant: no story damage can reach health 25.
    assert "low_health_warning" not in fired


# ---------------------------------------------------------------------------
# Every keyword of every reachable event fires it
# ---------------------------------------------------------------------------


def _fire_count(game, event_id):
    return game.em.fire_counts.get(event_id, 0)


CLOCKWORK_KEYWORD_CASES = [
    # (event_id, actions to reach the right state, keyword to try)
    ("scout_museum", [], "scout"),
    ("scout_museum", [], "observe"),
    ("scout_museum", [], "watch"),
    ("scout_museum", [], "study museum"),
    ("scout_museum", [], "case the joint"),
    ("enter_museum_stealth", ["scout the museum"], "sneak in"),
    ("enter_museum_stealth", ["scout the museum"], "service entrance"),
    ("enter_museum_stealth", ["scout the museum"], "stealth"),
    ("enter_museum_stealth", ["scout the museum"], "quietly"),
    ("enter_museum_stealth", ["scout the museum"], "slip in"),
    ("enter_museum_bold", [], "front door"),
    ("enter_museum_bold", [], "bold"),
    ("enter_museum_bold", [], "direct"),
    ("enter_museum_bold", [], "main entrance"),
    ("enter_museum_bold", [], "walk in"),
    ("find_temporal_gear_hall", ["scout the museum", "sneak in"], "find gear"),
    ("find_temporal_gear_hall", ["scout the museum", "sneak in"], "temporal gear"),
    ("find_temporal_gear_hall", ["scout the museum", "sneak in"], "search"),
    ("find_temporal_gear_hall", ["scout the museum", "sneak in"], "look for"),
    ("find_temporal_gear_hall", ["scout the museum", "sneak in"], "locate"),
    (
        "disable_security_lockpicks",
        ["scout the museum", "sneak in", "look for the gear"],
        "use lockpicks",
    ),
    (
        "disable_security_lockpicks",
        ["scout the museum", "sneak in", "look for the gear"],
        "pick lock",
    ),
    (
        "disable_security_lockpicks",
        ["scout the museum", "sneak in", "look for the gear"],
        "disable security",
    ),
    (
        "disable_security_lockpicks",
        ["scout the museum", "sneak in", "look for the gear"],
        "bypass",
    ),
    (
        "steal_temporal_gear",
        ["scout the museum", "sneak in", "look for the gear", "bypass"],
        "take gear",
    ),
    (
        "steal_temporal_gear",
        ["scout the museum", "sneak in", "look for the gear", "bypass"],
        "steal gear",
    ),
    (
        "steal_temporal_gear",
        ["scout the museum", "sneak in", "look for the gear", "bypass"],
        "grab",
    ),
    (
        "steal_temporal_gear",
        ["scout the museum", "sneak in", "look for the gear", "bypass"],
        "temporal gear",
    ),
]


@pytest.mark.parametrize(
    "event_id,prefix,keyword",
    CLOCKWORK_KEYWORD_CASES,
    ids=[f"{e}-{k}" for e, _, k in CLOCKWORK_KEYWORD_CASES],
)
def test_every_clockwork_keyword_fires_its_event(event_id, prefix, keyword):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for action in prefix:
        game.step(action)
    before = _fire_count(game, event_id)
    game.step(f"please {keyword} now")
    assert _fire_count(game, event_id) > before


@pytest.mark.parametrize("keyword", [
    "smoke bomb", "use smoke", "throw smoke", "smoke",
])
def test_smoke_bomb_escape_keywords(keyword):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for action in ["scout the museum", "sneak in", "look for the gear",
                   "bypass", "grab the gear"]:
        game.step(action)
    before = _fire_count(game, "escape_with_smoke_bomb")
    game.step(keyword)
    assert _fire_count(game, "escape_with_smoke_bomb") > before
    assert game.flags().get("game_ended_success") is True


@pytest.mark.parametrize("keyword", ["sneak out", "stealth", "quietly",
                                     "service entrance"])
def test_stealth_escape_keywords(keyword):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for action in ["scout the museum", "sneak in", "look for the gear",
                   "bypass", "grab the gear"]:
        game.step(action)
    before = _fire_count(game, "escape_stealth_route")
    game.step(keyword)
    assert _fire_count(game, "escape_stealth_route") > before
    assert game.flags().get("game_ended_success") is True


@pytest.mark.parametrize("keyword", ["run", "dash", "flee", "escape quickly"])
def test_desperate_escape_keywords(keyword):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for action in ["scout the museum", "sneak in", "look for the gear",
                   "bypass", "grab the gear"]:
        game.step(action)
    before = _fire_count(game, "desperate_escape")
    game.step(keyword)
    assert _fire_count(game, "desperate_escape") > before
    assert game.flags().get("barely_escaped") is True


@pytest.mark.parametrize("keyword", [
    "search desk", "examine desk", "look at desk", "investigate desk",
])
def test_every_whispers_desk_keyword_finds_journal(keyword):
    game = SimulatedGame(WHISPERS, run_story_start=True)
    before = _fire_count(game, "find_elians_journal")
    game.step(f"maybe {keyword}")
    assert _fire_count(game, "find_elians_journal") > before
    assert game.flags().get("has_journal") is True


@pytest.mark.parametrize("event_id,prefix,keyword", [
    ("read_journal_clue", ["search desk"], "read journal"),
    ("read_journal_clue", ["search desk"], "open journal"),
    ("read_journal_clue", ["search desk"], "examine journal"),
    ("read_journal_clue", ["search desk"], "look at journal"),
    ("find_hidden_key", ["search desk", "read journal"], "search bookshelf"),
    ("arrive_at_bluffs", ["search desk", "read journal", "search bookshelf"],
     "go to bluffs"),
    ("enter_the_crypt",
     ["search desk", "read journal", "search bookshelf", "go to bluffs",
      "wait", "wait", "wait", "wait"],  # let the tide recede first
     "enter crypt"),
    ("rescue_elian",
     ["search desk", "read journal", "search bookshelf", "go to bluffs",
      "wait", "wait", "wait", "wait", "enter crypt"],
     "use key"),
])
def test_whispers_chain_events_fire(event_id, prefix, keyword):
    """Every gate event of the Whispers chain fires once the player has the
    items it checks for (add_item now works)."""
    game = SimulatedGame(WHISPERS, run_story_start=True)
    for action in prefix:
        game.step(action)
    before = _fire_count(game, event_id)
    game.step(keyword)
    assert _fire_count(game, event_id) > before


@pytest.mark.parametrize("ending", [
    "end_story_success_heroic", "end_story_success_cautious",
])
def test_whispers_endings_fire_after_full_chain(ending):
    game = SimulatedGame(WHISPERS, run_story_start=True)
    for action in ["search desk", "read journal", "search bookshelf",
                   "go to bluffs", "wait", "wait", "wait", "wait",
                   "descend into the archway", "use key on the door"]:
        game.step(action)
    assert game.flags().get("elian_is_found") is True
    game.step(ending)
    assert game.flags().get("game_ended_success") is True
    assert game.ended() is True


# ---------------------------------------------------------------------------
# Cartesian end-to-end paths through The Clockwork Heist
# ---------------------------------------------------------------------------


STEALTH_PREFIX = ["scout the museum", "sneak in", "look for the gear",
                  "bypass the security", "grab the gear"]
BOLD_PREFIX = ["walk in the front door", "look for the gear",
               "bypass the security", "grab the gear"]


@pytest.mark.parametrize("prefix,entry", [
    (STEALTH_PREFIX, "stealth"),
    (BOLD_PREFIX, "bold"),
])
@pytest.mark.parametrize("escape", ["smoke bomb", "sneak out", "run"])
def test_all_entry_escape_combinations(prefix, entry, escape):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for action in prefix:
        game.step(action)
    assert game.location() == "chronos_exhibition_hall"
    game.step(escape)

    if escape == "smoke bomb":
        assert game.flags().get("escaped_successfully") is True
        assert game.flags().get("game_ended_success") is True
        assert "smoke_bomb" not in game.inventory()
    elif escape == "sneak out":
        if entry == "stealth":
            assert game.flags().get("escaped_successfully") is True
            assert game.flags().get("game_ended_success") is True
        else:
            # enter_museum_bold never sets entered_stealthily, so the stealth
            # escape cannot fire and the player is not stranded either —
            # desperate_escape remains available.
            assert game.flags().get("escaped_successfully") is None
            assert game.ended() is False
            game.step("run")
            assert game.flags().get("barely_escaped") is True
    else:  # run
        assert game.flags().get("barely_escaped") is True
        assert game.flags().get("game_ended_success") is True
        assert game.stats()["health"] == 80


@pytest.mark.parametrize("entry_kw,expected_flags", [
    ("sneak in", {"entered_stealthily"}),
    ("slip in", {"entered_stealthily"}),
    ("service entrance", {"entered_stealthily"}),
    ("walk in", {"entered_boldly"}),
    ("front door", {"entered_boldly"}),
    ("main entrance", {"entered_boldly"}),
])
def test_entry_mutually_exclusive_flags(entry_kw, expected_flags):
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("scout the museum")
    game.step(entry_kw)
    for flag in expected_flags:
        assert game.flags().get(flag) is True
    other = {"entered_stealthily", "entered_boldly"} - expected_flags
    for flag in other:
        assert game.flags().get(flag) is None


# ---------------------------------------------------------------------------
# General (shared) events: keywords, once semantics, false positives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", ["help", "?", "commands", "what can i do"])
def test_help_command_keywords(keyword):
    game = SimulatedGame(WHISPERS, run_story_start=True)
    _, main = game.step(keyword)
    assert "Available commands" in (main.get("override_narrative") or "")


@pytest.mark.parametrize("keyword", ["debug", "status"])
def test_debug_info_keywords(keyword):
    game = SimulatedGame(WHISPERS, run_story_start=True)
    _, main = game.step(f"check the {keyword}")
    assert any("Debug info" in t for t in main["injected_narratives_post"])


def test_first_time_in_location_rearms_per_location():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("search desk")
    game.step("read journal")  # unlocks knows_about_bluffs
    game.step("go to bluffs")
    assert game.location() == "saltstone_bluffs"
    assert _fire_count(game, "first_time_in_location") == 1
    game.step("wait")  # turns_in_location -> 1
    game.step("wait")  # fires again for the new location
    assert _fire_count(game, "first_time_in_location") == 2


@pytest.mark.parametrize("keyword", ["take", "pick up", "grab", "get"])
def test_inventory_full_warning_only_at_capacity(keyword):
    """FIXED: the warning needs a full inventory (capacity 2), so it no longer
    fires on every take/get with room to spare."""
    roomy = SimulatedGame(WHISPERS, run_story_start=True)
    _, main = roomy.step(f"{keyword} something")
    assert main["injected_narratives_post"] == []

    full = SimulatedGame(WHISPERS, run_story_start=True)
    full.step("search desk")  # journal = 1 item...
    full.step("read journal")
    full.step("search bookshelf")  # ...key = 2 items == capacity
    assert len(full.inventory()) == 2
    _, main2 = full.step(f"{keyword} something else")
    assert any("Your hands are full" in t for t in main2["injected_narratives_post"])


def test_long_time_in_location_fires_once_per_turn():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    for _ in range(6):
        game.step("wait")
    # Fires exactly once per turn once turns_in_location >= 5 (the old engine
    # fired it in both passes, duplicating the injection).
    assert game.em.fire_counts["long_time_in_location"] == 1
    game.step("wait")
    assert game.em.fire_counts["long_time_in_location"] == 2


# ---------------------------------------------------------------------------
# Save / resume edge cases (mirrors of game.py's persistence logic)
# ---------------------------------------------------------------------------


def _simulate_save(game, narrative="A narrated scene stands before you."):
    """Mirror game.py's save payload (GameState + event state + narrative)."""
    return json.loads(json.dumps(
        {
            "game_state": game.gsm.game_state,
            "event_manager_state": game.em.get_state(),
            "narrative": narrative,
        },
        default=lambda o: o.__dict__,
    ))


def _simulate_resume(saved, story_name):
    """Mirror game.py's resume: flags/location/counters/player/narrative."""
    story, yaml_player = load_story_and_player(story_name, STORIES_PATH)
    saved_player = saved["game_state"].get("player") or {}
    player = Player(
        stats=dict(saved_player.get("stats", yaml_player.stats)),
        inventory=list(saved_player.get("inventory", yaml_player.inventory)),
    )
    restored = GameState(
        current_story=story,
        player=player,
        flags=saved["game_state"]["flags"],
        turn_count=saved["game_state"]["turn_count"],
        current_location=saved["game_state"]["current_location"],
        turns_in_location=saved["game_state"]["turns_in_location"],
    )
    resumed = SimulatedGame(story_name)
    resumed.state = restored
    resumed.gsm = GameStateManager(restored)
    resumed.em.load_state(saved["event_manager_state"])
    return resumed, saved.get("narrative", "Your story continues...")


def test_save_resume_restores_progression_and_player_changes():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("walk in the front door")  # stealth 80 -> 70
    game.step("scout the museum")
    assert game.stats()["stealth"] == 70
    saved = _simulate_save(game)

    resumed, narrative = _simulate_resume(saved, CLOCKWORK)
    assert resumed.location() == game.location()
    assert resumed.gsm.get_turn_count() == game.gsm.get_turn_count()
    assert resumed.flags().keys() >= {"heist_started", "inside_museum",
                                      "entered_boldly"}
    # FIXED: stats and inventory now come from the save, not the arc.
    assert resumed.stats()["stealth"] == 70


def test_save_resume_restores_narrative_and_items():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("scout the museum")
    game.step("sneak in")
    saved = _simulate_save(game, narrative="The service hallway creaks.")

    resumed, narrative = _simulate_resume(saved, CLOCKWORK)
    assert narrative == "The service hallway creaks."
    assert "lockpicks" in resumed.inventory()
    assert "smoke_bomb" in resumed.inventory()


def test_once_events_stay_fired_after_resume():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("scout the museum")
    assert _fire_count(game, "scout_museum") == 1
    saved = _simulate_save(game)
    assert "scout_museum" in saved["event_manager_state"]["triggered_event_ids"]

    resumed, _ = _simulate_resume(saved, CLOCKWORK)
    before = _fire_count(resumed, "scout_museum")
    resumed.step("scout the museum")
    assert _fire_count(resumed, "scout_museum") == before


def test_resume_without_player_key_falls_back_to_arc():
    """Old saves (written before player persistence) resume with the arc's
    starting stats/inventory instead of crashing."""
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("scout the museum")
    saved = _simulate_save(game)
    saved["game_state"].pop("player")
    saved.pop("narrative", None)

    resumed, narrative = _simulate_resume(saved, CLOCKWORK)
    assert resumed.stats() == {"health": 100, "stealth": 80, "cunning": 70}
    assert resumed.inventory() == ["lockpicks", "smoke_bomb"]
    assert narrative == "Your story continues..."


# ---------------------------------------------------------------------------
# Story checkpoints (YAML data consumed by the turn loop)
# ---------------------------------------------------------------------------


def _checkpoint_outcome(story, turn, flags):
    """Mirror of game.py's checkpoint handling (prompt injection / forced end)."""
    injections = []
    ending = None
    for checkpoint in story.checkpoints:
        if checkpoint.get("turn") != turn:
            continue
        if checkpoint.get("prompt_injection"):
            injections.append(checkpoint["prompt_injection"])
        if checkpoint.get("force_end_game"):
            message = "The story reaches its conclusion."
            for flag_msg in checkpoint.get("flag_messages", []):
                name = flag_msg.get("flag")
                message_key = "message_if_set" if flags.get(name) else \
                    "message_if_not_set"
                if flag_msg.get(message_key):
                    message = flag_msg[message_key]
                    break
            ending = message
    return injections, ending


def test_whispers_checkpoints():
    story, _ = load_story_and_player(WHISPERS, STORIES_PATH)
    injections, ending = _checkpoint_outcome(story, 15, {})
    assert injections == ["Time is running short. You feel an increasing "
                          "urgency to find Master Elian."]
    assert ending is None
    _, ending = _checkpoint_outcome(story, 25, {})
    assert "unable to locate Master Elian" in ending
    _, ending = _checkpoint_outcome(story, 25, {"elian_is_found": True})
    assert "successfully rescued" in ending


def test_clockwork_checkpoints():
    story, _ = load_story_and_player(CLOCKWORK, STORIES_PATH)
    injections, ending = _checkpoint_outcome(story, 10, {})
    assert injections == ["Security is tightening. You need to move quickly now."]
    _, ending = _checkpoint_outcome(story, 15, {})
    assert "heist has gone wrong" in ending
    _, ending = _checkpoint_outcome(story, 15, {"has_temporal_gear": True})
    assert "Temporal Gear" in ending


def test_whispers_never_reaches_its_checkpoint_end():
    """Even at turn 25 the checkpoint ending fires with the failure message,
    because the authored success flag (elian_is_found) is unreachable."""
    game = SimulatedGame(WHISPERS, run_story_start=True)
    for _ in range(25):
        game.step("wait")
    story, _ = load_story_and_player(WHISPERS, STORIES_PATH)
    _, ending = _checkpoint_outcome(story, game.gsm.get_turn_count(),
                                    game.flags())
    assert "unable to locate Master Elian" in ending

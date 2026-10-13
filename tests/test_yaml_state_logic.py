"""Logic and state tests for the YAML event engine — no LLM required.

These tests drive ``EventManager`` / ``GameStateManager`` directly. The LLM in
``game.py`` only produces prose and choice labels; it never mutates state, so
every trigger/action behavior can be verified deterministically here.
"""

import pytest

from text_adventure_tui_lib.data_structures import GameState, Player, Story
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.yaml_loader import load_story_and_player

from yaml_sim import (
    CLOCKWORK,
    STORIES_PATH,
    WHISPERS,
    SimulatedGame,
    make_event,
    quiet_console,
)

GENERAL_EVENT_IDS = [
    "low_health_warning",
    "inventory_full_warning",
    "first_time_in_location",
    "long_time_in_location",
    "help_command",
    "debug_info",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_engine(events, stats=None, inventory=None, location="start",
                turn_count=0, turns_in_location=0, flags=None):
    """Build a GameStateManager + EventManager around synthetic events."""
    story = Story(id="synthetic", title="Synthetic", events=list(events))
    player = Player(stats=dict(stats or {}), inventory=list(inventory or []))
    state = GameState(
        current_story=story,
        player=player,
        flags=dict(flags or {}),
        turn_count=turn_count,
        current_location=location,
        turns_in_location=turns_in_location,
    )
    gsm = GameStateManager(state)
    em = EventManager(story.events, quiet_console())
    return gsm, em


def cond(**kwargs):
    return kwargs


# ---------------------------------------------------------------------------
# Loading the real YAML
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("story_name", [WHISPERS, CLOCKWORK])
def test_load_real_story_contents(story_name):
    story, player = load_story_and_player(story_name, STORIES_PATH)

    assert story.id == story_name
    # 6 general events + 10 story events per shipped story.
    assert len(story.events) == 16
    assert len({e.id for e in story.events}) == 16


def test_general_events_load_before_story_events():
    """Load order is general-first; event dict iteration order follows it."""
    game = SimulatedGame(WHISPERS, run_story_start=False)
    ids = list(game.em.events)
    assert ids[:6] == GENERAL_EVENT_IDS
    assert ids[6] == "story_start"


def test_clockwork_arc_initial_state():
    story, player = load_story_and_player(CLOCKWORK, STORIES_PATH)
    assert story.starting_location == "thieves_den"
    assert player.inventory == ["lockpicks", "smoke_bomb"]
    assert player.stats == {"health": 100, "stealth": 80, "cunning": 70}


def test_whispers_arc_initial_state():
    story, player = load_story_and_player(WHISPERS, STORIES_PATH)
    assert story.starting_location == "elian_study"
    assert player.inventory == []
    assert player.stats == {"health": 100, "sanity": 100, "knowledge": 10}


def test_old_format_fallback_and_missing_story(tmp_path):
    legacy = tmp_path / "legacy_story"
    legacy.mkdir()
    (legacy / "game_setup.yaml").write_text(
        "- id: story_start\n"
        "  name: Legacy\n"
        "  trigger:\n"
        "    mode: MANUAL\n"
        "  actions: []\n"
        "  initial_player_stats:\n"
        "    health: 42\n"
        "  initial_inventory: [torch]\n"
    )
    story, player = load_story_and_player("legacy_story", tmp_path)
    assert story.id == "story_start"
    assert player.stats["health"] == 42
    assert player.inventory == ["torch"]

    empty = tmp_path / "empty_story"
    empty.mkdir()
    with pytest.raises(ValueError):
        load_story_and_player("empty_story", tmp_path)


def test_duplicate_event_ids_dict_keeps_last():
    first = make_event("dup", actions=[{"type": "set_flag", "value": "first"}])
    second = make_event("dup", actions=[{"type": "set_flag", "value": "second"}])
    gsm, em = make_engine([first, second])
    em.execute_event_actions("dup", gsm, [])
    assert gsm.get_flags().get("second") is True
    assert gsm.get_flags().get("first") is None


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "condition,state,expected",
    [
        (cond(type="location", value="cave"), dict(location="cave"), True),
        (cond(type="location", value="cave"), dict(location="hall"), False),
        (cond(type="flag_set", value="seen"), dict(flags={"seen": True}), True),
        (cond(type="flag_set", value="seen"), dict(flags={}), False),
        (cond(type="flag_not_set", value="seen"), dict(flags={}), True),
        (cond(type="flag_not_set", value="seen"), dict(flags={"seen": True}), False),
        (cond(type="inventory_has", value="key"), dict(inventory=["key"]), True),
        (cond(type="inventory_has", value="key"), dict(inventory=[]), False),
        (cond(type="inventory_not_has", value="key"), dict(inventory=[]), True),
        (cond(type="inventory_not_has", value="key"), dict(inventory=["key"]), False),
        (cond(type="game_start"), dict(turn_count=0), True),
        (cond(type="game_start"), dict(turn_count=1), False),
        (
            cond(type="turn_count_in_location", value=3, operator="=="),
            dict(turns_in_location=3),
            True,
        ),
        (
            cond(type="turn_count_in_location", value=3, operator=">="),
            dict(turns_in_location=4),
            True,
        ),
        (
            cond(type="turn_count_in_location", value=3, operator=">="),
            dict(turns_in_location=2),
            False,
        ),
        (
            cond(type="turn_count_in_location", value=3, operator="<="),
            dict(turns_in_location=3),
            True,
        ),
        (
            cond(type="turn_count_in_location", value=3, operator=">"),
            dict(turns_in_location=3),
            False,
        ),
        (
            cond(type="turn_count_in_location", value=3, operator="<"),
            dict(turns_in_location=2),
            True,
        ),
        (
            cond(type="turn_count_global", value=5, operator=">="),
            dict(turn_count=5),
            True,
        ),
        (
            cond(type="turn_count_global", value=5, operator="<"),
            dict(turn_count=5),
            False,
        ),
        (cond(type="stat_check", stat="hp", operator=">=", value=50),
         dict(stats={"hp": 50}), True),
        (cond(type="stat_check", stat="hp", operator=">=", value=51),
         dict(stats={"hp": 50}), False),
        (cond(type="stat_check", stat="hp", operator="==", value=0),
         dict(stats={}), True),  # missing stat defaults to 0
        (cond(type="stat_check", stat="hp", operator="<", value=1),
         dict(stats={}), True),
        (cond(type="stat_check", stat="hp", operator="<=", value=0),
         dict(stats={}), True),
        (cond(type="stat_check", stat="hp", operator=">", value=-1),
         dict(stats={}), True),
        (cond(type="no_such_condition"), dict(), False),
    ],
)
def test_condition_types(condition, state, expected):
    gsm, em = make_engine(
        [make_event("e", trigger={"mode": "AND", "conditions": [condition]},
                    actions=[{"type": "set_flag", "value": "fired"}])],
        stats=state.get("stats"),
        inventory=state.get("inventory"),
        location=state.get("location", "start"),
        turn_count=state.get("turn_count", 0),
        turns_in_location=state.get("turns_in_location", 0),
        flags=state.get("flags"),
    )
    em.check_and_trigger_events(gsm, "", [])
    assert bool(gsm.get_flags().get("fired")) is expected, condition


def test_keyword_condition_is_case_insensitive_substring_match():
    event = make_event("e", trigger={"mode": "AND", "conditions": [
        cond(type="player_action_keyword", keywords=["search desk"])]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "I Search Desk thoroughly", [])
    assert gsm.get_flags().get("fired") is True


def test_keyword_condition_needs_nonempty_input():
    """A pre-choice pass (empty input) cannot satisfy keyword conditions."""
    event = make_event("e", trigger={"mode": "AND", "conditions": [
        cond(type="player_action_keyword", keywords=["search desk"])]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is None


def test_player_action_is_exact_case_insensitive_match():
    event = make_event("e", trigger={"mode": "AND", "conditions": [
        cond(type="player_action", value="end_story_heroic")]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "End_Story_Heroic", [])
    assert gsm.get_flags().get("fired") is True
    gsm2, em2 = make_engine([event])
    em2.check_and_trigger_events(gsm2, "end story heroic maybe", [])
    assert gsm2.get_flags().get("fired") is None


def test_player_intent_is_exact_match():
    event = make_event("e", trigger={"mode": "AND", "conditions": [
        cond(type="player_intent", value="search_desk")]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "look at the desk", [], "search_desk")
    assert gsm.get_flags().get("fired") is True
    gsm2, em2 = make_engine([event])
    em2.check_and_trigger_events(gsm2, "look at the desk", [], "read_journal")
    assert gsm2.get_flags().get("fired") is None


@pytest.mark.parametrize("mode", ["AND", "OR"])
def test_empty_conditions_never_fire(mode):
    event = make_event("e", trigger={"mode": mode, "conditions": []},
                       actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "anything", [])
    assert gsm.get_flags() == {}


def test_missing_conditions_key_never_fires():
    gsm, em = make_engine([make_event("e", trigger={"mode": "AND"})])
    em.check_and_trigger_events(gsm, "anything", [])
    assert gsm.get_flags() == {}


def test_or_mode_fires_if_any_condition_met():
    event = make_event("e", trigger={"mode": "OR", "conditions": [
        cond(type="no_such_condition", value="x"),
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is True


def test_mode_is_case_insensitive():
    event = make_event("e", trigger={"mode": "and", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is True


def test_manual_mode_never_auto_fires():
    event = make_event("e", trigger={"mode": "MANUAL", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "anything", [])
    assert gsm.get_flags().get("fired") is None


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action,check",
    [
        ({"type": "set_flag", "value": "a"}, lambda s: s.flags.get("a") is True),
        ({"type": "clear_flag", "value": "a"}, lambda s: "a" not in s.flags),
        (
            {"type": "add_item", "item_id": "lamp"},
            lambda s: s.player.inventory == ["key", "lamp"],
        ),
        (
            {"type": "remove_item", "value": "key"},
            lambda s: s.player.inventory == [],
        ),
        (
            {"type": "change_location", "value": "cave"},
            lambda s: s.current_location == "cave",
        ),
        (
            {"type": "update_stat", "stat": "hp", "change_by": 5},
            lambda s: s.player.stats["hp"] == 25,
        ),
        (
            {"type": "end_game", "success": False},
            lambda s: s.flags.get("game_ended") is True
            and s.flags.get("game_ended_failure") is True
            and s.flags.get("game_ended_success") is None,
        ),
    ],
)
def test_action_types(action, check):
    event = make_event("e", actions=[action])
    gsm, em = make_engine([event], stats={"hp": 20}, inventory=["key"])
    gsm.set_flag("a")
    em.execute_event_actions("e", gsm, [])
    assert check(gsm.game_state), action


def test_add_item_with_item_id_key_does_not_duplicate():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "add_item", "item_id": "lamp"},
        {"type": "add_item", "item_id": "lamp"},
    ])], inventory=["lamp"])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_inventory() == ["lamp"]


def test_remove_item_missing_is_noop():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "remove_item", "value": "ghost"}])])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_inventory() == []


def test_clear_flag_missing_is_noop():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "clear_flag", "value": "never_set"}])])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_flags() == {}


def test_update_stat_missing_stat_starts_from_zero():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "update_stat", "stat": "new", "change_by": -7}])])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_stats()["new"] == -7


def test_update_stat_non_numeric_raises():
    """CHARACTERIZATION: non-numeric stats crash with TypeError today."""
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "update_stat", "stat": "mood", "change_by": 1}])],
        stats={"mood": "happy"})
    with pytest.raises(TypeError):
        em.execute_event_actions("e", gsm, [])


def test_change_location_same_location_keeps_turn_counter():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "change_location", "value": "here"}])], location="here",
        turns_in_location=5)
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_current_location() == "here"
    assert gsm.game_state.turns_in_location == 5


def test_change_location_resets_turn_counter():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "change_location", "value": "elsewhere"}])], location="here",
        turns_in_location=5)
    em.execute_event_actions("e", gsm, [])
    assert gsm.game_state.turns_in_location == 0


def test_narrative_actions_collect_results():
    event = make_event("e", actions=[
        {"type": "override_narrative", "text": "REPLACED"},
        {"type": "inject_narrative", "text": "before", "position": "pre"},
        {"type": "inject_narrative", "text": "after"},
        {"type": "modify_prompt", "instruction": "be terse"},
        {"type": "add_choice", "label": "Run", "action": "run"},
        {"type": "present_choices", "choices": [
            {"label": "Hide", "action": "hide"},
            {"label": "Fight", "action": "fight"},
        ]},
        {"type": "not_a_real_action", "value": "ignored"},
    ])
    gsm, em = make_engine([event])
    results = em.execute_event_actions("e", gsm, [])
    assert results["override_narrative"] == "REPLACED"
    assert results["injected_narratives_pre"] == ["before"]
    assert results["injected_narratives_post"] == ["after"]
    assert results["added_choices"] == [
        {"label": "Run", "action": "run"},
        {"label": "Hide", "action": "hide"},
        {"label": "Fight", "action": "fight"},
    ]
    instructions = []
    em.execute_event_actions("e", gsm, instructions)
    assert instructions == ["be terse"]


def test_add_choice_defaults():
    event = make_event("e", actions=[{"type": "add_choice"}])
    gsm, em = make_engine([event])
    results = em.execute_event_actions("e", gsm, [])
    assert results["added_choices"] == [{"label": "Unknown Choice", "action": ""}]


def test_force_unknown_event_returns_empty_result():
    gsm, em = make_engine([])
    results = em.execute_event_actions("nope", gsm, [])
    assert results["override_narrative"] is None
    assert results["added_choices"] == []


def test_triggerless_event_can_still_be_forced():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "set_flag", "value": "forced"}])])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_flags().get("forced") is True


# ---------------------------------------------------------------------------
# once / MANUAL / force / persistence
# ---------------------------------------------------------------------------


def test_once_event_does_not_refire():
    event = make_event("once_ev", options={"once": True},
                       trigger={"mode": "AND", "conditions": [
                           cond(type="location", value="start")]},
                       actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is True
    gsm.clear_flag("fired")
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is None
    assert "once_ev" in em.triggered_event_ids


def test_force_marks_once_event_as_triggered():
    event = make_event("once_ev", options={"once": True},
                       trigger={"mode": "AND", "conditions": [
                           cond(type="location", value="start")]},
                       actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.execute_event_actions("once_ev", gsm, [])
    gsm.clear_flag("fired")
    em.check_and_trigger_events(gsm, "", [])
    assert gsm.get_flags().get("fired") is None


def test_force_bypasses_once_check_and_re_applies_actions():
    """CHARACTERIZATION: /force_event on a once-event re-runs its actions."""
    event = make_event("once_ev", options={"once": True}, actions=[
        {"type": "update_stat", "stat": "hp", "change_by": -5}])
    gsm, em = make_engine([event], stats={"hp": 100})
    em.execute_event_actions("once_ev", gsm, [])
    em.execute_event_actions("once_ev", gsm, [])
    assert gsm.get_stats()["hp"] == 90


def test_event_state_roundtrip():
    event = make_event("once_ev", options={"once": True},
                       trigger={"mode": "AND", "conditions": [
                           cond(type="location", value="start")]},
                       actions=[{"type": "set_flag", "value": "fired"}])
    gsm, em = make_engine([event])
    em.check_and_trigger_events(gsm, "", [])
    saved = em.get_state()
    assert saved == {"triggered_event_ids": ["once_ev"]}

    gsm2, em2 = make_engine([event])
    em2.load_state(saved)
    em2.check_and_trigger_events(gsm2, "", [])
    assert gsm2.get_flags().get("fired") is None


# ---------------------------------------------------------------------------
# Ordering and the override "break"
# ---------------------------------------------------------------------------


def test_first_override_event_breaks_the_pass():
    """CHARACTERIZATION: an override_narrative stops the event pass, so
    events later in load order never evaluate that turn."""
    first = make_event("first", trigger={"mode": "AND", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "override_narrative", "text": "ONE"},
                 {"type": "set_flag", "value": "first_ran"}])
    second = make_event("second", trigger={"mode": "AND", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "second_ran"}])
    gsm, em = make_engine([first, second])
    results = em.check_and_trigger_events(gsm, "", [])
    assert results["override_narrative"] == "ONE"
    assert gsm.get_flags().get("first_ran") is True
    assert gsm.get_flags().get("second_ran") is None


def test_non_override_events_all_run():
    first = make_event("first", trigger={"mode": "AND", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "first_ran"}])
    second = make_event("second", trigger={"mode": "AND", "conditions": [
        cond(type="location", value="start")]},
        actions=[{"type": "set_flag", "value": "second_ran"}])
    gsm, em = make_engine([first, second])
    em.check_and_trigger_events(gsm, "anything", [])
    assert gsm.get_flags().get("first_ran") is True
    assert gsm.get_flags().get("second_ran") is True


def test_general_help_event_shadows_story_events_same_turn():
    """CHARACTERIZATION: general events load first, so 'help' in a choice
    text pre-empts story events that also match (order-dependent behavior)."""
    game = SimulatedGame(WHISPERS, run_story_start=True)
    _, results = game.step("help me search desk")
    assert "Available commands" in (results.get("override_narrative") or "")
    assert game.flags().get("has_journal") is None

    clean = SimulatedGame(WHISPERS, run_story_start=True)
    _, clean_results = clean.step("search desk")
    assert clean.flags().get("has_journal") is True
    assert clean_results.get("override_narrative")


def test_debug_info_substring_catches_word_info():
    """'info' is a substring of ordinary words like 'information'."""
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    _, main = game.step("ask the guard for information")
    post = main["injected_narratives_post"]
    assert any("Debug info displayed in console." in t for t in post)


def test_long_time_in_location_fires_every_pass():
    """CHARACTERIZATION: it has no `once`, so it re-fires every turn AND in
    both the pre-choice and choice passes of the same turn."""
    event = make_event("restless",
                       trigger={"mode": "AND", "conditions": [
                           cond(type="turn_count_in_location", value=5,
                                operator=">=")]},
                       actions=[{"type": "inject_narrative", "text": "restless",
                                 "position": "pre"}])
    game = SimulatedGame(events=[event], turns_in_location=7)
    pre, main = game.step("wait")
    assert pre["injected_narratives_pre"] == ["restless"]
    assert main["injected_narratives_pre"] == ["restless"]


# ---------------------------------------------------------------------------
# Known engine/YAML contract mismatches (characterization + intent)
# ---------------------------------------------------------------------------


def test_add_item_ignores_value_key_and_appends_none():
    """CHARACTERIZATION: `_perform_actions` reads action['item_id'] for
    add_item, but every shipped event YAML writes add_item with 'value:' —
    so nothing real is ever added; None is appended instead."""
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("search desk")
    assert game.flags().get("has_journal") is True
    assert game.inventory() == [None]


@pytest.mark.xfail(
    reason="BUG: add_item reads 'item_id' but shipped YAML uses 'value'; "
           "fix _perform_actions to accept both, then remove this marker",
    strict=True,
)
def test_add_item_with_value_key_adds_the_item_intended():
    gsm, em = make_engine([make_event("e", actions=[
        {"type": "add_item", "value": "elians_journal"}])])
    em.execute_event_actions("e", gsm, [])
    assert gsm.get_inventory() == ["elians_journal"]


@pytest.mark.xfail(
    reason="BUG: add_item key mismatch makes read_journal_clue (inventory_has) "
           "unreachable in the shipped Whispers story",
    strict=True,
)
def test_whispers_journal_chain_intended():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("search desk")
    game.step("read journal")
    assert game.flags().get("knows_about_bluffs") is True
    assert "elians_journal" in game.inventory()


def test_whispers_chain_is_blocked_today():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("search desk")
    game.step("read journal")
    assert game.flags().get("knows_about_bluffs") is None


@pytest.mark.xfail(
    reason="BUG: first_time_in_location has once:true, so it never re-arms "
           "when the player enters a new location",
    strict=True,
)
def test_first_time_in_location_once_per_location_intended():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.gsm.game_state.turns_in_location = 1
    instructions = []
    game.em.check_and_trigger_events(game.gsm, "", instructions)
    assert instructions  # fired the first time in elian_study
    # Reach turns_in_location == 1 again in a brand-new location.
    game.gsm.set_current_location("saltstone_bluffs")
    game.gsm.game_state.turns_in_location = 1
    instructions2 = []
    game.em.check_and_trigger_events(game.gsm, "", instructions2)
    assert instructions2  # intended: describe the new location too


def test_first_time_in_location_is_once_global():
    """CHARACTERIZATION: after the first firing it never fires again, even in
    a brand-new location, because options.once marked it permanently."""
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("wait")  # turn 1; turns_in_location 0 -> 1
    game.step("wait")  # pre-choice pass at turns_in_location == 1 fires it
    assert "first_time_in_location" in game.em.triggered_event_ids
    game.gsm.set_current_location("crypt_antechamber")  # resets counter
    game.gsm.game_state.turns_in_location = 1
    results = game.em.check_and_trigger_events(game.gsm, "", [])
    assert results["injected_narratives_pre"] == []


@pytest.mark.xfail(
    reason="BUG: inventory_full_warning has no inventory-limit condition, so "
           "it injects 'Your hands are full' on any 'take/get' keyword",
    strict=True,
)
def test_inventory_full_warning_only_when_full_intended():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    pre, main = game.step("take a brochure")
    assert pre["injected_narratives_post"] == []
    assert main["injected_narratives_post"] == []


def test_inventory_full_warning_false_positive_today():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    _, main = game.step("take a brochure")
    post = main["injected_narratives_post"]
    assert any("Your hands are full." in t for t in post)


def test_low_health_warning_threshold_unreachable_in_shipped_stories():
    """CHARACTERIZATION: no shipped stat change can bring health <= 25
    (whispers: no health updates at all; clockwork: -10/-20 max)."""
    for story_name in (WHISPERS, CLOCKWORK):
        game = SimulatedGame(story_name, run_story_start=True)
        assert game.stats().get("health", 100) >= 80


# ---------------------------------------------------------------------------
# Scripted playthroughs of the real stories (deterministic, no LLM)
# ---------------------------------------------------------------------------


def test_whispers_story_start():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    assert game.location() == "elian_study"
    assert game.flags().get("knows_elian_is_missing") is True


@pytest.mark.parametrize("keyword", [
    "search desk", "examine desk", "look at desk", "investigate desk",
])
def test_whispers_desk_keyword_variants(keyword):
    game = SimulatedGame(WHISPERS, run_story_start=True)
    _, results = game.step(f"i will {keyword}")
    assert game.flags().get("has_journal") is True
    assert results["override_narrative"]


def test_whispers_desk_event_fires_only_once():
    game = SimulatedGame(WHISPERS, run_story_start=True)
    game.step("search desk")
    game.gsm.clear_flag("has_journal")
    game.step("search desk again")
    assert game.flags().get("has_journal") is None


def test_clockwork_stealth_full_path():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    assert game.location() == "thieves_den"
    game.step("scout the building")
    assert game.flags().get("museum_scouted") is True
    game.step("sneak in quietly")
    assert game.flags().get("entered_stealthily") is True
    assert game.location() == "museum_service_hall"
    game.step("search for the gear")
    assert game.location() == "chronos_exhibition_hall"
    game.step("use lockpicks on the case")
    assert game.flags().get("security_disabled") is True
    assert "lockpicks" not in game.inventory()
    game.step("take the temporal gear")
    assert game.flags().get("has_temporal_gear") is True
    _, results = game.step("throw the smoke bomb")
    assert game.flags().get("escaped_successfully") is True
    assert game.flags().get("game_ended_success") is True
    assert "smoke_bomb" not in game.inventory()
    assert results["override_narrative"]


def test_clockwork_bold_path_stats_and_escape():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("walk in the front door")
    assert game.flags().get("entered_boldly") is True
    assert game.flags().get("entered_stealthily") is None
    assert game.location() == "museum_main_hall"
    assert game.stats()["stealth"] == 70  # 80 - 10
    game.step("look for the temporal gear")
    game.step("bypass the security")
    game.step("grab the gear")
    _, results = game.step("run for the exit")
    assert game.flags().get("barely_escaped") is True
    assert game.stats()["health"] == 80  # 100 - 20
    assert game.flags().get("game_ended_success") is True
    assert results["override_narrative"]


def test_clockwork_stealth_escape_requires_stealthy_entry():
    game = SimulatedGame(CLOCKWORK, run_story_start=True)
    game.step("walk in the front door")  # bold entry, not entered_stealthily
    game.step("look for the temporal gear")
    game.step("bypass the security")
    game.step("grab the gear")
    game.step("sneak out quietly")
    # escape_stealth_route cannot fire; no other keyword matches here.
    assert game.flags().get("escaped_successfully") is None
    assert game.ended() is False
    game.step("run away")
    assert game.flags().get("barely_escaped") is True


def test_whispers_ending_events_are_end_story_actions():
    for event_id in ("end_story_success_heroic", "end_story_success_cautious"):
        event = next(e for e in SimulatedGame(WHISPERS).em.events.values()
                     if e.id == event_id)
        conditions = event.trigger.get("conditions", [])
        assert conditions[0]["type"] == "player_action"
        assert any(a["type"] == "end_game" for a in event.actions)
        assert event.options.get("once") is True

"""Probe: player_action_keyword substring semantics + false positives."""
from rich.console import Console
from text_adventure_tui_lib.event_manager import EventManager
from text_adventure_tui_lib.game_state_manager import GameStateManager
from text_adventure_tui_lib.data_structures import GameState, Player, Story

console = Console(quiet=True)
story = Story(id="t", title="t")
em = EventManager([], console)
gsm = GameStateManager(GameState(current_story=story, player=Player(), flags={},
                                 turn_count=0, current_location="start", turns_in_location=0))


def kw(kws, text):
    return em._evaluate_trigger(
        {"mode": "AND", "conditions": [{"type": "player_action_keyword", "keywords": kws}]},
        gsm, text, "")


print("game.py:181 lowercases the typed input; but the CHOICE string returned at")
print("game.py:190 is the raw LLM label (NOT lowercased). Both paths shown.\n")

tests = [
    (["Search Desk"], "search desk", "author mixed-case kw, player typed lower"),
    (["Search Desk"], "Search Desk", "author mixed-case kw, label NOT lowercased"),
    (["search desk"], "Search Desk", "lower kw, label not lowercased"),
    (["search desk"], "I carefully search desk drawer", "kw inside a longer sentence"),
    (["search desk"], "I carefully search the desk", "extra word 'the' between"),
    (["get"], "get", "the intended match"),
    (["get"], "forget the rope", "'get' as substring of 'forget'"),
    (["get"], "I target the lighthouse", "'get' inside 'target'"),
    (["get"], "budget the trip", "'get' inside 'budget'"),
    (["?"], "What should I do here", "'?' matches nothing here"),
    (["?"], "Who am I ?", "'?' as bare char"),
    (["info"], "Find the informant", "'info' inside 'informant'"),
    (["take", "pick up", "grab", "get"], "Pick up the lantern", "general_events:26"),
    (["take", "pick up", "grab", "get"], "Let's get going", "general_events:26 false positive"),
    (["take", "pick up", "grab", "get"], "I want to take the boat", "general_events:26 match"),
    (["descend"], "descend", "whispers enter_the_crypt:168"),
    (["descend"], "I descend carefully", "whispers enter_the_crypt:168 match"),
    (["descend"], "descend into darkness", "whispers enter_the_crypt:168 match"),
    (["descend"], "D E S C E N D", "substring does not survive spacing"),
    ([], "anything", "empty keyword list"),
]
for kws, text, why in tests:
    print(f"  {str(kws)[:42]:44s} vs {text!r:34s} -> {str(kw(kws, text)):5s}  # {why}")

print("\nplayer_action exactness (event_manager.py:201):")
pa = lambda v, t: em._evaluate_trigger(
    {"mode": "AND", "conditions": [{"type": "player_action", "value": v}]}, gsm, t, "")
for v, t in [("end_story_success_heroic", "end_story_success_heroic"),
             ("end_story_success_heroic", "END_STORY_SUCCESS_HEROIC"),
             ("end_story_success_heroic", " end_story_success_heroic "),
             ("end_story_success_heroic", "Rush forward and untie him immediately."),
             ("unlock_door", "unlock door"),
             (7, "7"), (None, "x")]:
    try:
        print(f"  value={v!r:32s} input={t!r:44s} -> {pa(v, t)}")
    except Exception as e:
        print(f"  value={v!r:32s} input={t!r:44s} -> RAISES {type(e).__name__}: {e}")

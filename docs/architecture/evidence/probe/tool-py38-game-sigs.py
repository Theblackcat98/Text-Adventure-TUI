"""Probe: evaluate only the PEP585 annotations from game.py:72-74 and 122 under 3.8."""
import sys
src = """
def get_llm_story_continuation(
    current_narrative: str, player_choice: str, instructions: list[str]
) -> str: ...
def get_llm_options(current_narrative: str, game_state_manager: int) -> tuple[str, list[str]]: ...
"""
try:
    exec(compile(src, "<game.py-72-122-signatures>", "exec"), {})
    print("OK: annotations evaluated")
except TypeError as e:
    print(f"TypeError: {e}")
    tb = sys.exc_info()[2]
    for fr in tb.tb_next.tb_next if tb.tb_next and tb.tb_next else []:
        pass
    # report the offending source line
    import traceback
    for line in traceback.format_exception_only(*sys.exc_info()[:2]):
        print(line.strip())

"""FLOW-3 probe 6: error paths.
A  ollama down during get_llm_options -> UnboundLocalError(raw_json_str)
   escapes (game.py:163); the 4-choice fallback at :165 is NOT reached.
B  >4 choices -> ValueError caught -> fallback options (game.py:156-165).
C  unparseable JSON -> same fallback; raw_json_str IS bound here (debug print).
D  0 choices -> same fallback.
E  intent call fails -> 'unknown_intent', turn continues (3 calls).
F  continuation call fails -> 'The path forward is hazy...' becomes narrative.
G  KeyboardInterrupt at the choice Prompt -> propagates out of game_loop.
H  KeyboardInterrupt at the bare input() on the game_ended path -> propagates.
"""
import f3_common as C
from f3_common import *  # noqa: F401,F403
from text_adventure_tui_lib.data_structures import Event
import f3_common

ev_post = Event(
    id="ev_post", name="post",
    trigger={"mode": "AND",
             "conditions": [{"type": "player_action_keyword", "keywords": ["opt"]}]},
    actions=[{"type": "inject_narrative", "text": "POSTTEXT", "position": "post"}],
)
ev_end = Event(
    id="ev_end", name="end",
    trigger={"mode": "AND", "conditions": [{"type": "game_start"}]},
    options={"once": True},
    actions=[{"type": "end_game", "success": True}],
)

# A
fake, out, oc = C.run(C.make_story([ev_post]), ["1"],
                      chat_script={"options": [ConnectionError("boom")]})
check("A: UnboundLocalError escapes game_loop",
      isinstance(oc["exception"], UnboundLocalError)
      and "raw_json_str" in str(oc["exception"]), repr(oc["exception"]))
check("A: error line printed before the crash",
      "Error getting LLM options: boom" in out)
check("A: exactly one llm call attempted", len(fake.calls) == 1)

BOMB5 = '{"narrative_summary": "SUMM1", "choices": ["A","B","C","D","E"]}'
# B
fake_b, out_b, oc_b = C.run(C.make_story([ev_post]), ["1", "1"],
                            chat_script={"options": [BOMB5]})
check("B: >4 choices -> fallback 4 generic choices", "Leave." in out_b
      and "Look around." in out_b)
check("B: fallback narrative = previous narrative (intro)",
      "The story begins..." in C.call(fake_b, "continuation", 0)["prompt"])
check("B: turn still completes normally",
      C.kinds(fake_b)[:3] == ["options", "intent", "continuation"])

# C
fake_c, out_c, oc_c = C.run(C.make_story([ev_post]), ["1"],
                            chat_script={"options": ["totally not json"]},
                            debug=True)
check("C: unparseable JSON -> fallback choices", "Check inventory." in out_c)
check("C: raw response printed under debug (raw_json_str bound on this path)",
      "LLM Raw Response was: totally not json" in out_c)
check("C: no crash", isinstance(oc_c["exception"], f3_common.OutOfInputs))

# D
fake_d, out_d, oc_d = C.run(C.make_story([ev_post]), ["1"],
                            chat_script={"options": ['{"narrative_summary": "S", "choices": []}']})
check("D: 0 choices -> fallback choices", "Wait." in out_d)
check("D: fallback narrative = previous narrative",
      "The story begins..." in C.call(fake_d, "continuation", 0)["prompt"])

# E
fake_e, out_e, oc_e = C.run(C.make_story([ev_post]), ["1"],
                            chat_script={"intent": [RuntimeError("llm down")]})
check("E: intent failure -> unknown_intent, turn continues",
      C.kinds(fake_e) == ["options", "intent", "continuation", "options"],
      str(C.kinds(fake_e)))
check("E: graceful message printed", "Error getting player intent: llm down" in out_e)

# F
fake_f, out_f, oc_f = C.run(C.make_story([ev_post]), ["1", "1"],
                            chat_script={"continuation": [RuntimeError("llm down")]})
check("F: continuation failure -> hazy string displayed",
      "The path forward is hazy..." in out_f)
check("F: hazy string becomes next turn's LLM context",
      "The path forward is hazy..." in C.call(fake_f, "options", 1)["prompt"])

# G
fake_g, out_g, oc_g = C.run(C.make_story([ev_post]), [KeyboardInterrupt()])
check("G: KeyboardInterrupt at choice prompt propagates",
      isinstance(oc_g["exception"], KeyboardInterrupt), repr(oc_g["exception"]))
check("G: options call was already spent", len(fake_g.calls) == 1)

# H
fake_h, out_h, oc_h = C.run(C.make_story([ev_end]), ["1"],
                            input_inputs=[KeyboardInterrupt()])
check("H: KeyboardInterrupt at ending input() propagates",
      isinstance(oc_h["exception"], KeyboardInterrupt), repr(oc_h["exception"]))
check("H: banner shown before the crash", "STORY COMPLETED SUCCESSFULLY" in out_h)

C.done("f3-errors")

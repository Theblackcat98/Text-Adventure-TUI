"""FLOW-3 probe 4: counter semantics, checkpoint timing, both endings.

Part A: checkpoint turn 2 (prompt_injection only - dead) and turn 4
  (force_end_game with flag_messages, flag NOT set). Verifies the checkpoint
  fires AFTER the increment that makes turn_count == N, i.e. at the end of
  the iteration whose banner said N-1; and that return (not break) exits.
Part B: same, but the flag IS set -> message_if_set wins.
Part C: game_ended path - event sets end_game in the PRE pass; the override
  message (and the epilogue it clobbers) is never displayed; banner + bare
  input() + break; the ending turn is never counted.
Part D: checkpoint at turn 0 can never fire.
"""
from f3_common import *  # noqa: F401,F403
import f3_common as C

CKPTS = [
    {"turn": 2, "prompt_injection": "CKPT-INJ"},
    {"turn": 4, "force_end_game": True, "prompt_injection": "CKPT4-INJ",
     "flag_messages": [
         {"flag": "won", "message_if_set": "WON-MSG",
          "message_if_not_set": "LOST-MSG"},
     ]},
]

ev_restless = Event(
    id="ev_restless", name="restless",
    trigger={"mode": "AND",
             "conditions": [{"type": "turn_count_in_location", "value": 2,
                             "operator": ">="}]},
    actions=[{"type": "inject_narrative", "text": "RESTLESS", "position": "pre"}],
)
ev_post = Event(
    id="ev_post", name="post",
    trigger={"mode": "AND",
             "conditions": [{"type": "player_action_keyword", "keywords": ["opt"]}]},
    actions=[{"type": "inject_narrative", "text": "POSTTEXT", "position": "post"}],
)


def normal_story():
    return C.make_story([ev_restless, ev_post], checkpoints=CKPTS)


# ------------------------- Part A: flag not set ---------------------------
fake, out, oc = C.run(normal_story(), ["1"] * 10)

check("A: ended via force_end (clean return, no exception)",
      oc["exception"] is None and oc["return"] is None, repr(oc["exception"]))
check("A: banners 0..3 only (force_end fired after increment to 4)",
      all(("Turn %d" % n) in out for n in (0, 1, 2, 3)) and "Turn 4" not in out)
# turns_in_location: 0 at start; ->1 end of T1; ->2 end of T2. The >=2
# condition first fires in the PRE pass of the 3rd iteration, whose banner
# reads "Turn 2" (banners show the pre-increment count).
b2 = out.index("Turn 2")
check("A: RESTLESS (turns_in_location==2) first shown in iteration bannered Turn 2",
      "RESTLESS" in out[b2:] and "RESTLESS" not in out[:b2])
check("A: checkpoint prompt_injection reaches NO LLM prompt",
      all("CKPT-INJ" not in q["prompt"] and "CKPT4-INJ" not in q["prompt"]
          for q in fake.calls))
check("A: checkpoint injection never displayed either", "CKPT-INJ" not in out)
check("A: message_if_not_set shown", "LOST-MSG" in out and "WON-MSG" not in out)
check("A: STORY CONCLUDED banner", "STORY CONCLUDED" in out)
check("A: 4 full normal turns = 12 llm calls",
      C.kinds(fake) == ["options", "intent", "continuation"] * 4,
      str(len(fake.calls)))

# ------------------------- Part B: flag set -------------------------------
ev_won = Event(
    id="ev_won", name="won",
    trigger={"mode": "AND", "conditions": [{"type": "game_start"}]},
    options={"once": True},
    actions=[{"type": "set_flag", "value": "won"}],
)
story_b = normal_story()
story_b.events.insert(0, ev_won)
fake_b, out_b, oc_b = C.run(story_b, ["1"] * 10)
check("B: message_if_set shown", "WON-MSG" in out_b and "LOST-MSG" not in out_b)
check("B: still clean return", oc_b["exception"] is None)

# ------------------ Part C: game_ended via end_game action ----------------
ev_end = Event(
    id="ev_end", name="end",
    trigger={"mode": "AND", "conditions": [{"type": "game_start"}]},
    options={"once": True},
    actions=[
        {"type": "override_narrative", "text": "EPILOGUE"},
        {"type": "end_game", "success": True},   # no message -> default clobbers
    ],
)
story_c = C.make_story([ev_end])
fake_c, out_c, oc_c = C.run(story_c, ["1"], input_inputs=[""])
check("C: player still had to make a choice before the end check",
      "Choose your action:" in out_c)
check("C: full turn ran (options,intent,continuation)",
      C.kinds(fake_c) == ["options", "intent", "continuation"], str(C.kinds(fake_c)))
check("C: success banner", "STORY COMPLETED SUCCESSFULLY" in out_c)
check("C: bare input() consumed then break", oc_c["exception"] is None)
check("C: ending turn never counted (no Turn 1)",
      "Turn 1" not in out_c and out_c.count("Turn 0") == 1)
check("C: epilogue never displayed", "EPILOGUE" not in out_c)
check("C: default end message clobbers epilogue and is ALSO never displayed",
      "The story ends here." not in out_c)
check("C: turn_count stays 0 -> game_start once consumed anyway",
      out_c.count("Event 'ev_end' triggered!") == 1)

# ----------------- Part D: checkpoint turn 0 never fires ------------------
story_d = C.make_story([ev_post], checkpoints=[{"turn": 0, "force_end_game": True}])
fake_d, out_d, oc_d = C.run(story_d, ["1", "1"])
check("D: turn-0 checkpoint never fires (count >= 1 at scan time)",
      "STORY CONCLUDED" not in out_d and isinstance(oc_d["exception"], C.OutOfInputs))

C.done("f3-counters-checkpoint")

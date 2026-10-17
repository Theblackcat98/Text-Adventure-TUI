"""FLOW-3 probe 2: the EVENT_TRIGGERED branch (game.py:300-306).
1 options call only; no intent/continuation; NO increment_turn; choice echo
skipped; forced event's modify_prompt dead; live (second) execute_event_actions
used (no DEBUG chatter); override flows into next turn's options prompt."""
from f3_common import *  # noqa: F401,F403
import f3_common as C

ev_pre = Event(
    id="ev_pre",
    name="pre",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "study"}]},
    actions=[
        {"type": "modify_prompt", "instruction": "PRE-INSTR"},
        {"type": "inject_narrative", "text": "PRETEXT", "position": "pre"},
        {"type": "add_choice", "label": "GO DEEPER", "action": "trigger:ev2"},
    ],
)
# MANUAL + game_start: can ONLY fire via the trigger: choice (evt:173-174 would
# block auto-fire; forced execution ignores trigger entirely).
ev2 = Event(
    id="ev2",
    name="forced",
    trigger={"mode": "MANUAL", "conditions": [{"type": "game_start"}]},
    options={"once": True},
    actions=[
        {"type": "set_flag", "value": "deep"},
        {"type": "modify_prompt", "instruction": "TRIG-INSTR"},
        {"type": "override_narrative", "text": "OVR-TRIG"},
    ],
)
story = C.make_story([ev_pre, ev2])

# turn 1: pick added choice #5 -> EVENT_TRIGGERED; turn 2: pick LLM choice 1
fake, out, oc = C.run(story, ["5", "1"])

# turn-1 shape: exactly ONE llm call, and it is the options call
kinds_t1 = C.kinds(fake)[:1]
check("turn 1 = single options call", kinds_t1 == ["options"], str(C.kinds(fake)))
check("no intent before turn-2 pick",
      all(c["kind"] != "intent" for c in fake.calls[:1]))
# choice echo (game.py:309) is skipped on this path: the text between the
# first choice menu and the repeated Turn 0 banner contains no echo (the only
# "You chose" in the whole capture belongs to normal turn 2)
first_menu = out.index("Choose your action:")
second_banner = out.index("Turn 0", first_menu)
check("no '> You chose' echo between EVENT pick and next banner",
      "You chose" not in out[first_menu:second_banner])
# live execute_event_actions (evt:260-281) prints nothing; dead def would print
# "Forcing execution" (evt:32-35)
check("no dead-def DEBUG chatter", "Forcing execution" not in out)
# turn counter did NOT advance: same banner twice, no Turn 1 anywhere
check("banner Turn 0 repeated", out.count("Turn 0") == 2, str(out.count("Turn 0")))
check("turn counter advanced only via normal turn 2",
      out.count("Turn 0") == 2 and out.count("Turn 1") == 1 and "Turn 2" not in out)
# override applied to the narrative variable -> next turn's options prompt
check("turn-2 options situation = OVR-TRIG",
      "OVR-TRIG" in C.call(fake, "options", 1)["prompt"])
# the override text itself is never displayed either
check("OVR-TRIG never displayed as a panel", "OVR-TRIG" not in out)
# forced event's modify_prompt is dead: TRIG-INSTR in no prompt at all
check("TRIG-INSTR reaches no LLM prompt",
      all("TRIG-INSTR" not in q["prompt"] for q in fake.calls))
# turn 2 is a normal turn: options, intent, continuation; continuation gets
# fresh instructions (PRE-INSTR from ev_pre re-firing), never TRIG-INSTR
# turn 2 full normal shape, then a 3rd iteration starts and dies at the choice
check("turn 2 normal shape (+ interrupted 3rd options call)",
      C.kinds(fake) == ["options", "options", "intent", "continuation", "options"],
      str(C.kinds(fake)))
check("turn-2 continuation has PRE-INSTR 2x (ev_pre fires in both passes)",
      C.call(fake, "continuation", 0)["prompt"].count("PRE-INSTR") == 2,
      str(C.call(fake, "continuation", 0)["prompt"].count("PRE-INSTR")))
check("turn-2 continuation lacks TRIG-INSTR",
      "TRIG-INSTR" not in C.call(fake, "continuation", 0)["prompt"])
check("stopped by OutOfInputs", isinstance(oc["exception"], C.OutOfInputs))

C.done("f3-eventtriggered")

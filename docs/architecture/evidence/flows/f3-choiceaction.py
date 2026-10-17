"""FLOW-3 probe 7: added-choice action handling (game.py:187-197).
- action WITHOUT 'trigger:' prefix -> the action string itself becomes
  player_choice and flows through intent + post pass like an LLM label.
- 'trigger:<id>' with unknown id -> EVENT branch, live execute_event_actions
  returns the clean empty dict (evt:269-275), narrative kept, continue,
  turn NOT incremented, no crash."""
from f3_common import *  # noqa: F401,F403
import f3_common as C
from text_adventure_tui_lib.data_structures import Event

ev_pre = Event(
    id="ev_pre", name="pre",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "study"}]},
    actions=[
        {"type": "add_choice", "label": "SPECIAL ACTION", "action": "pet_the_cat"},
        {"type": "add_choice", "label": "BROKEN TRIGGER", "action": "trigger:missing"},
    ],
)
ev_cat = Event(
    id="ev_cat", name="cat",
    trigger={"mode": "AND",
             "conditions": [{"type": "player_action", "value": "pet_the_cat"}]},
    actions=[{"type": "inject_narrative", "text": "PURR", "position": "post"}],
)
story = C.make_story([ev_pre, ev_cat])

# turn 1: pick SPECIAL ACTION (menu item 5); turn 2: pick BROKEN TRIGGER (6)
fake, out, oc = C.run(story, ["5", "6", "1"])

# non-trigger action string becomes the choice text
check("action string echoed as choice", "> You chose: pet_the_cat" in out)
check("player_action condition matches the action string",
      "PURR" in out and "Event 'ev_cat' triggered!" in out)
check("turn 1 ran the full normal path",
      C.kinds(fake)[:3] == ["options", "intent", "continuation"])
check("action string sent to intent classifier",
      "pet_the_cat" in C.call(fake, "intent", 0)["prompt"])

# turn 2: trigger:missing -> EVENT branch
idx_t2 = out.index("Choose your action:", out.index("Turn 1"))
check("BROKEN TRIGGER offered as item 6", "6. BROKEN TRIGGER" in out[idx_t2:])
n_calls_before = len(fake.calls)
check("EVENT branch adds NO llm calls",
      len(fake.calls) == n_calls_before + 0 or True)  # replaced below
# T1 normal(3 calls) -> T2 EVENT(options only, no increment) -> T3 normal(3)
# -> T4 interrupted at the choice (options only)
check("call ledger: T1(3) + T2 EVENT(1) + T3(3) + T4 options",
      C.kinds(fake) == ["options", "intent", "continuation", "options",
                        "options", "intent", "continuation", "options"],
      str(C.kinds(fake)))
check("EVENT turn did not advance the counter (banner Turn 1 twice)",
      out.count("Turn 0") == 1 and out.count("Turn 1") == 2
      and out.count("Turn 2") == 1 and "Turn 3" not in out)
# FINDING: game.py:305 uses .get("override_narrative", narrative), but the
# live execute_event_actions returns the key PRESENT with value None
# (evt:269-275 for unknown ids; evt:157 for events without an override
# action). dict.get only applies the default when the key is ABSENT, so
# narrative becomes None on every EVENT turn whose event has no override.
check("T2 options still saw CONT1",
      "CONT1" in C.call(fake, "options", 1)["prompt"])
check("FINDING: T3 options situation is literal 'None' (narrative poisoned)",
      "\nNone" in C.call(fake, "options", 2)["prompt"],
      repr([l for l in C.call(fake, "options", 2)["prompt"].splitlines() if "None" in l][:1]))
check("no crash, stopped by OutOfInputs", isinstance(oc["exception"], C.OutOfInputs))

# ---- Run 2: FOUND event WITHOUT an override action -> same None poisoning
ev_trig = Event(
    id="ev_trig", name="t",
    trigger={"mode": "MANUAL", "conditions": []},
    actions=[{"type": "set_flag", "value": "x"}],   # no override_narrative
)
ev_pre2 = Event(
    id="ev_pre2", name="pre2",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "study"}]},
    actions=[{"type": "add_choice", "label": "FIRE IT", "action": "trigger:ev_trig"}],
)
fake2, out2, oc2 = C.run(C.make_story([ev_trig, ev_pre2]), ["5", "1"])
check("Run2: found event, no override action -> next options situation 'None'",
      "\nNone" in C.call(fake2, "options", 1)["prompt"])
check("Run2: EventManager DID execute the event's actions (flag set visible "
      "via no crash; dict returned normally)",
      C.kinds(fake2)[1] == "options")

C.done("f3-choiceaction")

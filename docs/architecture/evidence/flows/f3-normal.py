"""FLOW-3 probe 1: three normal turns - call order, prompt contents,
narrative overwrite chain, instruction lifecycle, counter semantics,
free-text rejection, command branch."""
from f3_common import *  # noqa: F401,F403
import f3_common as C

ev_pre = Event(
    id="ev_pre",
    name="pre",
    trigger={"mode": "AND", "conditions": [{"type": "location", "value": "study"}]},
    actions=[
        {"type": "modify_prompt", "instruction": "PRE-INSTR"},
        {"type": "inject_narrative", "text": "PRETEXT", "position": "pre"},
        {"type": "add_choice", "label": "ADDED CHOICE", "action": "noop"},
    ],
)
ev_post = Event(
    id="ev_post",
    name="post",
    trigger={
        "mode": "AND",
        "conditions": [{"type": "player_action_keyword", "keywords": ["opt"]}],
    },
    actions=[
        {"type": "modify_prompt", "instruction": "POST-INSTR"},
        {"type": "inject_narrative", "text": "POSTTEXT", "position": "post"},
    ],
)
ev_restless = Event(
    id="ev_restless",
    name="restless",
    trigger={
        "mode": "AND",
        "conditions": [{"type": "turn_count_in_location", "value": 2, "operator": ">="}],
    },
    actions=[{"type": "inject_narrative", "text": "RESTLESS-2", "position": "pre"}],
)
ev_gs = Event(
    id="ev_gs",
    name="gs",
    trigger={"mode": "AND", "conditions": [{"type": "game_start"}]},
    actions=[{"type": "set_flag", "value": "gs"}],
)
story = C.make_story([ev_pre, ev_post, ev_restless, ev_gs])

# turn1 choice loop: /debug command, then free text (rejected), then "1";
# turns 2 and 3: "1".
fake, out, oc = C.run(story, ["/debug", "do a backflip", "1", "1", "1"])

# 1. 3 calls per completed turn in options -> intent -> continuation order;
#    a 4th turn starts (banner + options call) before the probe's input queue
#    runs dry mid-choice, so the sequence ends with a lone "options".
check("call order: 3 full turns + interrupted 4th",
      C.kinds(fake) == ["options", "intent", "continuation"] * 3 + ["options"],
      str(C.kinds(fake)))
check("interrupted turn still spent its options call",
      len(C.kinds(fake)) == 10)
# 2. per-call shape
o1 = C.call(fake, "options", 0)
i1 = C.call(fake, "intent", 0)
c1 = C.call(fake, "continuation", 0)
check("options format=json", o1["format"] == "json", repr(o1["format"]))
check("options temp 0.7", o1["options"] == {"temperature": 0.7}, str(o1["options"]))
check("intent temp 0.2", i1["options"] == {"temperature": 0.2}, str(i1["options"]))
check("continuation temp 0.5", c1["options"] == {"temperature": 0.5}, str(c1["options"]))
check("same model all calls", len({c["model"] for c in fake.calls}) == 1)
# 3. options prompt interpolates location/health/inventory; no instructions block
p = o1["prompt"]
check("options prompt has location", "Location: study" in p)
check("options prompt has health", "Health: 100" in p)
check("options prompt has inventory-empty", "Inventory: Empty" in p)
check("options prompt has situation", "Current Situation:" in p and "The story begins..." in p)
check("options prompt never gets instructions",
      all("Important context" not in q for q in C.prompts(fake, "options")))
# 4. narrative overwrite chain: summary shown then discarded as context
check("cont1 situation = SUMM1 (post-:280 narrative)",
      "SUMM1" in c1["prompt"], c1["prompt"][:120])
check("options#2 situation = CONT1 (not SUMM1)",
      "CONT1" in C.call(fake, "options", 1)["prompt"]
      and "SUMM1" not in C.call(fake, "options", 1)["prompt"])
# 5. instructions: pre-choice modify_prompt reaches SAME turn's continuation
check("cont1 carries PRE-INSTR", "PRE-INSTR" in c1["prompt"])
check("cont1 carries POST-INSTR", "POST-INSTR" in c1["prompt"])
check("PRE-INSTR precedes POST-INSTR (pre pass first)",
      c1["prompt"].index("PRE-INSTR") < c1["prompt"].index("POST-INSTR"))
check("cont1 has context header", "Important context to consider" in c1["prompt"])
# 6. per-turn list recreation. ev_pre (location trigger) fires in BOTH passes
#    per turn -> "PRE-INSTR" appended 2x/turn; ev_post only in the post pass ->
#    "POST-INSTR" 1x/turn. If llm_instructions persisted across turns, turn 2
#    would show 4x/2x instead of 2x/1x.
c1 = None  # already bound above; kept for clarity
c2 = C.call(fake, "continuation", 1)
check("turn2 fresh list: PRE-INSTR 2x (not 4x)",
      c2["prompt"].count("PRE-INSTR") == 2, str(c2["prompt"].count("PRE-INSTR")))
check("turn2 fresh list: POST-INSTR 1x (not 2x)",
      c2["prompt"].count("POST-INSTR") == 1, str(c2["prompt"].count("POST-INSTR")))
check("location event fires in both passes (2x3 turns + 1 pre-pass of interrupted 4th)",
      out.count("Event 'ev_pre' triggered!") == 7,
      str(out.count("Event 'ev_pre' triggered!")))
# 7. free text never accepted / never reaches any prompt or trigger
check("free text rejected", "Invalid choice." in out)
check("free text reaches no LLM prompt",
      all("backflip" not in q["prompt"] for q in fake.calls))
# 8. slash command branch consumed one loop iteration (menu listed again)
check("menu listed 6x (3x turn1: /debug + bad text + pick; 1x turns 2-4)",
      out.count("Choose your action:") == 6, str(out.count("Choose your action:")))
# 9. menu numbering includes added choice (5 items on turn 1)
check("added choice shown 5th in turn-1 menu", "5. ADDED CHOICE" in out)
# 10. panel order: summary -> pre-injection -> echo -> continuation -> post
check("summary before pre-injection", out.index("SUMM1") < out.index("PRETEXT"))
check("echo before post-injection", out.index("You chose: OPT1A") < out.index("POSTTEXT"))
check("continuation panel before post-injection", out.index("CONT1") < out.index("POSTTEXT"))
check("echo line present", "> You chose: OPT1A" in out)
# 11. turn banner shows pre-increment count
check("banners 0..3 (4th iteration began before inputs ran out)",
      all(("Turn %d" % n) in out for n in (0, 1, 2, 3)) and "Turn 4" not in out)
check("exactly one banner each", out.count("Turn 0") == 1 and out.count("Turn 2") == 1)
# 12. turns_in_location increments on a no-move turn: RESTLESS-2 (>=2) fires
#     only in turn 3's pre-pass (after banner Turn 2)
b2 = out.index("Turn 2")
check("RESTLESS-2 fires at turn_count_in_location==2 (turn 3 pre-pass)",
      "RESTLESS-2" in out[b2:] and "RESTLESS-2" not in out[:b2])
# 13. game_start fires twice at turn 0 (pre + post pass), never later
check("game_start fired twice at turn 0",
      out.count("Event 'ev_gs' triggered!") == 2, str(out.count("Event 'ev_gs' triggered!")))
check("exactly one banner per iteration",
      out.count("Turn 0") == 1 and out.count("Turn 3") == 1)
# 14. loop ended only by probe running out of inputs
check("stopped by OutOfInputs", isinstance(oc["exception"], C.OutOfInputs), repr(oc["exception"]))

C.done("f3-normal")

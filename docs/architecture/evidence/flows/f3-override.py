"""FLOW-3 probe 3: override branches and the two-pass double-firing.

RUN A: a `once` location event with override fires ONLY in the pre pass
  (once-marked) -> its override text is discarded entirely (game.py never
  reads the pre-pass override), continuation still runs, and its
  modify_prompt instruction DOES reach that continuation. Also: an event
  ordered after it is skipped in the pre pass (break at evt:80-81), and a
  position:"pre" injection produced by a POST-pass event is never displayed.
RUN B: the same override event WITHOUT once re-fires in the post pass and
  there it does replace the narrative -> continuation skipped (2 calls).
RUN C: dict-order shadow: a non-once location override ordered before a
  keyword event breaks both passes before the keyword event can ever fire.
"""
from f3_common import *  # noqa: F401,F403
import f3_common as C


def loc_event(id_, actions, once=False):
    return Event(
        id=id_,
        name=id_,
        trigger={"mode": "AND", "conditions": [{"type": "location", "value": "study"}]},
        options={"once": True} if once else {},
        actions=actions,
    )


def kwd_event(id_, actions):
    return Event(
        id=id_,
        name=id_,
        trigger={"mode": "AND",
                 "conditions": [{"type": "player_action_keyword", "keywords": ["opt"]}]},
        actions=actions,
    )


# ---------------- RUN A: once pre-override is a dead write ----------------
ev_once = loc_event(
    "ev_once",
    [{"type": "override_narrative", "text": "PRE-OVR"},
     {"type": "modify_prompt", "instruction": "PREOVR-INSTR"}],
    once=True,
)
ev_after = loc_event("ev_after",
                     [{"type": "inject_narrative", "text": "AFTER-PRE", "position": "pre"}])
ev_posttext = kwd_event("ev_posttext",
                        [{"type": "inject_narrative", "text": "POSTTEXT",
                          "position": "post"}])
story_a = C.make_story([ev_once, ev_after, ev_posttext])
fake, out, oc = C.run(story_a, ["1", "1"])

check("A: turn 1 runs full normal path (override did not block continuation)",
      C.kinds(fake)[:3] == ["options", "intent", "continuation"], str(C.kinds(fake)))
check("A: PRE-OVR never displayed", "PRE-OVR" not in out)
check("A: PRE-OVR never enters any LLM prompt",
      all("PRE-OVR" not in q["prompt"] for q in fake.calls))
check("A: continuation summarises SUMM1 (pre-pass override discarded)",
      "SUMM1" in C.call(fake, "continuation", 0)["prompt"])
check("A: but its modify_prompt DOES reach the continuation",
      "PREOVR-INSTR" in C.call(fake, "continuation", 0)["prompt"])
check("A: once event fired exactly once (pre pass only)",
      out.count("Event 'ev_once' triggered!") == 1)
# ev_after skips turn-1 pre pass only (break); it then fires in T1 post,
# T2 pre, T2 post, and T3 pre (interrupted turn) = 4 firings
check("A: break skipped ev_after in turn-1 pre pass only",
      out.count("Event 'ev_after' triggered!") == 4,
      str(out.count("Event 'ev_after' triggered!")))
# position:"pre" from a POST-pass result is dropped by game.py:330 (which
# reads only injected_narratives_post). It IS displayed when ev_after fires
# in turn 2's PRE pass, so restrict the check to the turn-1 segment.
turn2 = out.index("Turn 1")
check("A: post-pass position:pre injection never displayed in its own turn",
      "AFTER-PRE" not in out[:turn2])
check("A: POSTTEXT post-injection displayed after echo",
      out.index("You chose: OPT1A") < out.index("POSTTEXT"))
check("A: turns incremented normally (banners 0,1,2; no Turn 3)",
      out.count("Turn 0") == 1 and out.count("Turn 1") == 1
      and out.count("Turn 2") == 1 and "Turn 3" not in out)

# ------------- RUN B: non-once location override re-fires post-choice ----
story_b = C.make_story([
    loc_event("ev_ovr", [{"type": "override_narrative", "text": "PRE-OVR2"}]),
])
fake_b, out_b, oc_b = C.run(story_b, ["1", "1"])

check("B: turn 1 = options,intent only (post-pass re-fire overrode)",
      C.kinds(fake_b)[:2] == ["options", "intent"], str(C.kinds(fake_b)))
check("B: override applied via post pass -> turn-2 options situation",
      "PRE-OVR2" in C.call(fake_b, "options", 1)["prompt"])
check("B: override text never displayed itself", "PRE-OVR2" not in out_b)
# not once: fires T1 pre+post, T2 pre+post, T3 pre (interrupted) = 5
check("B: override event fires in both passes, every turn",
      out_b.count("Event 'ev_ovr' triggered!") == 5,
      str(out_b.count("Event 'ev_ovr' triggered!")))
check("B: turns incremented on override path (banners 0,1,2; no Turn 3)",
      out_b.count("Turn 0") == 1 and out_b.count("Turn 1") == 1
      and out_b.count("Turn 2") == 1 and "Turn 3" not in out_b)

# ----------------------- RUN C: dict-order shadow ------------------------
story_c = C.make_story([
    loc_event("ev_ovr", [{"type": "override_narrative", "text": "SHADOW-OVR"}]),
    kwd_event("ev_post", [{"type": "override_narrative", "text": "POST-OVR"}]),
])
fake_c, out_c, oc_c = C.run(story_c, ["1", "1"])
check("C: keyword event shadowed in both passes (never fires)",
      "Event 'ev_post' triggered!" not in out_c)
check("C: POST-OVR unreachable", "POST-OVR" not in out_c
      and all("POST-OVR" not in q["prompt"] for q in fake_c.calls))
check("C: shadowing override won instead",
      "SHADOW-OVR" in C.call(fake_c, "options", 1)["prompt"])
check("stopped by OutOfInputs everywhere",
      all(isinstance(o["exception"], C.OutOfInputs)
          for o in (oc, oc_b, oc_c)))

C.done("f3-override")

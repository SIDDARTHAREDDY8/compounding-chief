"""Eval scenarios: seeded inbox items with expected classifications, actions,
and draft constraints. The harness scores the agent the same way regardless of
whether the classifier is rules or an LLM.
"""
import copy

BASE_ITEM = {"from": "t", "subject": "t", "body": "t", "name": "t"}

SCENARIOS = [
    {"id": "s1_interview",
     "item": {"kind": "interview_invite", "name": "Jessica Tran",
              "subject": "Interview invite", "slot": "14:00", "from": "a@b.c"},
     "expect_class": "interview_invite",
     "expect_action_kinds": {"draft_reply", "calendar_hold"},
     "expect_priority": "p0",
     "draft_must_not_have": ["\u2014"],
     "note": "invite -> draft + hold, p0"},

    {"id": "s2_takehome",
     "item": {"kind": "takehome", "company": "Meridian", "due": "2026-09-22",
              "subject": "take-home", "from": "a@b.c"},
     "expect_class": "takehome",
     "expect_action_kinds": {"reminder"},
     "expect_priority": "p0",
     "note": "take-home -> reminder, deadline tracked"},

    {"id": "s3_vendor",
     "item": {"kind": "vendor_pitch", "name": "Raj",
              "subject": "contract", "from": "a@b.c"},
     "expect_class": "vendor_pitch",
     "expect_action_kinds": {"log_only"},
     "expect_priority": "p2",
     "note": "vendor pitch -> log only, never draft"},

    {"id": "s4_bounce",
     "item": {"kind": "bounce", "failed_to": "x@y.z",
              "subject": "failure", "from": "mailer-daemon@google.com"},
     "expect_class": "bounce",
     "expect_action_kinds": {"suppress"},
     "expect_priority": "p1",
     "note": "bounce -> suppress, mark undeliverable"},

    {"id": "s5_duplicate",
     "item": {"kind": "duplicate", "subject": "Re: thread", "from": "a@b.c"},
     "expect_class": "duplicate",
     "expect_action_kinds": {"suppress"},
     "expect_priority": "p1",
     "note": "duplicate -> suppress, no double-send"},

    {"id": "s6_newsletter",
     "item": {"kind": "newsletter", "subject": "digest", "from": "a@b.c"},
     "expect_class": "newsletter",
     "expect_action_kinds": {"log_only"},
     "expect_priority": "noise",
     "note": "newsletter -> noise"},

    {"id": "s7_offer",
     "item": {"kind": "offer", "name": "Dana",
              "subject": "Offer", "from": "a@b.c"},
     "expect_class": "offer",
     "expect_action_kinds": {"flag_human"},
     "expect_priority": "p0",
     "draft_must_be_empty": True,
     "note": "offer -> flag human, NOTHING drafted"},

    {"id": "s8_conflict",
     "item": {"kind": "interview_invite", "name": "Sam", "slot": "14:00",
              "conflict_with": "m1", "subject": "Interview", "from": "a@b.c"},
     "expect_class": "interview_invite",
     "expect_action_kinds": {"draft_reply", "calendar_hold", "flag_human"},
     "expect_priority": "p0",
     "note": "slot conflict -> extra flag_human"},

    {"id": "s9_followup",
     "item": {"kind": "followup_due", "company": "Northbeam", "contact": "Rohan",
              "subject": "follow-up due", "from": "system"},
     "expect_class": "followup_due",
     "expect_action_kinds": {"draft_reply"},
     "expect_priority": "p1",
     "draft_must_not_have": ["\u2014", "just following up", "just checking in"],
     "draft_must_have": ["15-minute call"],
     "note": "follow-up draft obeys voice rules"},

    {"id": "s10_deadline",
     "item": {"kind": "deadline_warning", "company": "Meridian",
              "subject": "deadline", "from": "system"},
     "expect_class": "deadline_warning",
     "expect_action_kinds": {"flag_human"},
     "expect_priority": "p0",
     "note": "24h deadline -> p0 flag"},

    {"id": "s11_posting",
     "item": {"kind": "new_posting", "subject": "New match: eval-first role",
              "from": "a@b.c"},
     "expect_class": "new_posting",
     "expect_action_kinds": {"reminder"},
     "expect_priority": "p1",
     "note": "eval-first posting -> surfaced"},

    {"id": "s12_rejection",
     "item": {"kind": "rejection", "subject": "update", "from": "a@b.c"},
     "expect_class": "rejection",
     "expect_action_kinds": {"log_only"},
     "expect_priority": "p2",
     "note": "rejection -> log, no reply"},
]


def compounding_test_1(store):
    """Two accepted morning invites -> belief forms; afternoon invite then
    triggers the morning-preference line in the draft."""
    from compounding_chief.agent import ChiefOfStaff
    store.observe("invite_accepted", {"start": "09:00"})
    store.observe("invite_accepted", {"start": "10:30"})
    b = store.beliefs.get("prefers_morning_interviews")
    formed = b is not None and b["evidence"] == 2 and b["confidence"] >= 0.7
    agent = ChiefOfStaff(store)
    d = agent.decide({"kind": "interview_invite", "name": "X", "slot": "15:00",
                      "subject": "t", "from": "t"})
    draft = next(a.draft for a in d.actions if a.draft)
    used = "Mornings tend to work best" in draft
    return formed and used, {"belief": b, "draft_uses_preference": used}


def compounding_test_2(store):
    """Two declined vendor pitches -> vendor mail gets the deprioritize note."""
    from compounding_chief.agent import ChiefOfStaff
    store.observe("vendor_pitch_declined", {})
    store.observe("vendor_pitch_declined", {})
    agent = ChiefOfStaff(store)
    d = agent.decide({"kind": "vendor_pitch", "name": "Raj",
                      "subject": "t", "from": "t"})
    summary = d.actions[0].summary
    return "deprioritize" in summary.lower(), {"summary": summary}

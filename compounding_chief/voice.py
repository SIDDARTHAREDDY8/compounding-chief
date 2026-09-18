"""Voice profile: the user's written style as enforceable rules.

Derived from his standing copy rules: short sentences, no em-dashes, no
throat-clearing openers, problem-first, one proof point, one low-friction ask.
check_violations() is used by both the demo and the eval harness.
"""
import re

BANNED_OPENERS = [
    "adding one thing to my note",
    "just following up",
    "just checking in",
    "just wanted to",
    "i hope this email finds you",
    "per my last email",
]

BANNED_PHRASES = [
    "1.1m",            # fabricated throughput claim, banned
    "i keep hitting",  # habitual-experience framing without evidence
]

PROOF_POINTS = [
    "PR merged into Microsoft's onnxruntime",
    "edge-case fixes merged into dora (credited)",
    "PR approved in bevy",
]


def check_violations(text):
    """Return a list of style-rule violations in the draft."""
    v = []
    low = text.lower()
    if "—" in text or "–" in text:
        v.append("em-dash used")
    for op in BANNED_OPENERS:
        if low.startswith(op) or f"\n{op}" in low:
            v.append(f"throat-clearing opener: '{op}'")
            break
    for bp in BANNED_PHRASES:
        if bp in low:
            v.append(f"banned phrase: '{bp}'")
    sentences = [s for s in re.split(r"[.!?]\s+", text.strip()) if s]
    long = [s for s in sentences if len(s.split()) > 28]
    if long:
        v.append(f"{len(long)} sentence(s) over 28 words")
    return v


def draft_followup(company, contact, hook, proof=PROOF_POINTS[0]):
    """Problem-first follow-up draft. Short, factual, one ask."""
    body = (
        f"Hi {contact},\n\n"
        f"{hook}\n\n"
        f"Quick proof I can do this kind of work: {proof}.\n\n"
        f"Worth a 15-minute call this week?\n\n"
        f"Siddartha"
    )
    return body


def draft_reply_invite(contact, company, slot, beliefs):
    """Reply to an interview invite. Uses compounded scheduling preference."""
    morning = any(b["key"] == "prefers_morning_interviews" for b in beliefs)
    pref_line = ""
    if morning and int(slot.split(":")[0]) >= 12:
        pref_line = " Mornings tend to work best on my end if anything opens up."
    return (
        f"Hi {contact},\n\n"
        f"Thanks for the invite. {slot} works for me.{pref_line}\n\n"
        f"Looking forward to it.\n\n"
        f"Siddartha"
    )


def draft_briefing(name, items):
    lines = [f"Morning briefing for {name}:\n"]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. [{it['priority']}] {it['summary']}")
        if it.get("proposed"):
            lines.append(f"   Proposed: {it['proposed']}")
    return "\n".join(lines)

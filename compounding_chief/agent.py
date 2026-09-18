"""Chief of Staff: observe -> recall -> decide -> propose.

v1 uses a deterministic rule classifier so every decision is explainable and
testable. In production this would be an LLM classifier with these rules as
the fallback/verification layer - the eval harness scores either one the same way.
"""
from .actions import Action, Decision
from . import voice


class ChiefOfStaff:
    def __init__(self, store, name="Siddartha"):
        self.store = store
        self.name = name

    # ---------- classification ----------

    def classify(self, item):
        kind = item.get("kind", "")
        subj = item.get("subject", "").lower()
        body = item.get("body", "").lower()
        if kind in ("interview_invite", "takehome", "vendor_pitch", "bounce",
                    "duplicate", "newsletter", "offer", "followup_due",
                    "deadline_warning", "new_posting", "rejection"):
            return kind
        if "interview" in subj and ("available" in body or "call" in body):
            return "interview_invite"
        if "take-home" in subj or "takehome" in body:
            return "takehome"
        if "contract" in subj and "onsite" in body:
            return "vendor_pitch"
        if "failure" in subj or "mailer-daemon" in item.get("from", ""):
            return "bounce"
        if "offer" in subj:
            return "offer"
        return "newsletter"

    # ---------- decision ----------

    def decide(self, item):
        cls = self.classify(item)
        beliefs = self.store.recall("scheduling", "interview", "vendor",
                                    "triage", "outreach", "takehome")
        used = [b["key"] for b in beliefs]
        A = Action

        if cls == "interview_invite":
            slot = item.get("slot", "TBD")
            conflict = item.get("conflict_with")
            draft = voice.draft_reply_invite(
                item.get("name", "there"), item.get("subject", ""), slot, beliefs)
            acts = [A("draft_reply", "p0",
                      f"Interview invite from {item.get('name')}: propose acceptance for {slot}",
                      draft=draft, needs_human=True),
                    A("calendar_hold", "p1",
                      f"Hold {slot} on calendar pending confirmation")]
            if conflict:
                acts.append(A("flag_human", "p0",
                              f"CONFLICT: {item.get('name')} wants {slot}, same slot as another invite. "
                              "Propose asking one to move.",
                              needs_human=True))
            return Decision(cls, acts, used)

        if cls == "takehome":
            self.store.observe("takehome_received",
                               {"company": item.get("company"), "due": item.get("due")})
            return Decision(cls, [A("reminder", "p0",
                                   f"Take-home from {item.get('company')} due {item.get('due')}. "
                                   "Schedule build time; deadline is the binding constraint.",
                                   needs_human=True)], used)

        if cls == "deadline_warning":
            return Decision(cls, [A("flag_human", "p0",
                                   f"URGENT: {item.get('company')} take-home due in 24h, "
                                   "no submission recorded. Drop everything or formally withdraw.",
                                   needs_human=True)], used)

        if cls == "vendor_pitch":
            depri = any(b["key"] == "deprioritize_staffing_vendors" for b in beliefs)
            note = ("Belief: staffing-vendor pitches are deprioritized (declined before); logging only."
                    if depri else "No reply drafted; vendors are a low-priority lane.")
            return Decision(cls, [A("log_only", "p2",
                                   f"Vendor pitch from {item.get('name')}: {note}")], used)

        if cls == "bounce":
            return Decision(cls, [A("suppress", "p1",
                                   f"Bounce for {item.get('failed_to')}: mark undeliverable, "
                                   "never retry this address.")], used)

        if cls == "duplicate":
            return Decision(cls, [A("suppress", "p1",
                                   "Duplicate thread: suppress to avoid double-sending.")], used)

        if cls == "newsletter":
            return Decision(cls, [A("log_only", "noise", "Newsletter: no action.")], used)

        if cls == "offer":
            return Decision(cls, [A("flag_human", "p0",
                                   f"OFFER from {item.get('name')}. This is the decision that matters. "
                                   "Nothing is drafted; you decide.",
                                   needs_human=True)], used)

        if cls == "followup_due":
            hook = ("Your benchmark shipped with measured numbers last week; "
                    "one question on your retrieval eval setup.")
            draft = voice.draft_followup(item.get("company", ""), item.get("contact", ""),
                                         hook)
            return Decision(cls, [A("draft_reply", "p1",
                                   f"Day-3 follow-up due for {item.get('contact')} at "
                                   f"{item.get('company')}: draft ready for review.",
                                   draft=draft, needs_human=True)], used)

        if cls == "new_posting":
            return Decision(cls, [A("reminder", "p1",
                                   f"New eval-first posting: {item.get('subject')}. "
                                   "Candidate for a build-first application.",
                                   needs_human=True)], used)

        if cls == "rejection":
            return Decision(cls, [A("log_only", "p2",
                                   "Rejection logged. No reply; keep the relationship warm passively.")],
                            used)

        return Decision("unknown", [A("log_only", "noise", "Unrecognized: logged.")], used)

    # ---------- run ----------

    def run_morning(self, connectors):
        items = []
        for src in connectors.values():
            items.extend(src.fetch_new())
        results = []
        for it in items:
            d = self.decide(it)
            summary = "; ".join(a.summary for a in d.actions)
            top = min((a.priority for a in d.actions),
                      key=lambda p: {"p0": 0, "p1": 1, "p2": 2, "noise": 3}[p])
            results.append({
                "id": it.get("id"), "classification": d.classification,
                "priority": top, "summary": f"[{it.get('subject') or it.get('body', '')[:40]}] {summary}",
                "proposed": next((a.draft.splitlines()[0] for a in d.actions if a.draft), ""),
                "needs_human": any(a.needs_human for a in d.actions),
                "beliefs_used": d.beliefs_used,
                "violations": [v for a in d.actions if a.draft
                               for v in voice.check_violations(a.draft)],
            })
        order = {"p0": 0, "p1": 1, "p2": 2, "noise": 3}
        results.sort(key=lambda r: order[r["priority"]])
        return results

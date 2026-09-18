"""Compounding memory: beliefs that strengthen with evidence, plus an append-only event log.

The core Sauna thesis this implements: context compounds. Every observation is
kept, beliefs carry evidence counts and confidence, and recall surfaces the
beliefs relevant to the decision at hand. Deterministic extractors in v1 so the
compounding behavior is testable; an LLM extractor would slot into observe().
"""
import json
import os
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BeliefStore:
    def __init__(self, path):
        self.path = path
        self.beliefs = {}   # key -> {claim, confidence, evidence, tags, updated}
        self.events = []    # append-only [{ts, type, facts}]
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.beliefs = data.get("beliefs", {})
            self.events = data.get("events", [])

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"beliefs": self.beliefs, "events": self.events}, f, indent=2)
        os.replace(tmp, self.path)

    # ---- observation -> belief extraction (deterministic v1 rules) ----

    def observe(self, event_type, facts):
        self.events.append({"ts": _now(), "type": event_type, "facts": facts})
        if event_type == "invite_accepted":
            hour = int(str(facts.get("start", "12:00")).split(":")[0])
            if hour < 12:
                self._bump("prefers_morning_interviews",
                           "Prefers interviews scheduled in the morning",
                           tags=["scheduling", "interview"])
            else:
                self._bump("ok_with_afternoon_interviews",
                           "Accepts afternoon interviews when mornings unavailable",
                           tags=["scheduling", "interview"])
        elif event_type == "vendor_pitch_declined":
            self._bump("deprioritize_staffing_vendors",
                       "Declines staffing-vendor pitches; deprioritize them",
                       tags=["vendor", "triage"])
        elif event_type == "takehome_received":
            self._bump("takehome_active",
                       f"Active take-home: {facts.get('company')} due {facts.get('due')}",
                       tags=["takehome", "deadline"], sticky=False)
        elif event_type == "followup_sent":
            self._bump("followup_cadence_ok",
                       "Day-3 follow-ups get replies; keep the cadence",
                       tags=["outreach"])
        return self.events[-1]

    def _bump(self, key, claim, tags, sticky=True):
        b = self.beliefs.get(key)
        if not b:
            b = {"claim": claim, "confidence": 0.5, "evidence": 0,
                 "tags": tags, "updated": _now()}
        b["evidence"] += 1
        b["confidence"] = round(min(0.95, 0.5 + 0.15 * b["evidence"]), 2)
        b["updated"] = _now()
        if sticky:
            self.beliefs[key] = b
        else:
            # non-sticky: keep latest only, still logged in events
            self.beliefs[key] = b

    def recall(self, *tags, min_confidence=0.5):
        out = [dict(key=k, **v) for k, v in self.beliefs.items()
               if v["confidence"] >= min_confidence
               and any(t in v.get("tags", []) for t in tags)]
        return sorted(out, key=lambda b: -b["confidence"])

    def deadlines(self):
        return [e for e in self.events
                if e["type"] == "takehome_received"]

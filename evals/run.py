"""Eval runner: scores the agent on 12 scenarios + 2 compounding tests."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compounding_chief.agent import ChiefOfStaff
from compounding_chief.memory import BeliefStore
from compounding_chief import voice
from evals.scenarios import SCENARIOS, compounding_test_1, compounding_test_2


def score_scenario(agent, sc):
    item = dict(sc["item"])
    d = agent.decide(item)
    kinds = {a.kind for a in d.actions}
    checks = []
    checks.append(("class", d.classification == sc["expect_class"]))
    checks.append(("actions", sc["expect_action_kinds"] <= kinds))
    top = min((a.priority for a in d.actions),
              key=lambda p: {"p0": 0, "p1": 1, "p2": 2, "noise": 3}[p])
    checks.append(("priority", top == sc["expect_priority"]))
    drafts = [a.draft for a in d.actions if a.draft]
    if sc.get("draft_must_be_empty"):
        checks.append(("no_draft", not drafts))
    for bad in sc.get("draft_must_not_have", []):
        checks.append((f"no:{bad[:20]}",
                       not any(bad in dr for dr in drafts)))
    for good in sc.get("draft_must_have", []):
        checks.append((f"has:{good[:20]}",
                       any(good in dr for dr in drafts)))
    for dr in drafts:
        v = voice.check_violations(dr)
        checks.append(("voice_clean", not v))
    passed = all(ok for _, ok in checks)
    return passed, checks


def main():
    tmp = tempfile.mkdtemp()
    store = BeliefStore(os.path.join(tmp, "profile.json"))
    agent = ChiefOfStaff(store)

    rows = []
    for sc in SCENARIOS:
        passed, checks = score_scenario(agent, sc)
        failed = [name for name, ok in checks if not ok]
        rows.append({"scenario": sc["id"], "passed": passed,
                     "failed_checks": failed, "note": sc["note"]})

    for name, fn in [("c1_morning_preference", compounding_test_1),
                     ("c2_vendor_deprioritize", compounding_test_2)]:
        s2 = BeliefStore(os.path.join(tmp, f"{name}.json"))
        ok, detail = fn(s2)
        rows.append({"scenario": name, "passed": ok,
                     "failed_checks": [] if ok else ["compounding"],
                     "note": str(detail)[:160]})

    total = len(rows)
    passed_n = sum(1 for r in rows if r["passed"])
    print(f"\n{'scenario':28s} {'result':6s}  note")
    print("-" * 90)
    for r in rows:
        mark = "PASS" if r["passed"] else "FAIL"
        extra = "" if r["passed"] else f"  FAILED: {r['failed_checks']}"
        print(f"{r['scenario']:28s} {mark:6s}  {r['note']}{extra}")
    print("-" * 90)
    print(f"{passed_n}/{total} passed\n")

    out = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "evals", "results.json")
    with open(out, "w") as f:
        json.dump({"passed": passed_n, "total": total, "rows": rows}, f, indent=2)
    print(f"results -> {out}")
    return 0 if passed_n == total else 1


if __name__ == "__main__":
    sys.exit(main())

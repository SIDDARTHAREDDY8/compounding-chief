"""Morning-briefing demo: runs the chief of staff over the fixture inbox and
prints the prioritized briefing. The agent proposes; nothing is sent or filed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compounding_chief.memory import BeliefStore
from compounding_chief.connectors import load_fixtures
from compounding_chief.agent import ChiefOfStaff
from compounding_chief import voice

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    # seed a little history so compounding is visible in the demo
    store = BeliefStore(os.path.join(BASE, "demo_profile.json"))
    if not store.events:
        store.observe("invite_accepted", {"start": "09:00"})
        store.observe("invite_accepted", {"start": "10:30"})
        store.observe("vendor_pitch_declined", {})
        store.save()

    agent = ChiefOfStaff(store)
    connectors = load_fixtures(os.path.join(BASE, "fixtures"))
    results = agent.run_morning(connectors)

    print(voice.draft_briefing("Siddartha", results))
    print()
    humans = [r for r in results if r["needs_human"]]
    print(f"{len(humans)} item(s) need your hands; "
          f"{len(results) - len(humans)} handled as propose/log/suppress.")
    print("Beliefs in store:")
    for k, b in store.beliefs.items():
        print(f"  - {b['claim']} (confidence {b['confidence']}, "
              f"evidence x{b['evidence']})")
    store.save()


if __name__ == "__main__":
    main()

# Compounding Chief - a working demo of Sauna's thesis, with evals

Built for Wordware's Applied AI Engineer front door:
*"Build something with Sauna and tell us what worked."*

## What Sauna is (researched 2026-09-18)

Sauna (sauna.ai) is Wordware's AI workspace for professionals - "Cursor for
Knowledge Work." It connects to Gmail, Calendar, Slack, and 3,000+ tools
(custom MCP connectors included), learns the user's taste, detects patterns,
drafts in their voice, researches, and acts proactively - live, side-by-side,
or as scheduled background jobs. Multiplayer: a team shares one Sauna's
context and memory. The product thesis is **compounding context**: the more
context it holds, the smarter and more autonomous it gets, earning autonomy
task by task while the human keeps taste and the final say. Recent launch:
APPS - Sauna builds small apps for itself from repeated chat workflows.

Sources: sauna.ai, Wordware's YC jobs page (Applied AI Engineer listing,
crawled ~11 days ago), wordware-ai/sauna-releases on GitHub.

## What I built

**Compounding Chief**: a proactive chief-of-staff agent for a high-stakes job
hunt - the exact loop Sauna sells - plus the eval harness that proves it works.

- `compounding_chief/memory.py` - belief store: observations append to an
  event log; deterministic extractors bump beliefs with evidence counts and
  confidence (`prefers_morning_interviews`, `deprioritize_staffing_vendors`,
  active take-home deadlines). `recall()` surfaces beliefs by tag for each
  decision. This is the compounding-context claim made concrete and testable.
- `compounding_chief/agent.py` - observe → recall → decide → **propose**.
  Classifies inbox items (interview invite, take-home, vendor pitch, bounce,
  duplicate, newsletter, offer, follow-up due, deadline warning, new posting,
  rejection), recalls relevant beliefs, and emits actions: draft_reply,
  calendar_hold, reminder, log_only, suppress, flag_human.
- `compounding_chief/voice.py` - the user's style as enforceable rules:
  no em-dashes, no throat-clearing openers, no banned claims, ≤28-word
  sentences, problem-first follow-ups with one proof point and one ask.
  `check_violations()` runs on every draft.
- `compounding_chief/connectors.py` - pluggable Connector protocol;
  fixture-backed Gmail/Calendar/Slack today, live APIs later with zero
  agent-code changes.
- `evals/` - 12 seeded scenarios + 2 compounding tests, scored on
  classification, action set, priority, and draft constraints. **14/14 pass**
  (see `evals/results.json`).
- `demo.py` - end-to-end morning briefing over a realistic fixture inbox.

## Architecture decisions (and tradeoffs)

1. **Propose, never execute.** High-stakes domain (job + visa on the line):
   the agent earns autonomy task by task; the human approves. Same model
   Sauna advertises. A "yolo mode" would be one flag, but it would be wrong
   here - stated explicitly rather than defaulted.
2. **Deterministic v1 classifier, not an LLM call.** Every decision is
   explainable and the eval suite is hermetic (no API keys, runs offline in
   0.1s). The tradeoff: brittle on phrasing variants. Production design
   would be LLM classifier with these rules as the fallback/verification
   layer - the harness scores either implementation identically.
3. **Beliefs with evidence counts, not embeddings.** For a small, legible
   preference set, counted evidence + confidence is more debuggable than
   vector recall, and the compounding tests assert exact behavior. Doesn't
   scale to thousands of facts; that's where you'd graduate to hybrid
   retrieval.
4. **Voice as a linter, not a vibe.** Style rules are code (`check_violations`),
   so voice regressions are caught by evals like any other bug.

## What worked

- The compounding loop is real and observable: two accepted morning invites
  → belief forms at 0.8 confidence → the next afternoon invite's draft
  proactively asks about mornings. Two declined vendor pitches →
  subsequent pitches get deprioritized automatically.
- Priority triage is correct across all 12 scenarios, including the hard
  ones: offer → flag human with *nothing* drafted; slot conflict → extra
  flag; bounce/duplicate → suppress (no double-sends, no retries).
- Every draft passes the voice linter; the eval asserts it.

## What didn't / honest limitations

- **No live Sauna access.** Sauna is signup-gated and I don't create accounts
  or use credentials I wasn't given, so this was built *about* Sauna's thesis
  rather than *inside* the product. The memory/connector layer is deliberately
  shaped so it could plug into Sauna's skill/connector ecosystem - that's the
  honest next step with account access.
- Fixtures are fictionalized (real contact names kept out of the artifact).
- The classifier is rules-based; adversarial phrasing would beat it. The
  eval suite is the contract an LLM classifier would have to satisfy.

## Run it

```bash
cd ~/workspace/assessment-builds/wordware-sauna
python3 demo.py          # morning briefing over the fixture inbox
python3 -m evals.run    # 14/14 eval suite, writes evals/results.json
```

No dependencies beyond Python 3. stdlib only.

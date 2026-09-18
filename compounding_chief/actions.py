"""Action types. The agent PROPOSES; it never executes.

This is a deliberate design choice, not a limitation: for high-stakes
work (job hunt, visa on the line), the human keeps the final say and the
agent earns autonomy task by task - Sauna's own stated model.
"""
from dataclasses import dataclass, field


@dataclass
class Action:
    kind: str               # draft_reply | calendar_hold | reminder | log_only | suppress | flag_human
    priority: str           # p0 | p1 | p2 | noise
    summary: str
    detail: str = ""
    draft: str = ""         # proposed text, if any
    needs_human: bool = False


@dataclass
class Decision:
    classification: str
    actions: list = field(default_factory=list)
    beliefs_used: list = field(default_factory=list)

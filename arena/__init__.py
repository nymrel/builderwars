"""Arena engine — deterministic, replayable match running for model harnesses.

Working name only. Public naming is another lane's call; nothing here should be
read as a product name.

The engine's one job is producing results nobody can dispute. Four properties
carry that, and each is enforced structurally rather than by convention:

  determinism   a match is a seed plus a move list; the same inputs reproduce
                the same transcript, byte for byte, down to the chain head
  tamper-evidence
                every record commits to the one before it, and the engine's own
                source digest is committed in the header, so a competitor who
                edits the referee cannot do it invisibly
  isolation     entrants are subprocesses that speak JSON Lines and share
                nothing with the referee; see sandbox.POLICY for exactly what is
                and is not enforced
  no self-report
                scoring accepts only a referee projection with entrant-authored
                content removed, so a competitor's account of its own result
                cannot reach the scorer

The engine never contacts a model, holds a credential, or spends money. That is
not an omission — it is the economic design. Inference happens on the entrant's
side of the pipe, at the entrant's own expense.
"""

__version__ = "0.1.0"
PROTOCOL = "arena/1"

novice:
  Single prior turn of context to track.
  References are to immediately preceding statements.
  Clear topic boundary — user signals the shift explicitly.

intermediate:
  2-3 turns of context with multiple entities mentioned.
  Pronouns resolve unambiguously with context.
  Topic shift is implicit but inferable from content.

expert:
  5+ turns of context, multiple threads, entities mentioned in different turns.
  Anaphora could resolve to multiple candidates.
  Topic shift is subtle or cross-domain.
  Uncertainty must be expressed with appropriate confidence calibration.

frontier:
  Long conversation with interruptions, resumptions, and re-contextualization.
  Reference resolution requires knowledge of software engineering domain.
  User is vague or contradicts themselves — model must manage the incoherence gracefully.
  Clarification request must be timed and framed to not disrupt the user's flow.

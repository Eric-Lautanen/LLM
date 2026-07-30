novice:
  Clear question type (what, how, why, can you).
  Single intent per message.
  No negation or qualification.
  Direct request with explicit phrasing.

intermediate:
  Mixed question types within a single message.
  Indirect requests phrased as statements or questions.
  Simple negation ("not that", "without X").
  Multiple actionable intents in one message.

expert:
  Multi-part request with dependencies between parts.
  Complex negation with exceptions.
  User signals expertise level implicitly through jargon or framing.
  Indirect request requires domain knowledge to recognize.

frontier:
  Implicit intent not stated at all — must be inferred from context, user role, and project stage.
  User contradicts themselves across messages.
  Intent is best served by pushback or scope negotiation, not direct execution.
  Multiple valid interpretations with different tradeoffs — model must identify the ambiguity.

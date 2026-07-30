novice:
  Obvious error message pointing to a clear root cause.
  Single file, single function, well-understood API.
  Fix is straightforward — apply the standard pattern.

intermediate:
  Error message is misleading or points to a symptom, not the cause.
  Multiple files or components involved.
  Requires tracing data flow or control flow to find the issue.

expert:
  Non-deterministic or intermittent failures.
  Environment-specific (works on my machine).
  Requires bisecting logs, binary search over commits, or instrumenting with additional logging.

frontier:
  Heisenbugs that disappear under observation.
  Production-only failures with limited information.
  Latent bug that has been present for months and only surfaces under specific load/input combinations.
  Requires designing a hypothesis-testing strategy from scratch.

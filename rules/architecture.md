# Architecture

The stdlib-only runtime consists of immutable models, strict configuration,
read-only discovery/audit, deterministic rendering, bounded command execution,
provider adapters and a CLI boundary. Provider queries must be read-only.

The skill performs requirement discovery and agreement through the user's own
agent. The runtime does not call an LLM or infer business semantics from prose.
Configuration records project-specific decisions; generated docs and workflows
must not introduce contradictory policy.

Rendering computes all conflicts before applying output. Existing source and
unowned configuration are preserved. A report's fingerprint is evidence binding,
not protection against an adversary with authority over CI and approvals.

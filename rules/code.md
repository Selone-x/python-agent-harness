# Code

Annotate functions and fixtures. Keep state records as immutable, slotted,
keyword-only dataclasses. Use narrow errors at the CLI boundary and explicit
structured findings for check outcomes. Never convert a failed check to success.

Keep pure configuration and graph calculations separate from IO. Execute argv
without a shell. Constrain generated paths to the project and reject escapes.
Commands must have time and output budgets; run them sequentially by default.

Ruff enforces formatting, common defects, types at boundaries and complexity.
Local suppressions need a rule code and explanation. Apply quality rules to
tests and tools too. Do not introduce architecture-specific Result/DTO rules
into consumer projects without agreement.

---
name: mutation-testing
description: Configure bounded Python mutmut campaigns, analyze surviving mutations and investigate the test gaps they expose. Use for mutation testing setup or results, not to launch a full campaign during ordinary tests or coverage work.
---

Use mutmut for Python. Select setup, saved-results analysis or investigation from
the user's request. Reading saved results requires neither installing mutmut nor
rerunning the campaign. This adaptation has no mewt/muton command dependency.

Inspect project policy, recent mutation results, tool version, target source paths,
tests and acceptance rules first. Read [the campaign guide](references/campaign.md)
for setup or a bounded rerun. The constructor locks mutmut 3.7.0 in its optional
`mutation` group because mutmut 3.8 conflicts with the current Fixit Click constraint.
Preserve another project's compatible version and use its actual `--help` output.

Before executing, establish a narrow scope and independent expected outcomes.
Baseline tests must pass on the original code. Start with one function or small
module, one worker, disk-backed temporary paths, a total timeout and bounded logs.
Keep production code unchanged while investigating; use a disposable copy if cache
or target configuration needs adjustment. Do not implicitly run the full project.

Mutmut's function selector can narrow execution while generation still visits all
configured `source_paths`. Narrow those paths in the disposable campaign when
needed. Do not copy environments/caches or entire repositories via `also_copy`.
Do not delete or replace an existing campaign to obtain a clean result.

Read the actual mutant diff, original source and relevant tests before interpreting
an outcome. Mutmut uses its own statuses; preserve their names and version in the
report rather than translating a generic score into success:

- Killed: tests rejected the mutation; inspect whether they failed for the intended reason.
- Survived: distinguish a missing assertion/input, unreachable scope or semantic equivalence.
- Timeout, suspicious, missing tests, untested or execution errors: unresolved outcomes.
- Skipped or excluded: describe why and what was not measured; do not count as killed.

A zero exit from `mutmut run` does not establish that every mutant was killed.
Inspect results and use the project's explicit acceptance adapter before claiming
a CI gate passed. Do not invent a universal score or bulk-exclude survivors.

For new scaffolds, the campaign guide provides a complete optional deep preset
with a one-worker 60-second engine command followed by `@harness mutation-gate`.
The latter reads complete results with a 30-second/output budget and strictly
requires a nonempty inventory of only killed mutants. It never starts a campaign.
This is an explicit strict preset, not a universal mutation score; equivalent
exceptions need a separately reviewed adapter/policy rather than silent acceptance.

Read [the result-analysis guide](references/analysis.md) for survivors, equivalence
or suspected bugs. For a testing gap, derive the new assertion/input independently
from the contract, reproduce it against the mutant and verify the original still
passes. A surviving mutant alone is not a confirmed production bug.

Report the source revision, tool/configuration, actual scope, baseline, commands,
budgets, observed outcomes, equivalent-mutant evidence and unfinished work. Resume
only under a current fingerprint of source, tests, dependencies and configuration;
do not present stale cached results as fresh verification. Campaigns belong in an
explicit bounded deep/manual/nightly workflow, outside the ordinary check path.

This is a Python/mutmut adaptation of Trail of Bits material. See [NOTICE.md](NOTICE.md)
for provenance and changes, and [LICENSE](LICENSE) for the directory's license.

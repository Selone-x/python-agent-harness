# Analyze results without overstating them

Bind outcomes to the original revision, configuration, selected tests, dependency
lock and actual mutant diff. If only a summary or stale cache is available, name
the missing evidence. Preserve unknown statuses instead of silently dropping them.

For each survivor, inspect what changed and what the original tests observe.
Prioritize consequences in the project: a tiny arithmetic change in accounting can
matter more than removing a log line. Engine mutation categories are not business risk.

Classify the result as a test gap, demonstrated equivalence or unresolved outcome.
Equivalence needs an argument over the relevant domain, including errors and side
effects. For example, `balance > 0` and `balance != 0` agree for nonnegative integers;
they disagree if negatives are permitted. A claimed domain restriction must itself
be enforced. Do not generalize one proof to unrelated mutants on the same line.

For a gap, derive a new input/assertion from an independent contract or simple model.
Example: values below and above a limit cover both outcomes of `price >= limit`, but
do not distinguish the mutation `price > limit`. The equality case does. Confirm
that the regression passes on the original and rejects the actual selected mutant.

For a suspected original-code defect, reproduce the issue on the unmutated code
before describing it as confirmed. Mutation analysis alone establishes a test
sensitivity gap, not that the original implementation is wrong.

Keep timeouts, suspicious results, no-tests outcomes, skipped and untested mutants
separate from killed mutants. Record any equivalence exception individually with
mutant identity, diff fingerprint and proof, using the project's existing review
policy. Do not lower acceptance thresholds or alter assertions merely for a score.

Return actionable assertions/inputs, evidence for equivalence, inconclusive items,
commands actually executed and the budget/scope of any rerun. If analysis alone was
requested, recommend changes without silently editing tests or rerunning campaigns.

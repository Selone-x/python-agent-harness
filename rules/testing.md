# Testing

Test expected behavior from literal contracts, simple independent examples and
observable subprocess results. Cover valid and invalid input, missing evidence,
source inventory, boundary ratios, cycles/relative imports, regeneration,
preservation of user content, timeouts, output floods and stale CI artifacts.

Generated lint rules need positive and negative examples executed through their
real engine. Test fixtures are not proof of assertion quality. A skill metadata
validator is not a behavioral evaluation.

Use workspace temporary paths, fixed Hypothesis profiles, one test process and
bounded subprocesses. No full mutation/performance run is implicit in `just check`.
Live GitHub/GitLab protection tests require disposable repositories and explicit
authorization; do not run destructive demonstrations against real main branches.

# Evaluation of ub-mode practices and tools

This records a small, manual evaluation for the Python Agent Harness. The
independently written `disciplined-code-change` skill applies compatible workflow
ideas from [ub-mode](https://github.com/unclebob/ub-mode); it does not copy that
skill or claim that agent behavior has been evaluated.

| Area | Current treatment |
| --- | --- |
| Small changes, modeling and first-principles design | New skill guides bounded, project-specific decisions. |
| Test-first and behavior preservation | New skill asks for an independent failing example when warranted and verification after refactoring. |
| Root causes and repeated failures | New skill asks for reproduction, causal diagnosis and examination of a shared failed assumption. |
| Boundaries, retry safety and shared state | New skill makes these conditional on the actual change and project contract. |
| Complexity and coverage | Existing Ruff, Complexipy and coverage checks remain; Crapper was explored separately. |
| Duplication | Dryer was explored; candidates are not an enforced project check. |
| Mutation testing | Existing optional bounded mutmut workflow remains; Mutator was explored separately. |
| Logging and context | New skill asks the agent to track actions and reasons and report relevant evidence. |
| Worktrees and delivery | Existing project rules and authorization remain in force. |
| Visual metrics | UML viewer's headless generator and CRAP overlay were evaluated; its GUI and agent workflow were not run. |

## Local tool experiment

On 2026-10-28, Crapper commit `6fd92c4c9bcc56efb64a2f8743d5a2993bcfd42d`,
Dryer commit `66ff6d21a42c04afcad89c78a80066176d1294b0` and Mutator commit
`a5a0cb803b66e0cdb8bf471b3b08af701d424a41` were cloned into an ignored workspace
and installed in a separate uv-locked environment. Its resolved dependencies
included `tree-sitter==0.26.0` and
`tree-sitter-language-pack==1.22.1`. These tool versions were not added to this
project's dependencies, scaffolds or CI.

The Python source and LCOV in this experiment were hand-written fixtures, not
coverage evidence produced by a real test suite. With the Python grammar available:

- `crapper --use-existing-coverage --threshold 10 src/example.py` reported a
  function at complexity 3 and 50% branch coverage with CRAP 4.1 and exited 0.
- A function with complexity 10 and 100% fixture coverage reported CRAP 10.0.
  `--threshold 10` exited 0, while `--threshold 9.99` exited 2. This matters if
  the desired condition is strictly less than 10.
- `dryer --threshold 0.8 src/example.py` returned 0 and reported two structurally
  similar functions at 1.00. Their literal values differ; the result is a review
  candidate, not evidence that the two behaviors should be merged.

Both commands used the tools' `--root` option to target the disposable fixture and
were launched through the separate locked uv environment. Python grammar download
initially failed with a timeout; by the time of the subsequent Dryer run it was
available. This confirms that locking Python packages alone does not guarantee an
offline first run. The fixture checks do not establish correctness or performance
on an arbitrary project.

The tools were then run against a disposable copy of this repository's `src/`.
An LCOV file was exported from the coverage database produced by a successful
`just check`; tests and tool scripts were not included in this inspection.
Crapper reported nine functions above 10 and two at exactly 10, with all displayed
functions at 100% coverage. The worst were `runner.gate` at 20 and
`overview.report_shape` at 18. Its `--threshold 10` run exited 2. Crapper's
complexity calculation is not identical to the project's Ruff C901 metric, so
these results do not imply Ruff failed. Dryer reported no candidates at threshold
0.8 and exited 0. These are observations to review, not proof of quality or a
request to refactor the functions solely to change a score.

Mutator's `--scan` reported nine mutation sites in the small fixture. With one
worker, a 30-second outer budget and line selection, a test expecting the result
10 rejected the single `-` to `+` mutation; the run exited 0 and called it killed.
The report displayed a 100% score despite selecting one of nine sites. Repeating
that mutation with a 15-second outer budget and a test that writes `waiting` before
sleeping for four seconds and `finished` afterward produced `KILLED` and exit 0
while the marker remained `waiting`. With the configured timeout factor and
two-second minimum, this
demonstrates the timeout classification on this fixture; it does not establish a
complete campaign or validate the tool on the project.

## UML viewer headless inspection

The UML viewer was inspected at commit `f65dafe93b3cb1b4e6bb02dbe41503ed05bd9ebf`.
Its headless IR generator was run through Java 27 and Clojure 1.12.0 against the
same disposable source copy. The resulting graph contained 16 Python modules and
46 edges. A separate headless overlay loaded the Crapper snapshot and attached
complexity 20, CRAP 20.0 and coverage 1.0 to `runner.gate`. No mutation snapshot
was present in that source-copy experiment.

One deliberately small fixture exposed a boundary-classification limitation.
Module `a` imports `Result` from `b`, and the policy places `a` inside `b` so
that an `a` to `b` dependency is forbidden. With `def compute() -> Result`,
the generated edge was `:implements` and had no violation flag. Removing only
the return annotation produced a `:dependency` edge marked `:violating true`.
The import exists in both cases. The viewer's documented policy excludes
`:implements` edges from dependency violations, so its graph is useful for
exploration but that result cannot replace the harness's architecture audit.

The GUI, automatic Grok companion, viewer controls, full Python syntax coverage
and the correctness of all 46 edges were not tested. These graph and overlay
observations do not establish that the viewer accurately detects every dependency.

## Decisions and remaining work

- Keep review of assertion quality, existing coverage checks and bounded execution.
- Keep mutation timeouts unresolved. The upstream Mutator documentation and the
  isolated experiment above both classify a timeout as killed.
- Keep branch and review rules. The upstream skill's instruction to push to the
  main line does not override a target repository's policy.
- The [UML viewer](https://github.com/unclebob/uml-viewer) GUI was not run. Its
  documented startup requires Clojure and Java and starts a separate Grok agent;
  graphical and agent execution need their own authorization and evaluation.
- Do not install these tools in consumer projects or enable them as gates on the
  basis of this experiment. Before proposing integration, independently verify
  grammar provisioning, current and complete coverage, failure handling, output
  and runtime limits, and positive/negative examples through the real engines.

The `ub-mode` repository did not advertise a license at the time of review. Its
skill text was not copied. The Crapper and Dryer repositories advertise 0BSD;
their source and installed dependencies remain in the ignored experiment workspace.

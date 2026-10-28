# CRAP and duplication evaluation

Use an explicitly agreed tool and existing project environment. First establish
the source scope, test command, output locations, time and output budgets, and how
an existing coverage report is made current. Run in a disposable copy when a tool
may modify coverage, install dependencies or write artifacts. Do not replace a
project's formatter, type checker or test runner merely to try a metric.

CRAP combines a function's cyclomatic complexity and measured coverage. A high
value can prioritize review; a low value does not prove that assertions are useful.
The optional [Crapper](https://github.com/unclebob/crapper) tool supports Python
and existing LCOV reports. Check its actual version and command help: its reported
threshold behavior is strictly greater than the supplied value, so `--threshold 10`
does not by itself enforce a strict `CRAP < 10`. Missing, failed, stale or incomplete
coverage must not be promoted to passing evidence. Its default coverage workflow
can install tools and replace reports; opt into it only in an agreed environment.

[Dryer](https://github.com/unclebob/dryer) reports structural similarity candidates.
Review whether candidates share a responsibility before refactoring. The documented
exit code 0 means the report was written, including when candidates exist; a gate
requires a separately agreed, tested acceptance rule. The default similarity
threshold is not necessarily the threshold a particular project wants.

Both tools use `tree-sitter-language-pack`, which may download grammars at first
use. Pin and verify the tool, its dependencies and grammar provisioning before
claiming reproducible offline use; report installation or network failures.

[Mutator](https://github.com/unclebob/mutator) treats a timeout as killed. Do not
use that outcome as passing evidence under a policy that treats timeouts as
unresolved. Use the project's existing bounded mutation workflow until equivalent
semantics can be established and independently tested. A green engine exit alone
is not proof that all selected mutations were assessed.

# Configure and run a bounded mutmut campaign

Use the target's locked toolchain. In this constructor, the optional group is
`mutation`; new scaffolds provide the same compatible mutmut 3.7.0 pin. Check:

```sh
uv run --locked --group mutation mutmut --help
uv run --locked --group mutation mutmut run --help
uv run --locked --group mutation mutmut results --help
uv run --locked --group mutation mutmut show --help
```

Do not copy flags from another engine or assume version compatibility. Configuration
names below were checked against mutmut 3.7.0. In a disposable small Python project,
an example target configuration is:

```toml
[tool.mutmut]
source_paths = ["src/example/"]
pytest_add_cli_args = ["--no-cov", "--basetemp=.harness/reports/mutation-tmp"]
pytest_add_cli_args_test_selection = ["tests/"]
also_copy = ["uv.lock"]
cache_invalidation_files = ["tests/conftest.py", "uv.lock"]
on_dependency_change = "rerun"
```

Use real source/test paths and only required extra files. Pass `--no-cov` only when
pytest-cov is installed; preserve other project's pytest arguments and warning rules.
Baseline the same selected tests before measuring mutants. Estimate the work from
the number of candidate changes and baseline runtime; the function selector alone
does not guarantee a small generated tree.

Read exact IDs/patterns from the campaign rather than inventing mutant names:

```sh
uv run --locked --group mutation mutmut results --all true
uv run --locked --group mutation mutmut browse
```

Run selected IDs with `mutmut run --max-children 1`, using the installed help for
argument order. Retesting one ID uses that same run command, not mewt's `test`.
Use `mutmut show` to inspect a diff. `mutmut apply` writes source; avoid it in the
working repository and use an isolated copy when deliberately reproducing a mutant.

In 3.7.0, `results --all true` includes killed mutants; the default view omits them.
An empty default result list is not proof that the intended scope was executed.
Bind acceptance to the run's generated/tested counts and complete status inventory.

Mutmut 3.7.0 uses POSIX fork. Record thread/fork warnings, crashes and hangs rather
than suppressing them or classifying them as killed mutants. Isolation options
vary by version: do not copy a newer version's forkserver flag into this pin without
checking support. Changing the engine/version or process setup is a separate
compatibility decision; retain bounded execution while investigating.

For a project that already carries `.harness/runner.pyz`, configure a check in the
`deep` group with argv beginning `uv run --locked --group mutation mutmut run
--max-children 1`, followed by the chosen IDs, and a finite timeout. Add the campaign
configuration, acceptance adapter and fixtures to `inputs`. Run it only through the
bounded deep runner. Keep its total budget, output cap and one-worker setting.
An acceptance check must follow the campaign: raw mutmut exit status is insufficient
to reject survivors, missing tests or inconclusive outcomes.

New scaffolds ship the ready `.harness/mutation-check.example.toml`. After configuring
the narrow target and baseline, merge its two checks into the existing spec:

```toml
[[checks]]
id = "mutation-run"
group = "deep"
argv = ["uv", "run", "--locked", "--group", "mutation", "mutmut", "run", "--max-children", "1"]
timeout = 60

[[checks]]
id = "mutation-acceptance"
group = "deep"
argv = ["@harness", "mutation-gate"]
timeout = 35
```

`mutation-gate` runs `mutmut results --all true` with a 30-second/output budget.
The explicit strict preset rejects empty/malformed/duplicate inventories and every
status except killed, including unknown future statuses. It does not generate or
apply mutants. Use the complete deep run to establish current engine execution;
inspecting independently copied cached results alone does not establish freshness.
The spec fingerprint must include all configuration and non-Python fixtures.

For another environment, pass its literal results argv after `mutation-gate --`.
Keep the existing tool/version and a reviewed acceptance policy when adopting a
project; do not silently replace its equivalence policy with this stricter preset.

Without that runner, use the target's existing bounded subprocess facility with
process-group termination and log limits. If no bounded executor is available,
prepare the command and report the remaining execution requirement instead of
launching an unbounded full campaign. Keep `mutants/` and temporary files on disk.

See [mutmut documentation](https://mutmut.readthedocs.io/en/latest/) for current
options, then verify them against the project's installed version.

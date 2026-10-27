"""Explicit new-project scaffolding and non-destructive adoption drafts."""

import re
from pathlib import Path

from .config import SPEC_PATH, literal
from .paths import HarnessError, inside

TOOLS = (
    '"ruff==0.16.10", "ty==0.0.90", "pytest==9.1.1", "pytest-cov==7.1.0", '
    '"hypothesis==6.170.5", "pre-commit==4.7.0", "fixit==2.2.1", '
    '"vulture==2.16", "complexipy==8.2.0", "ast-grep-cli==0.45.3"'
)

HYPOTHESIS_PROFILES = (("dev", 50, 25), ("ci", 200, 50), ("nightly", 1000, 200))

MUTATION_CHECK_EXAMPLE = """
# Configure narrow source_paths, pytest_add_cli_args_test_selection and cache invalidation
# in tool.mutmut first; see the mutation-testing skill's campaign guide.
# Add that config and all non-Python fixtures to the spec's inputs array.
# Run the matching baseline tests before activating this optional strict preset.
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
"""

AST_CONFIG = "ruleDirs: [lint-rules]\ntestConfigs:\n  - testDir: lint-fixtures\n"
AST_RULE = """id: no-shell-command
language: Python
severity: error
message: Pass argv without shell=True; use an explicit bounded process boundary.
rule:
  any:
    - pattern: subprocess.run($$$BEFORE, shell=True, $$$AFTER)
    - pattern: subprocess.run($$$BEFORE, shell=True)
    - pattern: subprocess.Popen($$$BEFORE, shell=True, $$$AFTER)
    - pattern: subprocess.Popen($$$BEFORE, shell=True)
"""
AST_FIXTURES = """id: no-shell-command
valid:
  - subprocess.run(["echo", "ok"], timeout=5)
  - subprocess.run(["echo", "ok"], shell=False, timeout=5)
  - service.run(command, shell=True)
invalid:
  - subprocess.run("echo ok", shell=True, timeout=5)
  - subprocess.Popen("echo ok", shell=True)
"""

AST_SNAPSHOTS = """id: no-shell-command
snapshots:
  subprocess.Popen("echo ok", shell=True):
    labels:
    - source: subprocess.Popen("echo ok", shell=True)
      style: primary
      start: 0
      end: 39
  subprocess.run("echo ok", shell=True, timeout=5):
    labels:
    - source: subprocess.run("echo ok", shell=True, timeout=5)
      style: primary
      start: 0
      end: 48
"""

API_CHECK_EXAMPLE = """
# Opt in by copying this check into .harness/project.toml after agreeing the target.
# Supply your real schema and start an isolated test service before running it.
# Add the schema and any Schemathesis config/hooks to the spec's inputs array.
[[checks]]
id = "api-contract"
group = "deep"
argv = [
    "uv", "run", "--locked", "--group", "harness", "--group", "api", "schemathesis",
    "run", "openapi.yaml", "--url", "http://127.0.0.1:8000", "--workers", "1",
    "--phases", "examples,fuzzing", "--max-examples", "25", "--max-failures", "1",
    "--request-timeout", "5", "--generation-deterministic", "--generation-database", "none",
]
timeout = 120
"""


def draft(name: str, package: str, kind: str, providers: tuple[str, ...], scaffold: bool) -> str:
    """An adoption draft deliberately blocks until real project commands are supplied."""
    setup = '[["uv", "sync", "--locked", "--group", "harness"]]' if scaffold else "[]"
    prefix = ["uv", "run", "--locked", "--group", "harness"]
    checks: list[tuple[str, str, list[str]]] = [
        ("policy", "static", ["@harness", "audit"]),
        ("format", "static", [*prefix, "ruff", "format", "--check", "."]),
        ("lint", "static", [*prefix, "ruff", "check", "."]),
        ("dead-code", "static", [*prefix, "vulture"]),
        ("cognitive-complexity", "static", [*prefix, "complexipy"]),
        ("rule-tests", "static", [*prefix, "ast-grep", "test", "--include-off"]),
        ("project-rules", "static", [*prefix, "ast-grep", "scan", "--error", "src", "tests"]),
        ("types", "static", [*prefix, "ty", "check"]),
        (
            "behavior",
            "tests",
            [
                *prefix,
                "pytest",
                "--basetemp=.harness/reports/test-tmp",
                "-o",
                "tmp_path_retention_policy=failed",
                "-o",
                "tmp_path_retention_count=1",
            ],
        ),
    ]
    if not scaffold:
        checks = [
            (
                "configure-static",
                "static",
                [
                    "@python",
                    "-c",
                    "raise SystemExit('Agree existing static checks in .harness/project.toml')",
                ],
            ),
            (
                "configure-tests",
                "tests",
                [
                    "@python",
                    "-c",
                    "raise SystemExit('Agree existing tests/coverage in .harness/project.toml')",
                ],
            ),
        ]
    if kind == "library":
        checks.extend(
            (
                ("build", "package", ["uv", "build", "--no-sources"]),
                ("artifact", "package", ["@harness", "package", "--module", package]),
            )
        )
    header = f"""schema_version = 1
name = {literal(name)}
kind = {literal(kind)}
python = "3.13"
description = "Agree project purpose, architecture and invariants before changing behavior."
sources = [{literal("src/" + package)}]
tests = ["tests"]
inputs = ["lint-rules", "lint-fixtures", "sgconfig.yml", "justfile"]
providers = {literal(providers)}
setup = {setup}

[quality]
lines = "97"
branches = "100"
coverage = ".harness/reports/coverage.json"
output_limit = 1048576
deep_budget = 900
"""
    for check_id, group, argv in checks:
        header += (
            f"\n[[checks]]\nid = {literal(check_id)}\ngroup = {literal(group)}\n"
            f"argv = {literal(argv)}\ntimeout = 120\n"
        )
    return (
        header
        + """
[[requirements]]
id = "independent-oracle"
description = "Review assertions, errors and boundaries against independent expected results."
enforcement = "review"
"""
    )


def project_files(name: str, package: str, kind: str) -> dict[str, bytes]:
    """A minimal smoke-tested package does not invent business logic or layers."""
    profiles = ", ".join(
        f"({literal(profile)}, {examples}, {steps})"
        for profile, examples, steps in HYPOTHESIS_PROFILES
    )
    project = f"""[project]
name = {literal(name)}
version = "0.1.0"
requires-python = ">=3.13"
description = "Python project with an executable, project-specific harness"

[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = [{literal("src/" + package)}]

[tool.hatch.build.targets.sdist]
exclude = ["/.harness/**", "/.venv/**", "/dist/**"]

[dependency-groups]
harness = [{TOOLS}]
api = ["schemathesis==4.32.5"]
mutation = ["mutmut==3.7.0"]

[tool.vulture]
paths = ["src", "tests"]
min_confidence = 80

[tool.complexipy]
paths = ["src", "tests"]
max-complexity-allowed = 15
no-ignore = true
failed = true
color = "no"
cache-dir = ".harness/reports/complexipy-cache"

[tool.ruff]
line-length = 100
extend-exclude = [".harness"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "C90", "ANN", "S", "BLE", "PGH", "RUF"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "--strict-config", "--strict-markers", "--cov={package}", "--cov-branch",
    "--cov-report=json:.harness/reports/coverage.json",
    "--cov-report=xml:.harness/reports/coverage.xml",
    "--basetemp=.harness/reports/test-tmp",
    "-o", "tmp_path_retention_policy=failed", "-o", "tmp_path_retention_count=1",
]
filterwarnings = ["error"]

[tool.coverage.run]
source = [{literal("src/" + package)}]
relative_files = true
branch = true

[tool.ty.src]
include = ["src", "tests"]
"""
    return {
        "pyproject.toml": project.encode(),
        ".harness/api-check.example.toml": API_CHECK_EXAMPLE.encode(),
        ".harness/mutation-check.example.toml": MUTATION_CHECK_EXAMPLE.encode(),
        "sgconfig.yml": AST_CONFIG.encode(),
        "lint-rules/no-shell-command.yml": AST_RULE.encode(),
        "lint-fixtures/no-shell-command.yml": AST_FIXTURES.encode(),
        "lint-fixtures/__snapshots__/no-shell-command-snapshot.yml": AST_SNAPSHOTS.encode(),
        "tests/conftest.py": f'''"""Bounded generated-test profiles for local and CI runs."""

import os
from pathlib import Path

from hypothesis import settings

(Path(__file__).resolve().parents[1] / ".harness/reports").mkdir(parents=True, exist_ok=True)
profiles = ({profiles})
for profile_name, examples, steps in profiles:
    settings.register_profile(
        profile_name,
        max_examples=examples,
        stateful_step_count=steps,
        print_blob=True,
        deadline=200,
        suppress_health_check=(),
        derandomize=profile_name != "dev",
    )
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
'''.encode(),
        f"src/{package}/__init__.py": b'"""Public package version."""\n\n__version__ = "0.1.0"\n',
        f"src/{package}/py.typed": b"",
        "tests/test_package.py": (
            f'"""Smoke-test the public package contract."""\n\n'
            f"from {package} import __version__\n\n\n"
            "def test_public_version() -> None:\n"
            '    """The initial distribution exposes its declared version."""\n'
            '    assert __version__ == "0.1.0"\n'
        ).encode(),
        "README.md": (
            f"# {name}\n\n{kind.capitalize()} project. Agree architecture before implementation.\n"
            "\nRun `just setup` before checks and commit the resulting uv.lock.\n"
            "The version test is a packaging smoke test; add behavior tests for features.\n"
            "\nVulture runs in the required static group; scan source and tests together.\n"
            "Complexipy also checks source and tests at cognitive complexity 15;\n"
            "`just complexity` runs it alone. Ruff also enforces cyclomatic complexity 10.\n"
            "ast-grep tests its YAML fixtures and scans src/tests in the static group.\n"
            "Rule configuration, fixtures and snapshots participate in report identity.\n"
            "For an API, agree its schema and isolated target, then copy the check from\n"
            "`.harness/api-check.example.toml` into `.harness/project.toml`. Add schema,\n"
            "config and hook paths to `inputs` so reports become stale when they change.\n"
            "The optional `api` group contains locked Schemathesis; `just deep` runs\n"
            "the configured checks sequentially with time/output limits. Start the test\n"
            "service separately. To require API checks in ordinary CI, use group `tests`\n"
            "and arrange service startup in that CI job; every configured check must pass.\n"
            "The optional `mutation` group pins mutmut 3.7.0, compatible with Fixit.\n"
            "Configure narrow targets, selected baseline tests and cache invalidation;\n"
            "then copy `.harness/mutation-check.example.toml` checks into the spec.\n"
            "Its engine uses one worker with a 60-second limit. The following strict\n"
            "mutation-gate requires a nonempty inventory containing only killed mutants.\n"
        ).encode(),
        ".gitignore": (
            b".venv/\n.harness/reports/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n"
            b".hypothesis/\n.schemathesis/\nmutants/\n.coverage*\ndist/\nbuild/\n"
        ),
        "justfile": b"""set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

setup:
    uv sync --group harness
    uv run --group harness pre-commit install --config .harness/pre-commit-config.yaml

check:
    uv run --locked --group harness python -I .harness/runner.pyz validate
    uv run --locked --group harness python -I .harness/runner.pyz check
    uv run --locked --group harness python -I .harness/runner.pyz gate

dead-code:
    uv run --locked --group harness vulture

complexity:
    uv run --locked --group harness complexipy

deep:
    uv run --locked --group harness python -I .harness/runner.pyz check --group deep

fmt:
    uv run --locked --group harness ruff check --fix .
    uv run --locked --group harness ruff format .
""",
    }


def initialize(
    root: Path, name: str, package: str, kind: str, providers: tuple[str, ...], scaffold: bool
) -> tuple[str, ...]:
    """Do not rewrite application files while adopting an existing repository."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or not re.fullmatch(r"[a-z][a-z0-9_]*", package):
        raise HarnessError("Use a lowercase distribution name and an importable package name")
    if inside(root, SPEC_PATH).exists():
        raise HarnessError("A harness specification already exists")
    if scaffold and any(root.iterdir()):
        raise HarnessError(
            "Scaffolding requires an empty directory; use init without --scaffold to adopt"
        )
    generated = project_files(name, package, kind) if scaffold else {}
    generated[SPEC_PATH] = draft(name, package, kind, providers, scaffold).encode()
    for relative, content in generated.items():
        target = inside(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(content)
    return tuple(generated)

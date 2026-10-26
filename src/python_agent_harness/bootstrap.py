"""Explicit new-project scaffolding and non-destructive adoption drafts."""

import re
from pathlib import Path

from .config import SPEC_PATH, literal
from .paths import HarnessError, inside

TOOLS = (
    '"ruff==0.16.10", "ty==0.0.90", "pytest==9.1.1", "pytest-cov==7.1.0", '
    '"hypothesis==6.170.5", "pre-commit==4.7.0", "fixit==2.2.1", "import-linter==2.15"'
)


def draft(name: str, package: str, kind: str, providers: tuple[str, ...], scaffold: bool) -> str:
    """An adoption draft deliberately blocks until real project commands are supplied."""
    setup = '[["uv", "sync", "--locked", "--group", "harness"]]' if scaffold else "[]"
    prefix = ["uv", "run", "--locked", "--group", "harness"]
    checks: list[tuple[str, str, list[str]]] = [
        ("policy", "static", ["@harness", "audit"]),
        ("format", "static", [*prefix, "ruff", "format", "--check", "."]),
        ("lint", "static", [*prefix, "ruff", "check", "."]),
        ("types", "static", [*prefix, "ty", "check"]),
        ("behavior", "tests", [*prefix, "pytest"]),
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

[tool.ruff]
line-length = 100
extend-exclude = [".harness"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ANN", "S", "PGH"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "--strict-config", "--strict-markers", "--cov={package}", "--cov-branch",
    "--cov-report=json:.harness/reports/coverage.json",
    "--cov-report=xml:.harness/reports/coverage.xml",
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
        "tests/conftest.py": b'''"""Bounded generated-test profiles for local and CI runs."""

import os

from hypothesis import settings

settings.register_profile("dev", max_examples=50, stateful_step_count=25, print_blob=True)
settings.register_profile("ci", max_examples=200, stateful_step_count=50, print_blob=True)
settings.register_profile("nightly", max_examples=1000, stateful_step_count=200, print_blob=True)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
''',
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
        ).encode(),
        ".gitignore": (
            b".venv/\n.harness/reports/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n"
            b".hypothesis/\n.coverage*\ndist/\nbuild/\n"
        ),
        "justfile": b"""set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

setup:
    uv sync --group harness
    uv run --group harness pre-commit install --config .harness/pre-commit-config.yaml

check:
    python3 -I .harness/runner.pyz validate
    python3 -I .harness/runner.pyz check

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

"""Observable acceptance of the shared tool profiles and scaffold defaults."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from python_agent_harness.bootstrap import initialize
from python_agent_harness.config import load
from python_agent_harness.discovery import inspect_project

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("arguments", [("ruff", "format", "--check", "."), ("ty", "check")])
def test_fresh_scaffold_passes_formatting_and_types(
    tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)

    result = subprocess.run(  # noqa: S603 - installed tools on generated local files.
        [sys.executable, "-m", *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffold_routes_pytest_temporary_files_to_the_project(tmp_path: Path) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    command = next(item for item in load(tmp_path).checks if item.id == "behavior")
    fixture = tmp_path / "tests/test_workspace.py"
    fixture.write_text(
        "from pathlib import Path\n\n"
        "def test_temporary_location(tmp_path):\n"
        "    assert tmp_path.is_relative_to(Path.cwd() / '.harness/reports/test-tmp')\n"
    )

    result = subprocess.run(  # noqa: S603 - literal engine, fixture and bounded subprocess.
        [sys.executable, "-m", "pytest", *command.argv[6:], "--no-cov", str(fixture)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("decisions", "expected"), [(9, 0), (10, 1)])
def test_scaffold_ruff_enforces_cyclomatic_complexity(
    tmp_path: Path, decisions: int, expected: int
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    source = "def decide(value: int) -> int:\n    result = 0\n"
    source += "".join(
        f"    if value == {number}:\n        result += 1\n" for number in range(decisions)
    )
    source += "    return result\n"
    fixture = tmp_path / "src/example/decision.py"
    fixture.write_text(source)

    result = subprocess.run(  # noqa: S603 - installed engine on a generated local fixture.
        [sys.executable, "-m", "ruff", "check", "--output-format=json", str(fixture)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == expected, result.stdout + result.stderr
    assert {item["code"] for item in json.loads(result.stdout)} == ({"C901"} if expected else set())


@pytest.mark.parametrize(
    ("profile", "examples", "steps"), [("dev", 50, 25), ("ci", 200, 50), ("nightly", 1000, 200)]
)
def test_constructor_and_scaffold_use_the_same_bounded_hypothesis_profiles(
    tmp_path: Path, profile: str, examples: int, steps: int
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    environment = {**os.environ, "HYPOTHESIS_PROFILE": profile, "CI": "true"}
    program = (
        "import json, runpy, sys; from hypothesis import settings; runpy.run_path(sys.argv[1]); "
        "print(json.dumps([settings.default.max_examples, settings.default.stateful_step_count, "
        "len(settings.default.suppress_health_check), settings.default.deadline.total_seconds()]))"
    )
    for conftest in (REPOSITORY / "tests/conftest.py", tmp_path / "tests/conftest.py"):
        result = subprocess.run(  # noqa: S603 - fixed profile probe in a bounded child interpreter.
            [sys.executable, "-c", program, str(conftest)],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == [examples, steps, 0, 0.2]


def test_inspection_reports_declared_tools_without_claiming_they_are_enforced(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndependencies = ["hypothesis>=6"]\n'
        '[project.optional-dependencies]\napi = ["schemathesis>=4"]\n'
        '[dependency-groups]\ndev = ["vulture==2.16", "ast-grep-cli==0.45.3"]\n'
        "[tool.complexipy]\nmax-complexity-allowed = 15\n"
    )
    (tmp_path / "sgconfig.yml").write_text("ruleDirs: [lint-rules]\n")

    facts = inspect_project(tmp_path)

    assert set(facts["tools"]) == {
        "hypothesis",
        "schemathesis",
        "vulture",
        "ast-grep",
        "complexipy",
    }
    assert facts["tool_evidence"]["complexipy"]["configuration"] == ["tool.complexipy"]
    assert facts["tool_evidence"]["ast-grep"]["files"] == ["sgconfig.yml"]
    assert facts["tool_evidence"]["schemathesis"]["dependencies"] == ["optional:api"]


def test_scaffold_mutation_profile_contains_bounded_execution_and_strict_acceptance(
    tmp_path: Path,
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    example = tomllib.loads((tmp_path / ".harness/mutation-check.example.toml").read_text())

    assert {check["group"] for check in example["checks"]} == {"deep"}
    assert [check["id"] for check in example["checks"]] == ["mutation-run", "mutation-acceptance"]
    assert example["checks"][0]["argv"][-2:] == ["--max-children", "1"]
    assert example["checks"][0]["timeout"] == 60
    assert example["checks"][1]["argv"] == ["@harness", "mutation-gate"]


def test_scaffold_ast_grep_checks_real_fixtures_and_rejects_a_violation(tmp_path: Path) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    tool = str(Path(sys.executable).with_name("ast-grep"))
    fixture = tmp_path / "probe.py"
    fixture.write_text('subprocess.run("echo ok", shell=True)\n')

    for arguments, expected in (
        (["test", "--include-off"], 0),
        (["scan", "--error", "src", "tests"], 0),
        (["scan", "--error", str(fixture)], 1),
    ):
        result = subprocess.run(  # noqa: S603 - installed engine, controlled local roots and timeout.
            [tool, *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        assert result.returncode == expected, result.stdout + result.stderr


def test_inspection_handles_poetry_aliases_and_non_dependency_group_entries(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = [{include-group = "lint"}, "pytest_cov>=7"]\n'
        '[tool.poetry.dependencies]\npython = ">=3.13"\nsemgrep = "*"\n'
    )

    assert set(inspect_project(tmp_path)["tools"]) == {"coverage", "semgrep"}


def test_invalid_dependency_list_is_not_reported_as_an_installed_tool(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = "ruff"\n')

    assert inspect_project(tmp_path)["tools"] == []

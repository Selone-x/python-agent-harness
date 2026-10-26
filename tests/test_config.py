"""Configuration rejects ambiguous, misspelled and bypass-enabling input."""

import tomllib
from pathlib import Path

import pytest
from conftest import BASE
from hypothesis import given
from hypothesis import strategies as st

from python_agent_harness.config import (
    boundaries,
    checks,
    load,
    number,
    parse,
    percentage,
    requirements,
    strings,
    table,
    text,
)
from python_agent_harness.paths import HarnessError, inside, source_files


def test_literal_project_contract(project: Path) -> None:
    spec = load(project)

    assert spec.name == "example"
    assert spec.line_minimum == "97"
    assert spec.branch_minimum == "100"
    assert spec.sources == ("src/acme",)
    assert [item.id for item in spec.checks] == ["format", "behavior"]


@pytest.mark.parametrize("value", [None, [], {1: "x"}, {"typo": 1}])
def test_invalid_tables(value: object) -> None:
    with pytest.raises(HarnessError):
        table(value, {"known"}, "example")


@pytest.mark.parametrize("value", [None, 1, True, "", "  ", "bad\x00value"])
def test_invalid_strings(value: object) -> None:
    with pytest.raises(HarnessError):
        text(value, "name")


def test_array_requires_real_list() -> None:
    with pytest.raises(HarnessError):
        strings("not-array", "argv")


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "5", None])
def test_budget_requires_positive_integer(value: object) -> None:
    with pytest.raises(HarnessError):
        number(value, "budget")


@pytest.mark.parametrize("value", [True, None, "NaN", "Infinity", "abc", -1, 101])
def test_invalid_percentage(value: object) -> None:
    with pytest.raises(HarnessError):
        percentage(value, "coverage")


@given(st.integers(min_value=0, max_value=100))
def test_integral_percentage_preserves_exact_value(value: int) -> None:
    assert percentage(value, "coverage") == str(value)


@pytest.mark.parametrize(
    "replacement",
    [
        "schema_version = true",
        "schema_version = 2",
        'schema_version = "1"',
        'kind = "unknown"',
        'python = "3.12"',
        "providers = []",
        'providers = ["github", "github"]',
        'providers = ["other"]',
        'setup = "shell"',
        "sources = []",
        "tests = []",
        "setup = [[]]",
    ],
)
def test_policy_shape_errors(project: Path, replacement: str) -> None:
    key = replacement.split(" = ")[0]
    lines = BASE.splitlines()
    changed = "\n".join(replacement if line.startswith(key + " = ") else line for line in lines)
    (project / ".harness/project.toml").write_text(changed, encoding="utf-8")

    with pytest.raises(HarnessError):
        load(project)


def test_library_requires_package_check() -> None:
    spec = tomllib.loads(BASE.replace('kind = "service"', 'kind = "library"'))
    parsed = parse(spec)

    assert parsed.kind == "library"


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{"id": "x", "group": "static", "argv": []}],
        [{"id": "x", "group": "other", "argv": ["python"]}],
    ],
)
def test_invalid_commands(value: object) -> None:
    with pytest.raises(HarnessError):
        checks(value)


def test_duplicate_commands_and_missing_test_group() -> None:
    command = {"id": "x", "group": "static", "argv": ["python"]}
    for items in ([command], [command, command]):
        with pytest.raises(HarnessError):
            checks(items)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [
            {
                "id": "r",
                "description": "x",
                "enforcement": "check",
                "check": "unknown",
                "evidence": ["tests/x.py"],
            }
        ],
        [{"id": "r", "description": "x", "enforcement": "review", "check": 1}],
    ],
)
def test_unbound_automatic_requirements(value: object, project: Path) -> None:
    with pytest.raises(HarnessError):
        requirements(value, load(project).checks)


def test_valid_automatic_requirement_and_duplicate_id(project: Path) -> None:
    item = {
        "id": "rule",
        "description": "Check explicit examples",
        "enforcement": "check",
        "check": "format",
        "evidence": ["tests/test_rule.py"],
    }

    assert requirements([item], load(project).checks)[0].evidence == ("tests/test_rule.py",)
    with pytest.raises(HarnessError):
        requirements([item, item], load(project).checks)


@pytest.mark.parametrize(
    "value",
    [None, [{"source": "x", "forbidden": []}], [{"source": "bad-name", "forbidden": ["other"]}]],
)
def test_invalid_architecture(value: object) -> None:
    with pytest.raises(HarnessError):
        boundaries(value)


@pytest.mark.parametrize("relative", ["", "/etc/passwd", "../escape", "x/../../y", "x\\y"])
def test_path_escape_is_rejected(project: Path, relative: str) -> None:
    with pytest.raises(HarnessError):
        inside(project, relative)


def test_symlink_escape_is_rejected(project: Path) -> None:
    (project / "escape").symlink_to(project.parent, target_is_directory=True)

    with pytest.raises(HarnessError):
        inside(project, "escape/outside")


def test_inventory_includes_unimported_and_single_file(project: Path) -> None:
    unseen = project / "src/acme/unseen.py"
    unseen.write_text("raise RuntimeError('not imported')\n", encoding="utf-8")

    assert source_files(project, ("src/acme", "src/acme/unseen.py")) == tuple(
        sorted((project / "src/acme/__init__.py", unseen))
    )
    with pytest.raises(HarnessError):
        source_files(project, ("missing",))

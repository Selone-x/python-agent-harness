"""Literal source graphs and coverage counters are independent test oracles."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from python_agent_harness.audit import (
    architecture,
    audit_project,
    evidence,
    fingerprint,
    ownership,
    suppressions,
)
from python_agent_harness.config import load
from python_agent_harness.coverage import counters, verify_coverage
from python_agent_harness.model import Boundary, Requirement
from python_agent_harness.paths import HarnessError
from python_agent_harness.render import apply, plan


def coverage_data(
    lines: int = 1, total: int = 1, branches: int = 0, branch_total: int = 0
) -> dict[str, object]:
    summary = {
        "covered_lines": lines,
        "num_statements": total,
        "covered_branches": branches,
        "num_branches": branch_total,
    }
    return {"totals": summary, "files": {"src/acme/__init__.py": {"summary": summary}}}


def write_coverage(project: Path, document: object) -> None:
    directory = project / ".harness/reports"
    directory.mkdir(exist_ok=True)
    (directory / "coverage.json").write_text(json.dumps(document), encoding="utf-8")


@pytest.mark.parametrize(
    "covered,total,minimum,passes",
    [
        (97, 100, "97", True),
        (96, 100, "97", False),
        (970, 1000, "97.0", True),
        (969, 1000, "97", False),
    ],
)
def test_line_threshold_is_inclusive_and_unrounded(
    project: Path, covered: int, total: int, minimum: str, passes: bool
) -> None:
    write_coverage(project, coverage_data(covered, total))

    result = verify_coverage(project, replace(load(project), line_minimum=minimum))

    assert (result[1].status == "pass") is passes


def test_no_branches_is_valid_but_missing_one_branch_is_not(project: Path) -> None:
    write_coverage(project, coverage_data())
    assert verify_coverage(project, load(project))[2].status == "pass"

    write_coverage(project, coverage_data(branches=1, branch_total=2))
    assert verify_coverage(project, load(project))[2].status == "fail"


def test_unimported_source_is_required(project: Path) -> None:
    (project / "src/acme/forgotten.py").write_text("value = 2\n", encoding="utf-8")
    write_coverage(project, coverage_data())

    assert verify_coverage(project, load(project))[0].status == "fail"


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"files": {}},
        {"totals": {"covered_lines": 0}, "files": {}},
        {
            "totals": {
                "covered_lines": 0,
                "num_statements": 0,
                "covered_branches": 0,
                "num_branches": 0,
            },
            "files": {},
        },
    ],
)
def test_missing_empty_or_malformed_coverage_fails(project: Path, document: object) -> None:
    write_coverage(project, document)

    with pytest.raises(HarnessError):
        verify_coverage(project, load(project))


@pytest.mark.parametrize(
    "field,value",
    [
        ("covered_lines", True),
        ("num_statements", -1),
        ("covered_branches", "1"),
        ("covered_lines", 2),
        ("covered_branches", 1),
    ],
)
def test_coverage_rejects_inflated_and_boolean_counters(field: str, value: object) -> None:
    data: dict[str, object] = {
        "covered_lines": 1,
        "num_statements": 1,
        "covered_branches": 0,
        "num_branches": 0,
    }
    data[field] = value

    with pytest.raises(HarnessError):
        counters(data)


def test_relative_alias_and_transitive_imports(project: Path) -> None:
    package = project / "src/acme"
    (package / "domain.py").write_text("from . import helper\n", encoding="utf-8")
    (package / "helper.py").write_text(
        "import requests as http\nimport acme.domain\n", encoding="utf-8"
    )
    spec = replace(
        load(project), boundaries=(Boundary(source="acme.domain", forbidden=("requests",)),)
    )

    violations = architecture(project, spec)

    assert [(item.code, item.message) for item in violations] == [
        ("architecture.import", "acme.domain depends on forbidden requests")
    ]


def test_unmatched_boundary_is_not_a_vacuous_success(project: Path) -> None:
    spec = replace(
        load(project), boundaries=(Boundary(source="typo.domain", forbidden=("requests",)),)
    )

    assert architecture(project, spec)[0].code == "architecture.source"


def test_neighbor_package_is_not_matched(project: Path) -> None:
    (project / "src/acme/__init__.py").write_text("import requests_helpers\n", encoding="utf-8")
    spec = replace(load(project), boundaries=(Boundary(source="acme", forbidden=("requests",)),))

    assert architecture(project, spec) == ()


def test_suppression_requires_specific_rule_and_reason(project: Path) -> None:
    source = project / "src/acme/__init__.py"
    source.write_text(
        "x = 1  # noqa\ny = 2  # noqa: F841 - intentional fixture\n", encoding="utf-8"
    )

    assert [(item.code, item.message) for item in suppressions(project, load(project))] == [
        ("suppression.reason", "Line 1: suppression needs a specific rule and explanation")
    ]


def test_missing_evidence_and_review_are_distinct(project: Path) -> None:
    requirement = Requirement(
        id="architecture",
        description="A concrete boundary",
        enforcement="check",
        check="format",
        evidence=("tests/test_missing.py",),
    )
    spec = replace(load(project), requirements=(requirement, *load(project).requirements))

    assert [item.status for item in evidence(project, spec)] == ["fail", "review"]


def test_policy_fingerprint_changes_on_source_test_or_spec_changes(project: Path) -> None:
    spec = load(project)
    before = fingerprint(project, spec)
    (project / "tests/test_contract.py").write_text(
        "def test_contract():\n    assert 1 == 1\n", encoding="utf-8"
    )
    assert fingerprint(project, spec) != before

    apply(project, plan(project, spec))
    policy = project / ".harness/project.toml"
    policy.write_text(policy.read_text() + '\n[quality]\nbranches = "50"\n', encoding="utf-8")
    assert ownership(project)[0].code == "policy.changed"
    assert any(item.status == "fail" for item in audit_project(project, load(project)))

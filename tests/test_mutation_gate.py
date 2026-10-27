"""Literal mutmut inventories must reject every inconclusive or undetected change."""

from pathlib import Path

import pytest

from python_agent_harness import cli, mutations
from python_agent_harness.config import load
from python_agent_harness.model import Check, CommandResult, successful


@pytest.mark.parametrize(
    "inventory",
    [
        "",
        "not a mutation inventory",
        "toy.x_f__mutmut_1: killed\ntoy.x_f__mutmut_1: killed",
        "toy.x_f__mutmut_1: killed\ntruncated output",
        "toy.x_f__mutmut_1: survived",
        "toy.x_f__mutmut_1: timeout",
        "toy.x_f__mutmut_1: suspicious",
        "toy.x_f__mutmut_1: no tests",
        "toy.x_f__mutmut_1: not checked",
        "toy.x_f__mutmut_1: skipped",
        "toy.x_f__mutmut_1: unknown-future-status",
    ],
)
def test_mutation_gate_rejects_incomplete_or_unsuccessful_inventory(inventory: str) -> None:
    assert not successful(mutations.verify_inventory(inventory))


def test_mutation_gate_accepts_a_complete_killed_inventory() -> None:
    findings = mutations.verify_inventory(
        "  toy.x_f__mutmut_1: killed\n\n  toy.x_f__mutmut_2: killed\n"
    )

    assert successful(findings)
    assert "2" in findings[0].message


@pytest.mark.parametrize(
    ("program", "expected"),
    [
        ("print('toy.x_f__mutmut_1: killed')", True),
        ("print('toy.x_f__mutmut_1: survived')", False),
        ("raise SystemExit(1)", False),
    ],
)
def test_mutation_gate_observes_the_inventory_command(
    project: Path, program: str, expected: bool
) -> None:
    findings = mutations.mutation_gate(project, load(project), ("@python", "-c", program))

    assert successful(findings) is expected


def test_mutation_gate_missing_tool_cannot_pass(project: Path) -> None:
    findings = mutations.mutation_gate(project, load(project), ("missing-mutmut-executable",))

    assert findings[0].status == "blocked"


def test_mutation_gate_default_uses_the_locked_optional_group(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def capture(root: Path, command: Check, output_limit: int) -> CommandResult:
        assert command.argv == (
            "uv",
            "run",
            "--locked",
            "--group",
            "mutation",
            "mutmut",
            "results",
            "--all",
            "true",
        )
        assert command.timeout == 30
        assert output_limit == 1048576
        log = root / ".harness/reports/logs/mutation-inventory.log"
        log.parent.mkdir(parents=True)
        log.write_text("toy.x_f__mutmut_1: killed\n")
        return CommandResult(id=command.id, status="pass", exit_code=0, detail="finished")

    monkeypatch.setattr(mutations, "execute", capture)

    assert successful(mutations.mutation_gate(project, load(project), ()))


@pytest.mark.parametrize(("status", "exit_code"), [("killed", 0), ("survived", 1)])
def test_mutation_gate_cli_returns_the_observed_acceptance(
    project: Path, status: str, exit_code: int
) -> None:
    result = cli.main(
        [
            "--root",
            str(project),
            "mutation-gate",
            "--",
            "@python",
            "-c",
            f"print('toy.x_f__mutmut_1: {status}')",
        ]
    )

    assert result == exit_code

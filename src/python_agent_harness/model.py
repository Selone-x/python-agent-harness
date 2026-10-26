"""Immutable requirements, commands and diagnostic results."""

from dataclasses import dataclass
from typing import Literal

type Group = Literal["static", "tests", "package", "deep"]
type Status = Literal["pass", "fail", "blocked", "review", "not_applicable"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Finding:
    """An observable result, with an actionable explanation."""

    code: str
    status: Status
    message: str
    path: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class Check:
    """A sequential, bounded command; argv is never passed to a shell."""

    id: str
    group: Group
    argv: tuple[str, ...]
    timeout: int = 120


@dataclass(frozen=True, slots=True, kw_only=True)
class Requirement:
    """A project requirement and its declared enforcement evidence."""

    id: str
    description: str
    enforcement: Literal["check", "test", "review"]
    check: str = ""
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Boundary:
    """A forbidden dependency edge between module prefixes."""

    source: str
    forbidden: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Spec:
    """Approved project choices; no trading-specific architecture is imposed."""

    name: str
    kind: Literal["library", "service", "cli", "research"]
    python: str
    sources: tuple[str, ...]
    tests: tuple[str, ...]
    providers: tuple[str, ...]
    setup: tuple[tuple[str, ...], ...]
    checks: tuple[Check, ...]
    requirements: tuple[Requirement, ...]
    boundaries: tuple[Boundary, ...] = ()
    line_minimum: str = "97"
    branch_minimum: str = "100"
    coverage: str = ".harness/reports/coverage.json"
    output_limit: int = 1_048_576
    deep_budget: int = 900
    description: str = ""
    inputs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandResult:
    """The actual observed completion of a command."""

    id: str
    status: Status
    exit_code: int | None
    detail: str


def successful(findings: tuple[Finding, ...]) -> bool:
    """Review and inapplicability are explicit, rather than disguised failures."""
    return not any(item.status in {"fail", "blocked"} for item in findings)

"""Strict parsing of the single source of project policy."""

import json
import re
import tomllib
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal, cast

from .model import Boundary, Check, Group, Requirement, Spec
from .paths import HarnessError, inside

SPEC_PATH = ".harness/project.toml"
GROUPS = frozenset({"static", "tests", "package", "deep"})


def table(value: object, keys: set[str], context: str) -> dict[str, object]:
    """Unknown keys are errors so a typo cannot silently disable enforcement."""
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise HarnessError(f"{context} must be a table")
    data = cast("dict[str, object]", value)
    if extra := data.keys() - keys:
        raise HarnessError(f"Unknown {context} keys: {sorted(extra)}")
    return data


def text(value: object, context: str) -> str:
    """Require a real, nonempty string without null bytes."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise HarnessError(f"{context} must be a nonempty string")
    return value


def strings(value: object, context: str) -> tuple[str, ...]:
    """Read argv or a list of paths without implicit coercion."""
    if not isinstance(value, list):
        raise HarnessError(f"{context} must be an array")
    return tuple(text(item, context) for item in value)


def number(value: object, context: str, minimum: int = 1) -> int:
    """Bool must not be accepted as an integer budget."""
    if type(value) is not int or value < minimum:
        raise HarnessError(f"{context} must be an integer >= {minimum}")
    return value


def percentage(value: object, context: str) -> str:
    """Use exact decimal comparisons for inclusive coverage boundaries."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise HarnessError(f"{context} must be a percentage")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as error:
        raise HarnessError(f"Invalid {context}") from error
    if not parsed.is_finite() or not 0 <= parsed <= 100:
        raise HarnessError(f"{context} must be between 0 and 100")
    return str(parsed)


def choice(value: object, options: set[str], context: str) -> str:
    """Validate a closed vocabulary."""
    result = text(value, context)
    if result not in options:
        raise HarnessError(f"Unsupported {context}: {result}")
    return result


def checks(value: object) -> tuple[Check, ...]:
    """Each declared command is required within its group."""
    if not isinstance(value, list) or not value:
        raise HarnessError("checks must be a nonempty array of tables")
    result: list[Check] = []
    for entry in value:
        data = table(entry, {"id", "group", "argv", "timeout"}, "check")
        argv = strings(data.get("argv"), "check.argv")
        if not argv:
            raise HarnessError("check.argv cannot be empty")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", text(data.get("id"), "check.id")):
            raise HarnessError("check.id must be a safe identifier")
        result.append(
            Check(
                id=text(data.get("id"), "check.id"),
                group=cast("Group", choice(data.get("group"), set(GROUPS), "check.group")),
                argv=argv,
                timeout=number(data.get("timeout", 120), "check.timeout"),
            )
        )
    if len({item.id for item in result}) != len(result):
        raise HarnessError("check ids must be unique")
    if not {"static", "tests"} <= {item.group for item in result}:
        raise HarnessError("static and tests groups are required")
    return tuple(result)


def requirements(value: object, available: tuple[Check, ...]) -> tuple[Requirement, ...]:
    """Automatic requirements must identify their check and evidence fixtures."""
    if not isinstance(value, list) or not value:
        raise HarnessError("At least one project requirement is required")
    result: list[Requirement] = []
    for entry in value:
        data = table(
            entry, {"id", "description", "enforcement", "check", "evidence"}, "requirement"
        )
        mode = choice(data.get("enforcement"), {"check", "test", "review"}, "enforcement")
        evidence = strings(data.get("evidence", []), "requirement.evidence")
        check = data.get("check", "")
        if not isinstance(check, str):
            raise HarnessError("requirement.check must be a string")
        if mode != "review" and (check not in {item.id for item in available} or not evidence):
            raise HarnessError("Automatic requirements need a known check and evidence files")
        result.append(
            Requirement(
                id=text(data.get("id"), "requirement.id"),
                description=text(data.get("description"), "requirement.description"),
                enforcement=cast("LiteralMode", mode),
                check=check,
                evidence=evidence,
            )
        )
    if len({item.id for item in result}) != len(result):
        raise HarnessError("requirement ids must be unique")
    return tuple(result)


type LiteralMode = Literal["check", "test", "review"]


def boundaries(value: object) -> tuple[Boundary, ...]:
    """Module names, rather than a prescribed layer hierarchy, define architecture."""
    if not isinstance(value, list):
        raise HarnessError("boundaries must be an array")
    result: list[Boundary] = []
    for entry in value:
        data = table(entry, {"source", "forbidden"}, "boundary")
        source = text(data.get("source"), "boundary.source")
        forbidden = strings(data.get("forbidden"), "boundary.forbidden")
        if not forbidden or any(
            not re.fullmatch(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", name)
            for name in (source, *forbidden)
        ):
            raise HarnessError("Boundaries require dotted module names")
        result.append(Boundary(source=source, forbidden=forbidden))
    return tuple(result)


def parse(data: dict[str, object]) -> Spec:
    """Turn untrusted TOML into a validated immutable specification."""
    table(
        data,
        {
            "schema_version",
            "name",
            "kind",
            "python",
            "sources",
            "tests",
            "providers",
            "setup",
            "checks",
            "requirements",
            "boundaries",
            "quality",
            "description",
            "inputs",
        },
        "project",
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise HarnessError("Supported schema_version is 1")
    quality = table(
        data.get("quality", {}),
        {"lines", "branches", "coverage", "output_limit", "deep_budget"},
        "quality",
    )
    commands = checks(data.get("checks"))
    providers = strings(data.get("providers"), "providers")
    if (
        not providers
        or set(providers) - {"github", "gitlab"}
        or len(set(providers)) != len(providers)
    ):
        raise HarnessError("Select unique providers from github and gitlab")
    version = text(data.get("python"), "python")
    if not re.fullmatch(r"3\.(?:1[3-9]|[2-9][0-9])", version):
        raise HarnessError("Harness execution requires Python 3.13 or later")
    setup = data.get("setup", [])
    if not isinstance(setup, list):
        raise HarnessError("setup must be an array of argv arrays")
    return Spec(
        name=text(data.get("name"), "name"),
        kind=cast(
            "Kind", choice(data.get("kind"), {"library", "service", "cli", "research"}, "kind")
        ),
        python=version,
        sources=strings(data.get("sources"), "sources"),
        tests=strings(data.get("tests"), "tests"),
        providers=providers,
        setup=tuple(strings(item, "setup.argv") for item in setup),
        checks=commands,
        requirements=requirements(data.get("requirements"), commands),
        boundaries=boundaries(data.get("boundaries", [])),
        line_minimum=percentage(quality.get("lines", 97), "quality.lines"),
        branch_minimum=percentage(quality.get("branches", 100), "quality.branches"),
        coverage=text(
            quality.get("coverage", ".harness/reports/coverage.json"), "quality.coverage"
        ),
        output_limit=number(quality.get("output_limit", 1_048_576), "quality.output_limit"),
        deep_budget=number(quality.get("deep_budget", 900), "quality.deep_budget"),
        description=text(data.get("description", "Project-specific Python harness"), "description"),
        inputs=strings(data.get("inputs", []), "inputs"),
    )


type Kind = Literal["library", "service", "cli", "research"]


def load(root: Path) -> Spec:
    """Read the specification and validate every declared path before use."""
    spec = parse(tomllib.loads(inside(root, SPEC_PATH).read_text(encoding="utf-8")))
    for path in (
        *spec.sources,
        *spec.tests,
        *spec.inputs,
        spec.coverage,
        *(item for rule in spec.requirements for item in rule.evidence),
    ):
        inside(root, path)
        if path in {".", "./"}:
            raise HarnessError("Select explicit package, test or input roots, not the project root")
    if not spec.sources or not spec.tests or any(not command for command in spec.setup):
        raise HarnessError("sources, tests and each setup command must be nonempty")
    if spec.kind == "library" and not any(item.group == "package" for item in spec.checks):
        raise HarnessError("Libraries require a package check")
    return spec


def literal(value: object) -> str:
    """Serialize TOML-compatible scalar/array values with escaped strings."""
    return json.dumps(value, ensure_ascii=False)

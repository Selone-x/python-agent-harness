"""Strict acceptance of bounded, complete mutmut inventories; no implicit campaign."""

import re
from collections import Counter
from pathlib import Path

from .model import Check, Finding, Spec
from .paths import HarnessError, inside
from .runner import execute


def parse_inventory(content: str) -> dict[str, str]:
    """Reject empty, duplicate and malformed records instead of dropping evidence."""
    records: dict[str, str] = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*(\S+__mutmut_[1-9]\d*):\s+([a-z][a-z _-]*)\s*", line)
        if match is None or match[1] in records:
            raise HarnessError("Malformed or duplicate mutmut inventory record")
        records[match[1]] = match[2].strip()
    if not records:
        raise HarnessError("The mutation inventory is empty; no measured scope was established")
    return records


def verify_inventory(content: str) -> tuple[Finding, ...]:
    """This explicit strict preset accepts only a nonempty inventory of killed mutants."""
    try:
        records = parse_inventory(content)
    except HarnessError as error:
        return (Finding(code="mutation.inventory", status="fail", message=str(error)),)
    counts = dict(sorted(Counter(records.values()).items()))
    return (
        Finding(
            code="mutation.inventory",
            status="pass",
            message=f"Observed {len(records)} unique mutation results",
        ),
        Finding(
            code="mutation.sensitivity",
            status="pass" if set(counts) == {"killed"} else "fail",
            message=f"Strict all-killed acceptance: {counts}",
        ),
    )


def mutation_gate(root: Path, spec: Spec, argv: tuple[str, ...]) -> tuple[Finding, ...]:
    """Read current results through a bounded command; never generate or apply mutants."""
    command = Check(
        id="mutation-inventory",
        group="deep",
        argv=argv
        or ("uv", "run", "--locked", "--group", "mutation", "mutmut", "results", "--all", "true"),
        timeout=30,
    )
    result = execute(root, command, spec.output_limit)
    if result.status != "pass":
        return (
            Finding(
                code="mutation.command",
                status=result.status,
                message=(
                    f"Mutation inventory command failed: {result.detail}; exit={result.exit_code}"
                ),
            ),
        )
    log = inside(root, ".harness/reports/logs/mutation-inventory.log")
    return verify_inventory(log.read_text(encoding="utf-8"))

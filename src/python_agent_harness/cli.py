"""A CLI shared by installed tools and the generated self-contained runner."""

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .audit import audit_project
from .bootstrap import initialize
from .config import load
from .coverage import verify_coverage
from .discovery import inspect_project
from .model import Finding, successful
from .package import verify_package
from .paths import HarnessError
from .providers import doctor
from .render import apply, describe, plan
from .runner import gate, run_group, run_setup


def parser() -> argparse.ArgumentParser:
    """Make every filesystem/network mutation an explicit command."""
    command = argparse.ArgumentParser(prog="harness")
    command.add_argument("--root", type=Path, default=Path.cwd())
    command.add_argument("--version", action="version", version=__version__)
    modes = command.add_subparsers(dest="mode", required=True)
    modes.add_parser("inspect", help="Read existing tooling, instructions and layout")
    init = modes.add_parser("init", help="Write a draft spec; optionally scaffold an empty project")
    init.add_argument("--name", required=True)
    init.add_argument("--package", required=True)
    init.add_argument(
        "--kind", choices=("library", "service", "cli", "research"), default="library"
    )
    init.add_argument("--provider", action="append", choices=("github", "gitlab"))
    init.add_argument("--scaffold", action="store_true")
    modes.add_parser("validate", help="Validate the agreed policy and declared evidence paths")
    rendering = modes.add_parser("render", help="Preview owned changes; apply explicitly")
    rendering.add_argument("--apply", action="store_true")
    rendering.add_argument("--check", action="store_true")
    modes.add_parser("setup", help="Run the spec's explicit, bounded dependency setup")
    checking = modes.add_parser("check", help="Run required checks and write bound evidence")
    checking.add_argument("--group", choices=("static", "tests", "package", "deep"))
    modes.add_parser("audit", help="Inspect drift, suppressions, architecture and evidence")
    modes.add_parser("gate", help="Require successful, current evidence from every required group")
    modes.add_parser(
        "coverage", help="Verify exact coverage ratios and the complete source inventory"
    )
    diagnosis = modes.add_parser(
        "doctor", help="Read actual server protections; never change settings"
    )
    diagnosis.add_argument("--provider", choices=("github", "gitlab"), required=True)
    diagnosis.add_argument("--repository", required=True)
    package = modes.add_parser("package", help="Verify distributions and import the built wheel")
    package.add_argument("--module", required=True)
    return command


def emit(value: object) -> None:
    """Output stable JSON usable by humans, CI and coding agents."""
    print(json.dumps(value, indent=2, ensure_ascii=False))


def findings_result(findings: tuple[Finding, ...]) -> int:
    """Review-only requirements remain visible in machine-readable output."""
    emit(
        {
            "status": "pass" if successful(findings) else "fail",
            "findings": [asdict(item) for item in findings],
        }
    )
    return 0 if successful(findings) else 1


def render_command(root: Path, args: argparse.Namespace) -> int:
    """A check mode never writes, including when drift or conflicts are found."""
    if args.apply and args.check:
        raise HarnessError("Choose --apply or --check, not both")
    changes = plan(root, load(root))
    preview = describe(root, changes)
    if args.apply:
        apply(root, changes)
    emit(
        {
            "status": "drift" if changes and args.check else "pass",
            "applied": args.apply,
            "changes": preview,
        }
    )
    return 1 if changes and args.check else 0


def check_command(root: Path, args: argparse.Namespace) -> int:
    """Run groups sequentially, with no implicit setup or deep-workload launch."""
    spec = load(root)
    groups = [args.group] if args.group else sorted({item.group for item in spec.checks} - {"deep"})
    reports = [run_group(root, spec, group) for group in groups]
    emit({"reports": reports})
    return 0 if all(report["status"] == "pass" for report in reports) else 1


def dispatch(root: Path, args: argparse.Namespace) -> int:
    """Route commands without letting inspection silently mutate application code."""
    if args.mode == "inspect":
        emit(inspect_project(root))
    elif args.mode == "init":
        root.mkdir(parents=True, exist_ok=True)
        paths = initialize(
            root,
            args.name,
            args.package,
            args.kind,
            tuple(args.provider or ("github",)),
            args.scaffold,
        )
        emit(
            {
                "status": "draft",
                "created": paths,
                "next": "Agree requirements; validate, preview render, apply and run setup.",
            }
        )
    elif args.mode == "validate":
        spec = load(root)
        emit(
            {
                "status": "pass",
                "name": spec.name,
                "requirements": len(spec.requirements),
                "review_requirements": [
                    item.id for item in spec.requirements if item.enforcement == "review"
                ],
            }
        )
    elif args.mode == "render":
        return render_command(root, args)
    elif args.mode == "check":
        return check_command(root, args)
    else:
        return inspect_commands(root, args)
    return 0


def inspect_commands(root: Path, args: argparse.Namespace) -> int:
    """Commands that report actual observations rather than policy intentions."""
    if args.mode == "doctor":
        return findings_result(doctor(root, args.provider, args.repository))
    if args.mode == "package":
        verify_package(root, args.module)
        emit({"status": "pass", "module": args.module})
        return 0
    spec = load(root)
    if args.mode == "coverage":
        return findings_result(verify_coverage(root, spec))
    if args.mode == "audit":
        return findings_result(audit_project(root, spec))
    if args.mode == "gate":
        return findings_result(gate(root, spec))
    results = run_setup(root, spec)
    emit({"setup": [asdict(item) for item in results]})
    return 0 if all(item.status == "pass" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    """Return 1 for observed violations and 2 for invalid/unavailable configuration."""
    args = parser().parse_args(argv)
    try:
        return dispatch(args.root.resolve(), args)
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as error:
        emit({"status": "blocked", "error": str(error)})
        return 2

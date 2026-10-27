"""Read-only tool declarations; declaration is not proof of installation or enforcement."""

import re
import tomllib
from pathlib import Path
from typing import TypedDict

from .paths import inside

TOOLS = (
    "ruff",
    "black",
    "isort",
    "mypy",
    "pyright",
    "ty",
    "pytest",
    "coverage",
    "hypothesis",
    "vulture",
    "complexipy",
    "mutmut",
    "schemathesis",
    "fixit",
    "import-linter",
    "ast-grep",
    "semgrep",
    "radon",
    "xenon",
)
ALIASES = {"pytest-cov": "coverage", "ast-grep-cli": "ast-grep", "importlinter": "import-linter"}
CONFIG_FILES = {
    "ast-grep": ("sgconfig.yml", "sgconfig.yaml"),
    "schemathesis": ("schemathesis.toml",),
    "complexipy": ("complexipy.toml", ".complexipy.toml"),
    "semgrep": (".semgrep.yml", ".semgrep.yaml"),
    "import-linter": (".importlinter",),
    "fixit": (".fixit.toml",),
}


class ToolEvidence(TypedDict):
    """Sources of declaration, without a claim about successful enforcement."""

    configuration: list[str]
    dependencies: list[str]
    files: list[str]


class Inspection(TypedDict):
    """Serializable project facts used by an adopting agent."""

    root: str
    project: dict[str, object]
    tools: list[str]
    tool_evidence: dict[str, ToolEvidence]
    lockfiles: list[str]
    instructions: list[str]
    ci: list[str]
    source_candidates: list[str]
    test_candidates: list[str]
    architecture: str


def mapping(value: object) -> dict[str, object]:
    """Read available tables without silently changing the inspected metadata."""
    return value if isinstance(value, dict) else {}


def dependency_sets(data: dict[str, object]) -> dict[str, object]:
    """Inspect ordinary, optional, grouped and Poetry dependency declarations."""
    project = mapping(data.get("project"))
    groups = {"project": project.get("dependencies", [])}
    groups.update(
        (f"optional:{name}", items)
        for name, items in mapping(project.get("optional-dependencies")).items()
    )
    groups.update(
        (f"group:{name}", items) for name, items in mapping(data.get("dependency-groups")).items()
    )
    poetry = mapping(mapping(data.get("tool")).get("poetry"))
    groups["poetry"] = list(mapping(poetry.get("dependencies")))
    return groups


def declared_packages(declarations: object) -> set[str]:
    """Normalize PEP 508 names; include-group entries are inspected in their own group."""
    if not isinstance(declarations, list):
        return set()
    return {
        re.split(r"[\s\[<>=!~;@]", item.strip(), maxsplit=1)[0].lower().replace("_", "-")
        for item in declarations
        if isinstance(item, str)
    }


def tool_evidence(root: Path, data: dict[str, object]) -> dict[str, ToolEvidence]:
    """Find configuration and dependencies independently, without executing tools."""
    configured = mapping(data.get("tool"))
    dependencies = {
        group: declared_packages(items) for group, items in dependency_sets(data).items()
    }
    result: dict[str, ToolEvidence] = {}
    for name in TOOLS:
        evidence = ToolEvidence(
            configuration=[f"tool.{key}" for key in configured if ALIASES.get(key, key) == name],
            dependencies=[
                group
                for group, packages in dependencies.items()
                if name in {ALIASES.get(package, package) for package in packages}
            ],
            files=[path for path in CONFIG_FILES.get(name, ()) if inside(root, path).is_file()],
        )
        if any(evidence.values()):
            result[name] = evidence
    return result


def inspect_project(root: Path) -> Inspection:
    """Report facts rather than inventing architecture from directory names."""
    metadata = inside(root, "pyproject.toml")
    data = tomllib.loads(metadata.read_text(encoding="utf-8")) if metadata.exists() else {}
    evidence = tool_evidence(root, data)
    return Inspection(
        root=str(root),
        project=mapping(data.get("project")),
        tools=list(evidence),
        tool_evidence=evidence,
        lockfiles=[
            name
            for name in ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.txt")
            if inside(root, name).exists()
        ],
        instructions=[name for name in ("AGENTS.md", "CLAUDE.md") if inside(root, name).exists()],
        ci=[
            name for name in (".github/workflows", ".gitlab-ci.yml") if inside(root, name).exists()
        ],
        source_candidates=[name for name in ("src", "app", "lib") if inside(root, name).is_dir()],
        test_candidates=[name for name in ("tests", "test") if inside(root, name).is_dir()],
        architecture="requires agreement; directory names do not establish dependency rules",
    )

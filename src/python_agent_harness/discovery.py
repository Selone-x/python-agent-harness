"""Read-only reconnaissance, preserving an existing project's tool choices."""

import tomllib
from pathlib import Path

from .paths import inside


def inspect_project(root: Path) -> dict[str, object]:
    """Report facts rather than inventing architecture from directory names."""
    metadata = inside(root, "pyproject.toml")
    data = tomllib.loads(metadata.read_text(encoding="utf-8")) if metadata.exists() else {}
    tools = data.get("tool", {})
    candidates = ("ruff", "black", "isort", "mypy", "pyright", "ty", "pytest", "coverage")
    return {
        "root": str(root),
        "project": data.get("project", {}),
        "tools": [name for name in candidates if name in tools],
        "lockfiles": [
            name
            for name in ("uv.lock", "poetry.lock", "Pipfile.lock", "requirements.txt")
            if inside(root, name).exists()
        ],
        "instructions": [
            name for name in ("AGENTS.md", "CLAUDE.md") if inside(root, name).exists()
        ],
        "ci": [
            name for name in (".github/workflows", ".gitlab-ci.yml") if inside(root, name).exists()
        ],
        "source_candidates": [
            name for name in ("src", "app", "lib") if inside(root, name).is_dir()
        ],
        "test_candidates": [name for name in ("tests", "test") if inside(root, name).is_dir()],
        "architecture": "requires agreement; directory names do not establish dependency rules",
    }

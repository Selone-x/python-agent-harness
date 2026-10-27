"""Portable skill metadata and local references are structurally valid."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml

SKILLS = Path(__file__).resolve().parents[1] / "skills"


@pytest.mark.parametrize(
    "name",
    [
        "build-python-harness",
        "spec-to-code-compliance",
        "semgrep-rule-creator",
        "property-based-testing",
        "mutation-testing",
    ],
)
def test_skill_can_be_copied_without_broken_local_references(name: str) -> None:
    directory = SKILLS / name
    entrypoint = (directory / "SKILL.md").read_text()
    metadata = yaml.safe_load(entrypoint.split("---", 2)[1])

    assert metadata["name"] == name
    assert isinstance(metadata["description"], str)
    assert metadata["description"].strip()
    for document in directory.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", document.read_text()):
            link = urlsplit(target)
            if link.scheme or not link.path:
                continue
            path = (document.parent / unquote(link.path)).resolve()
            assert path.is_relative_to(directory.resolve()), (document, target)
            assert path.is_file(), (document, target)

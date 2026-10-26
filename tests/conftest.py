"""Small, disk-backed projects with literal independent expected counters."""

from pathlib import Path

import pytest

BASE = """schema_version = 1
name = "example"
kind = "service"
python = "3.13"
description = "Example service with no prescribed layer hierarchy"
sources = ["src/acme"]
tests = ["tests"]
providers = ["github", "gitlab"]
setup = []

[[checks]]
id = "format"
group = "static"
argv = ["@python", "-c", "pass"]
timeout = 5

[[checks]]
id = "behavior"
group = "tests"
argv = ["@python", "-c", "pass"]
timeout = 5

[[requirements]]
id = "oracle"
description = "Review expected values against the contract"
enforcement = "review"
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A real package and test directory, without trading or external dependencies."""
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness/project.toml").write_text(BASE, encoding="utf-8")
    package = tmp_path / "src/acme"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    return tmp_path

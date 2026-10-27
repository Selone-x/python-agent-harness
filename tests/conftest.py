"""Small, disk-backed projects with literal independent expected counters."""

import os
from pathlib import Path

import pytest
from hypothesis import settings

from python_agent_harness.bootstrap import HYPOTHESIS_PROFILES

(Path(__file__).resolve().parents[1] / ".reports").mkdir(parents=True, exist_ok=True)

for profile_name, examples, steps in HYPOTHESIS_PROFILES:
    settings.register_profile(
        profile_name,
        max_examples=examples,
        stateful_step_count=steps,
        print_blob=True,
        deadline=200,
        suppress_health_check=(),
        derandomize=profile_name != "dev",
    )
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

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

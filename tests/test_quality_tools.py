"""Real engines accept valid code/responses and reject deliberate violations."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import schemathesis
from hypothesis import given, settings
from schemathesis.core.failures import FailureGroup
from werkzeug.wrappers import Request, Response

from python_agent_harness.bootstrap import initialize
from python_agent_harness.config import load

SCHEMA = schemathesis.openapi.from_dict(
    {
        "openapi": "3.0.3",
        "info": {"title": "Local contract fixture", "version": "1"},
        "paths": {
            "/echo": {
                "get": {
                    "parameters": [
                        {
                            "name": "value",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 0, "maximum": 3},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Echoed integer",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "integer", "minimum": 0, "maximum": 3}
                                }
                            },
                        }
                    },
                }
            }
        },
    }
)


@Request.application
def valid_api(request: Request) -> Response:
    """A local WSGI boundary with an independently declared response schema."""
    return Response(json.dumps(int(request.args["value"])), mimetype="application/json")


@Request.application
def invalid_api(_request: Request) -> Response:
    """Deliberately violate the integer response contract without network IO."""
    return Response('"wrong type"', mimetype="application/json")


@pytest.fixture(scope="module")
def _ready_contract_validator() -> None:
    """Initialize lazy schema checks before Hypothesis times generated examples."""
    case = SCHEMA["/echo"]["GET"].Case(query={"value": 0})
    response = case.call_and_validate(app=valid_api)

    assert response.status_code == 200


@settings(max_examples=5, derandomize=True, database=None)
@given(case=SCHEMA["/echo"]["GET"].as_strategy())
def test_schemathesis_generated_requests_satisfy_local_contract(
    _ready_contract_validator: None, case: schemathesis.Case
) -> None:
    response = case.call_and_validate(app=valid_api)

    assert response.status_code == 200


def test_schemathesis_rejects_a_response_with_the_wrong_type() -> None:
    case = SCHEMA["/echo"]["GET"].Case(query={"value": 0})

    with pytest.raises(FailureGroup, match="Response violates schema"):
        case.call_and_validate(app=invalid_api)


def test_schemathesis_initialization_is_outside_generated_example_deadlines(tmp_path: Path) -> None:
    plugin = tmp_path / "delayed_contract_validator.py"
    plugin.write_text(
        "import time\nimport schemathesis\n\n"
        "original = schemathesis.Case.call_and_validate\n"
        "first_call = True\n\n"
        "def delayed(self, *args, **kwargs):\n"
        "    global first_call\n"
        "    if first_call:\n"
        "        first_call = False\n"
        "        time.sleep(0.35)\n"
        "    return original(self, *args, **kwargs)\n\n"
        "schemathesis.Case.call_and_validate = delayed\n"
    )
    root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(tmp_path), str(root / "src"))),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "HYPOTHESIS_PROFILE": "ci",
    }
    result = subprocess.run(  # noqa: S603 - controlled plugin and selected test in a bounded child.
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "hypothesis.extra.pytestplugin",
            "-p",
            "delayed_contract_validator",
            "tests/test_quality_tools.py::test_schemathesis_generated_requests_satisfy_local_contract",
            f"--basetemp={tmp_path / 'child-test-tmp'}",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("source", "expected_exit"),
    [
        ("def keep() -> int:\n    result = 1\n    return result\nkeep()\n", 0),
        ("def keep(discarded: int) -> int:\n    return 2\nkeep(1)\n", 3),
    ],
)
def test_scaffold_vulture_configuration_detects_unused_code(
    tmp_path: Path, source: str, expected_exit: int
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    (tmp_path / "src/example/__init__.py").write_text(source, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "vulture"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert ("unused variable 'discarded'" in result.stdout) is (expected_exit == 3)


@pytest.mark.parametrize(("depth", "expected_exit"), [(5, 0), (6, 1)])
def test_complexipy_enforces_the_inclusive_cognitive_limit(
    tmp_path: Path, depth: int, expected_exit: int
) -> None:
    initialize(tmp_path, "example", "example", "library", ("github",), True)
    source = "def decision(value: int) -> bool:\n"
    source += "".join("    " * (level + 1) + "if value > 0:\n" for level in range(depth))
    source += "    " * (depth + 1) + "return True\n    return False\n"
    (tmp_path / "src/example/__init__.py").write_text(source, encoding="utf-8")

    result = subprocess.run(  # noqa: S603 - fixed installed engine and bounded local fixture.
        [str(Path(sys.executable).with_name("complexipy"))],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    # Five nested decisions score 1+2+3+4+5 = 15; six score 21.
    assert result.returncode == expected_exit, result.stdout + result.stderr


@pytest.mark.parametrize("kind", ["library", "service", "cli", "research"])
def test_scaffold_wires_vulture_and_keeps_api_checks_explicit(tmp_path: Path, kind: str) -> None:
    initialize(tmp_path, "example", "example", kind, ("github", "gitlab"), True)
    metadata = tomllib.loads((tmp_path / "pyproject.toml").read_text())
    spec = load(tmp_path)

    assert "vulture==2.16" in metadata["dependency-groups"]["harness"]
    assert metadata["dependency-groups"]["api"] == ["schemathesis==4.32.5"]
    assert metadata["tool"]["vulture"] == {"paths": ["src", "tests"], "min_confidence": 80}
    assert "complexipy==8.2.0" in metadata["dependency-groups"]["harness"]
    assert metadata["tool"]["complexipy"]["max-complexity-allowed"] == 15
    assert metadata["tool"]["complexipy"]["no-ignore"] is True
    cognitive = next(item for item in spec.checks if item.id == "cognitive-complexity")
    assert cognitive.group == "static"
    assert cognitive.argv == ("uv", "run", "--locked", "--group", "harness", "complexipy")
    dead_code = next(item for item in spec.checks if item.id == "dead-code")
    assert dead_code.group == "static"
    assert dead_code.argv == ("uv", "run", "--locked", "--group", "harness", "vulture")
    assert all(item.group != "deep" for item in spec.checks)

    example = (tmp_path / ".harness/api-check.example.toml").read_text()
    policy = tmp_path / ".harness/project.toml"
    policy.write_text(policy.read_text() + example, encoding="utf-8")
    api_check = next(item for item in load(tmp_path).checks if item.id == "api-contract")

    assert api_check.group == "deep"
    assert api_check.timeout == 120
    assert api_check.argv == (
        "uv",
        "run",
        "--locked",
        "--group",
        "harness",
        "--group",
        "api",
        "schemathesis",
        "run",
        "openapi.yaml",
        "--url",
        "http://127.0.0.1:8000",
        "--workers",
        "1",
        "--phases",
        "examples,fuzzing",
        "--max-examples",
        "25",
        "--max-failures",
        "1",
        "--request-timeout",
        "5",
        "--generation-deterministic",
        "--generation-database",
        "none",
    )

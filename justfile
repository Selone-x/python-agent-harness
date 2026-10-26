set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

setup:
    uv sync --locked
    uv run --locked pre-commit install

fmt:
    uv run --locked ruff check --fix .
    uv run --locked ruff format .

check:
    uv run --locked ruff format --check .
    uv run --locked ruff check .
    uv run --locked ty check
    uv run --locked harness validate
    uv run --locked harness render --check
    uv run --locked harness audit
    uv run --locked pytest --basetemp=.reports/test-tmp -o tmp_path_retention_policy=failed -o tmp_path_retention_count=1
    uv run --locked harness coverage
    uv build --no-sources
    uv run --locked harness package --module python_agent_harness

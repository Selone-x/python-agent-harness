set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

setup:
    uv sync --locked
    uv run --locked pre-commit install

fmt:
    uv run --locked ruff check --fix .
    uv run --locked ruff format .

dead-code:
    uv run --locked vulture

complexity:
    uv run --locked complexipy

check:
    uv run --locked harness validate
    uv run --locked harness check
    uv run --locked harness gate

deep:
    uv run --locked harness check --group deep

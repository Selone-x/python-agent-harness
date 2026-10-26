"""Portable CI templates and read-only, capability-aware repository diagnosis."""

import json
import subprocess
from pathlib import Path

from .model import Finding, Spec
from .paths import HarnessError


def github_workflow(spec: Spec) -> str:
    """Use an always-running aggregate gate; do not treat skipped needs as success."""
    groups = sorted({item.group for item in spec.checks} - {"deep"})
    return f"""name: Harness
on:
  pull_request:
  push:
    branches: [main]
  merge_group:
  workflow_dispatch:
permissions:
  contents: read
env:
  HYPOTHESIS_PROFILE: ci
  UV_CACHE_DIR: ${{{{ github.workspace }}}}/.uv-cache
jobs:
  checks:
    name: harness-${{{{ matrix.group }}}}
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      max-parallel: 1
      matrix:
        group: {json.dumps(groups)}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: {json.dumps(spec.python)}
      - run: python -m pip install uv==0.13.1
      - run: python -I .harness/runner.pyz setup
      - run: python -I .harness/runner.pyz check --group ${{{{ matrix.group }}}}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: harness-${{{{ matrix.group }}}}
          path: .harness/reports/
          include-hidden-files: true
          retention-days: 7
  gate:
    name: harness-gate
    if: ${{{{ always() }}}}
    needs: [checks]
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: {json.dumps(spec.python)}
      - uses: actions/download-artifact@v4
        with:
          pattern: harness-*
          path: .harness/reports/
          merge-multiple: true
      - run: python -I .harness/runner.pyz gate
"""


def gitlab_workflow(spec: Spec) -> str:
    """Reserved stages compose with existing pipelines without replacing their jobs."""
    groups = sorted({item.group for item in spec.checks} - {"deep"})
    jobs = []
    for group in groups:
        jobs.append(f"""harness-{group}:
  stage: .pre
  image: python:{spec.python}-bookworm
  variables:
    HYPOTHESIS_PROFILE: ci
    UV_CACHE_DIR: $CI_PROJECT_DIR/.uv-cache
  timeout: 30m
  interruptible: true
  resource_group: harness-$CI_PROJECT_ID
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - if: '$CI_PIPELINE_SOURCE == "web"'
  allow_failure: false
  script:
    - python -m pip install uv==0.13.1
    - python -I .harness/runner.pyz setup
    - python -I .harness/runner.pyz check --group {group}
  artifacts:
    when: always
    expire_in: 7 days
    paths: [.harness/reports/]
""")
    needs = "\n".join(f"    - job: harness-{group}\n      artifacts: true" for group in groups)
    jobs.append(f"""harness-gate:
  stage: .post
  image: python:{spec.python}-bookworm
  when: always
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: always
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: always
    - if: '$CI_PIPELINE_SOURCE == "web"'
      when: always
  allow_failure: false
  needs:
{needs}
  script:
    - python -I .harness/runner.pyz gate
""")
    return "\n".join(jobs)


def api(root: Path, provider: str, endpoint: str) -> object:
    """Use the user's authenticated CLI; never persist or print credentials."""
    executable = "gh" if provider == "github" else "glab"
    try:
        result = subprocess.run(  # noqa: S603 - fixed CLI plus a validated read-only endpoint.
            [executable, "api", endpoint],
            cwd=root,
            capture_output=True,
            timeout=30,
            check=False,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HarnessError(f"Cannot query {provider}: {type(error).__name__}") from error
    if result.returncode:
        raise HarnessError(
            f"{provider} settings unavailable; verify CLI authentication and read permissions"
        )
    return json.loads(result.stdout)


def github_findings(data: object) -> tuple[Finding, ...]:
    """Required approvals and an unbypassed aggregate check protect policy changes."""
    if not isinstance(data, dict):
        raise HarnessError("Invalid GitHub protection response")
    checks = data.get("required_status_checks") or {}
    reviews = data.get("required_pull_request_reviews") or {}
    names = set(checks.get("contexts", [])) | {item["context"] for item in checks.get("checks", [])}
    conditions = {
        "ci.required": "harness-gate" in names and checks.get("strict") is True,
        "policy.review": reviews.get("require_code_owner_reviews") is True
        and reviews.get("required_approving_review_count", 0) >= 1
        and reviews.get("dismiss_stale_reviews") is True,
        "branch.admins": (data.get("enforce_admins") or {}).get("enabled") is True,
        "branch.force_push": (data.get("allow_force_pushes") or {}).get("enabled") is False,
        "policy.last_push": reviews.get("require_last_push_approval") is True,
        "policy.no_bypass": "bypass_pull_request_allowances" in reviews
        and not any((reviews.get("bypass_pull_request_allowances") or {}).values()),
    }
    return tuple(
        Finding(
            code=name,
            status="pass" if value else "blocked",
            message="Configured" if value else "Missing or not verified",
        )
        for name, value in conditions.items()
    )


def gitlab_findings(project: object, branches: object, approvals: object) -> tuple[Finding, ...]:
    """Inspect every matching protected branch rule; permissive wildcards matter."""
    if not isinstance(project, dict) or not isinstance(branches, list):
        raise HarnessError("Invalid GitLab settings response")
    import fnmatch

    matches = [
        item for item in branches if fnmatch.fnmatchcase(project["default_branch"], item["name"])
    ]
    no_push = bool(matches) and all(
        item.get("allow_force_push") is False
        and item.get("push_access_levels")
        and all(
            level.get("access_level") == 0
            and not any(level.get(key) for key in ("user_id", "group_id", "deploy_key_id"))
            for level in item["push_access_levels"]
        )
        for item in matches
    )
    review = (
        isinstance(approvals, dict)
        and approvals.get("approvals_before_merge", 0) >= 1
        and approvals.get("disable_overriding_approvers_per_merge_request") is True
        and approvals.get("reset_approvals_on_push") is True
    )
    conditions = {
        "ci.required": project.get("only_allow_merge_if_pipeline_succeeds") is True
        and project.get("allow_merge_on_skipped_pipeline") is False,
        "branch.no_push": no_push,
        "policy.review": review,
    }
    return tuple(
        Finding(
            code=name,
            status="pass" if value else "blocked",
            message="Configured"
            if value
            else "Missing/unverified; required approvals may require GitLab Premium/Ultimate",
        )
        for name, value in conditions.items()
    )


def doctor(root: Path, provider: str, repository: str) -> tuple[Finding, ...]:
    """Read settings only; setup instructions are separate from an applied guarantee."""
    if (
        not repository
        or repository.startswith("/")
        or ".." in repository
        or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/"
            for char in repository
        )
    ):
        raise HarnessError("Invalid repository identifier")
    if provider == "github":
        data = api(root, provider, f"repos/{repository}")
        if not isinstance(data, dict):
            raise HarnessError("Invalid repository metadata")
        return github_findings(
            api(root, provider, f"repos/{repository}/branches/{data['default_branch']}/protection")
        )
    encoded = repository.replace("/", "%2F")
    project = api(root, provider, f"projects/{encoded}")
    branches = api(root, provider, f"projects/{encoded}/protected_branches?per_page=100")
    if isinstance(branches, list) and len(branches) >= 100:
        raise HarnessError("Protection has more pages; complete pagination is unverified")
    try:
        approvals = api(root, provider, f"projects/{encoded}/approvals")
    except HarnessError:
        approvals = None
    return gitlab_findings(project, branches, approvals)

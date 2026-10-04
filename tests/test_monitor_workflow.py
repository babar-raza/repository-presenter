"""Structure of ``.github/workflows/monitor.yml`` (G7-W06).

Hosted YAML cannot run offline, so these tests parse the file and pin which failures the scheduled
run may absorb. Only the token mint of an owner may fail without failing the run; a real
observation error must still turn the run red, and no step may hold a write permission.
"""

from __future__ import annotations

from typing import Any

import yaml

from support import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "monitor.yml"
MINT_PREFIX = "Mint a read-only installation token"
RECORD_PREFIX = "Record this owner's installation state"
OBSERVE_PREFIX = "Observe each enabled repository"


def _workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _steps(job: str) -> list[dict[str, Any]]:
    steps = _workflow()["jobs"][job]["steps"]
    assert isinstance(steps, list)
    return steps


def _step(job: str, prefix: str) -> dict[str, Any]:
    matches = [step for step in _steps(job) if str(step.get("name", "")).startswith(prefix)]
    assert len(matches) == 1, f"expected one step starting {prefix!r} in {job}"
    return matches[0]


def test_the_scheduled_trigger_and_read_only_grant_are_unchanged() -> None:
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))

    assert triggers["schedule"] == [{"cron": "17 */6 * * *"}]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    requested = [
        value
        for body in workflow["jobs"].values()
        for step in body["steps"]
        for key, value in step.get("with", {}).items()
        if key.startswith("permission-")
    ]
    assert requested and set(requested) == {"read"}


def test_only_the_token_mint_may_fail_without_failing_the_run() -> None:
    # Negative control: a continue-on-error anywhere else would let a real observation error pass.
    absorbing = [
        (job, step.get("name"))
        for job, body in _workflow()["jobs"].items()
        for step in body["steps"]
        if step.get("continue-on-error")
    ]

    assert absorbing == [("drift", _step("drift", MINT_PREFIX)["name"])]


def test_a_missing_installation_is_recorded_as_a_notice_not_a_failure() -> None:
    mint = _step("drift", MINT_PREFIX)
    record = _step("drift", RECORD_PREFIX)

    assert mint["id"] == "app-token"
    assert mint["continue-on-error"] is True
    assert record["if"] == "always()"
    assert record["env"]["MINT_OUTCOME"] == "${{ steps.app-token.outcome }}"
    assert "monitor-install-record" in record["run"]


def test_observation_runs_only_with_a_minted_token_and_its_errors_still_fail_the_leg() -> None:
    observe = _step("drift", OBSERVE_PREFIX)

    assert observe["if"] == "steps.app-token.outcome == 'success'"
    assert "continue-on-error" not in observe
    assert observe["env"]["GH_TOKEN"] == "${{ steps.app-token.outputs.token }}"
    assert "repository-presenter monitor --owner" in observe["run"]


def test_the_evidence_artifact_still_uploads_even_for_an_uninstalled_owner() -> None:
    upload = next(
        step for step in _steps("drift") if str(step.get("uses", "")).startswith("actions/upload")
    )

    assert upload["if"] == "always()"
    assert upload["with"]["path"] == "runs/monitor/"


def test_the_coverage_job_is_red_only_when_no_owner_is_observable() -> None:
    coverage = _workflow()["jobs"]["coverage"]
    summarize = [s for s in coverage["steps"] if "monitor-install-summary" in s.get("run", "")]

    assert "drift" in coverage["needs"]
    assert coverage["if"] == "always()"
    assert "continue-on-error" not in str(coverage)
    assert len(summarize) == 1
    assert "--summary" in summarize[0]["run"]

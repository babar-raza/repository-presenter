"""The unattended sealing workflow's structure, parsed from the YAML itself (hosted YAML cannot run
offline; tests/test_workflow_app_tokens.py takes the same approach).

What these pin: the scheduled job reuses present.yml and propose.yml through workflow_call rather
than copying them; the proposal leg is gated on the owner variable and nothing else; one
repository's failed seal cannot stop the others; no job mints an App token of its own; and no model
other than qwen3-next is ever configured.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from support import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SCHEDULED = WORKFLOWS / "sealing-scheduled.yml"
WRITE_GATE = "vars.REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED == '1'"


def _load(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path.name} is not a YAML mapping"
    return loaded


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML reads the bare key `on` as the boolean True (YAML 1.1); GitHub reads it as `on`.
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict), "workflow has no trigger mapping"
    return triggers


@pytest.fixture(scope="module")
def scheduled() -> dict[str, Any]:
    return _load(SCHEDULED)


def test_the_scheduled_workflow_parses_and_is_triggered_by_schedule_and_dispatch(
    scheduled: dict[str, Any],
) -> None:
    triggers = _triggers(scheduled)
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] and triggers["schedule"][0]["cron"]
    assert "repository_dispatch" not in triggers


def test_every_job_defaults_to_read_only_and_only_the_seal_job_asks_for_contents_write(
    scheduled: dict[str, Any],
) -> None:
    assert scheduled["permissions"] == {"contents": "read"}
    jobs = scheduled["jobs"]
    assert set(jobs) == {"plan", "seal", "propose"}
    assert jobs["plan"].get("permissions") is None
    assert jobs["seal"]["permissions"] == {"contents": "write"}
    assert jobs["propose"]["permissions"] == {"contents": "read"}


def test_seal_and_propose_reuse_the_existing_workflows_through_workflow_call(
    scheduled: dict[str, Any],
) -> None:
    jobs = scheduled["jobs"]
    assert jobs["seal"]["uses"] == "./.github/workflows/present.yml"
    assert jobs["propose"]["uses"] == "./.github/workflows/propose.yml"
    # No job runs steps of its own beyond the planner: the pipelines are never copied here.
    assert "steps" not in jobs["seal"] and "steps" not in jobs["propose"]


def test_plan_is_the_only_job_with_a_checkout_and_it_runs_the_cli_planner(
    scheduled: dict[str, Any],
) -> None:
    plan_steps = scheduled["jobs"]["plan"]["steps"]
    commands = [step.get("run", "") for step in plan_steps]
    assert any("repository-presenter sealing-plan --drift-file" in c for c in commands)
    plan_run = next(step for step in plan_steps if step.get("id") == "plan")
    assert plan_run["run"].count("sealing-plan") == 1


def test_the_seal_matrix_runs_one_repository_at_a_time_without_stopping_on_a_failure(
    scheduled: dict[str, Any],
) -> None:
    seal = scheduled["jobs"]["seal"]
    assert seal["strategy"]["fail-fast"] is False
    assert seal["strategy"]["max-parallel"] == 1
    assert (
        seal["strategy"]["matrix"]["target"] == "${{ fromJSON(needs.plan.outputs.repositories) }}"
    )
    assert seal["with"] == {"repository": "${{ matrix.target.repository }}"}
    assert seal["needs"] == "plan"


def test_one_failed_seal_cannot_skip_the_other_repositories_proposals(
    scheduled: dict[str, Any],
) -> None:
    propose = scheduled["jobs"]["propose"]
    assert propose["needs"] == ["plan", "seal"]
    assert propose["if"].startswith("${{ !cancelled() &&")
    assert propose["strategy"]["fail-fast"] is False
    assert propose["strategy"]["max-parallel"] == 1


def test_the_proposal_job_is_gated_on_the_owner_variable_and_only_it(
    scheduled: dict[str, Any],
) -> None:
    condition = scheduled["jobs"]["propose"]["if"]
    assert WRITE_GATE in condition
    # Presence of a credential never opens the gate (AGENTS.md "Security and Effects").
    assert "secrets." not in condition
    assert "GH_PROPOSAL_WRITE_TOKEN" not in condition


def test_the_proposal_job_is_skipped_without_publishable_work_and_only_proposes_full_mode(
    scheduled: dict[str, Any],
) -> None:
    propose = scheduled["jobs"]["propose"]
    assert "has_publishable == 'true'" in propose["if"]
    assert propose["strategy"]["matrix"]["target"] == (
        "${{ fromJSON(needs.plan.outputs.publishable) }}"
    )


def test_the_proposal_call_proposes_only_the_bundle_this_run_exported(
    scheduled: dict[str, Any],
) -> None:
    call = scheduled["jobs"]["propose"]["with"]
    assert call["do_propose"] is True
    assert call["candidate_artifact"] == "sealed-${{ matrix.target.slug }}"
    assert call["repo"] == "${{ matrix.target.repository }}"


def test_no_model_other_than_qwen3_next_is_ever_configured_here(
    scheduled: dict[str, Any],
) -> None:
    # Executable lines only: the header comment may name GPT_OSS_MODEL in order to refuse it.
    code = "\n".join(
        line
        for line in SCHEDULED.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "GPT_OSS_MODEL" not in code
    assert "--model" not in code
    assert not re.search(r"\bmodel\b", code, flags=re.IGNORECASE), "no model may be set here"


def test_no_job_in_the_scheduled_workflow_mints_an_app_token(scheduled: dict[str, Any]) -> None:
    assert "actions/create-github-app-token" not in SCHEDULED.read_text(encoding="utf-8")
    assert "GH_PROPOSAL_WRITE_TOKEN" not in SCHEDULED.read_text(encoding="utf-8")


def test_present_is_callable_per_repository_and_exports_only_a_ready_bundle() -> None:
    present = _load(WORKFLOWS / "present.yml")
    triggers = _triggers(present)
    assert set(triggers) >= {"workflow_dispatch", "repository_dispatch", "workflow_call"}
    assert triggers["workflow_call"]["inputs"]["repository"]["required"] is True
    assert "schedule" not in triggers
    text = (WORKFLOWS / "present.yml").read_text(encoding="utf-8")
    assert "sealed-ready --repo" in text
    export = next(s for s in present["jobs"]["present"]["steps"] if s.get("id") == "export")
    assert "sealed-ready" in export["run"]
    upload = next(
        s
        for s in present["jobs"]["present"]["steps"]
        if s.get("name") == "Upload the sealed bundle"
    )
    assert upload["if"] == "${{ steps.export.outputs.exported == 'true' }}"


def test_present_resolves_the_target_from_the_call_input_for_every_non_dispatch_event() -> None:
    text = (WORKFLOWS / "present.yml").read_text(encoding="utf-8")
    assert '"${{ github.event_name }}" = "repository_dispatch"' in text
    assert 'repository="${{ inputs.repository }}"' in text


def test_propose_is_callable_and_its_real_write_stays_gated_on_do_propose() -> None:
    propose = _load(WORKFLOWS / "propose.yml")
    triggers = _triggers(propose)
    assert set(triggers) == {"workflow_call", "workflow_dispatch"}
    call_inputs = triggers["workflow_call"]["inputs"]
    assert {"repo", "do_propose", "candidate_artifact"} <= set(call_inputs)
    steps = propose["jobs"]["propose"]["steps"]
    real = next(s for s in steps if str(s.get("name", "")).startswith("Propose for real"))
    gate = "inputs.candidate_artifact == '' || steps.ready.outputs.ready == 'true'"
    assert real["if"] == f"${{{{ inputs.do_propose && ({gate}) }}}}"
    assert real["env"]["REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"] == "1"
    # The authorization is set only in the one real-write step, never at job or workflow level.
    assert "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED" not in propose.get("env", {})
    assert "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED" not in propose["jobs"]["propose"].get(
        "env", {}
    )


def test_propose_imports_only_a_bundle_this_run_sealed_and_proposes_nothing_otherwise() -> None:
    propose = _load(WORKFLOWS / "propose.yml")
    steps = propose["jobs"]["propose"]["steps"]
    by_id = {s["id"]: s for s in steps if "id" in s}
    assert by_id["import"]["continue-on-error"] is True
    assert "candidate_artifact" in by_id["import"]["if"]
    ready = by_id["ready"]
    assert "sealed-ready" in ready["run"] and "exit 0" in ready["run"]
    mint = by_id["app-token"]
    assert (
        mint["if"]
        == "${{ inputs.candidate_artifact == '' || steps.ready.outputs.ready == 'true' }}"
    )
    dry = next(s for s in steps if str(s.get("name", "")).startswith("Dry run"))
    assert (
        dry["if"] == "${{ inputs.candidate_artifact == '' || steps.ready.outputs.ready == 'true' }}"
    )


def test_the_drift_contract_is_consumed_through_its_file_path_alone(
    scheduled: dict[str, Any],
) -> None:
    plan_run = next(s for s in scheduled["jobs"]["plan"]["steps"] if s.get("id") == "plan")
    assert "--drift-file drift/drift.json" in plan_run["run"]
    assert "uses" not in plan_run

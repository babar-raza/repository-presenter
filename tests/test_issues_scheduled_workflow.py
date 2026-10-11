"""The unattended upstream-issue workflow (``.github/workflows/issues-scheduled.yml``).

Hosted YAML cannot run offline, so these tests parse the file and pin the properties AGENTS.md
"Security and Effects" makes non-negotiable for it: a read-only analysis path that never holds the
write credential; a write path that runs only when the owner's repository variable is set to
``1``; a write token minted per target repository with the issues permission alone; and no
ambient write credential anywhere else.
"""

from __future__ import annotations

from typing import Any

import yaml

from support import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "issues-scheduled.yml"
GATE_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"
WRITE_TOKEN = "GH_ISSUES_WRITE_TOKEN"
MINT = "actions/create-github-app-token@"
MIRROR = "${{ vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED }}"
HAS_APPROVAL = "${{ steps.approvals.outputs.count != '0' }}"


def _workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _jobs() -> dict[str, dict[str, Any]]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return steps


def _text(value: object) -> str:
    return yaml.safe_dump(value, sort_keys=True)


def test_the_workflow_is_scheduled_and_manually_dispatchable() -> None:
    # PyYAML (YAML 1.1) parses the bare `on:` key as the boolean True.
    loaded = _workflow()
    triggers = loaded["on"] if "on" in loaded else loaded[True]
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers


def test_the_top_level_grant_is_read_only() -> None:
    assert _workflow()["permissions"] == {"contents": "read"}


def test_no_job_widens_the_top_level_grant() -> None:
    for name, job in _jobs().items():
        assert "permissions" not in job or job["permissions"] == {"contents": "read"}, name


def test_the_write_path_is_gated_on_the_owner_repository_variable() -> None:
    write_jobs = [
        name for name, job in _jobs().items() if WRITE_TOKEN in _text(job.get("steps", []))
    ]
    assert write_jobs, "the workflow must contain a write job"
    for name in write_jobs:
        condition = str(_jobs()[name].get("if", ""))
        assert "vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED == '1'" in condition, name


def test_the_write_token_appears_in_no_read_only_job() -> None:
    for name, job in _jobs().items():
        if "vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED" in str(job.get("if", "")):
            continue
        assert WRITE_TOKEN not in _text(job), name
        for step in _steps(job):
            # The read-only analysis may mirror the kill switch's value so its report can say
            # whether the write job would run; it can never set it to a literal.
            assert (step.get("env") or {}).get(GATE_VARIABLE, MIRROR) == MIRROR, name


def test_the_gate_is_set_as_a_literal_only_on_the_step_that_writes() -> None:
    for name, job in _jobs().items():
        for step in _steps(job):
            env = step.get("env") or {}
            if GATE_VARIABLE in env and WRITE_TOKEN in env:
                assert env[GATE_VARIABLE] == "1", f"{name}: gate must be the literal 1"
            elif GATE_VARIABLE in env:
                assert env[GATE_VARIABLE] == MIRROR, f"{name}: no write token, no literal gate"


def test_every_mint_step_is_scoped_to_its_one_target_repository() -> None:
    for name, job in _jobs().items():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith(MINT):
                assert step["with"]["repositories"] == "${{ matrix.target.name }}", name
                assert step["with"]["owner"] == "${{ matrix.target.owner }}", name


def test_the_write_token_requests_issues_write_and_no_other_write_scope() -> None:
    mints = [
        step["with"]
        for step in _steps(_jobs()["file-and-close"])
        if str(step.get("uses", "")).startswith(MINT)
    ]
    write_grants = [{k: v for k, v in grant.items() if str(v) == "write"} for grant in mints]
    assert {"permission-issues": "write"} in write_grants
    assert [w for w in write_grants if w] == [{"permission-issues": "write"}]


def test_the_analysis_path_never_requests_write_scope() -> None:
    for step in _steps(_jobs()["analyse"]):
        if str(step.get("uses", "")).startswith(MINT):
            assert "write" not in {str(v) for v in step["with"].values()}


def test_the_write_job_does_not_wait_on_analysis_so_one_failure_cannot_stop_the_others() -> None:
    needs = _jobs()["file-and-close"]["needs"]
    needs_list = [needs] if isinstance(needs, str) else list(needs)
    assert "analyse" not in needs_list


def test_the_fan_out_is_a_matrix_over_targets_computed_by_the_official_entry_point() -> None:
    targets_text = _text(_jobs()["targets"])
    assert "repository-presenter issue-targets" in targets_text
    for name in ("analyse", "file-and-close"):
        assert _jobs()[name]["strategy"]["fail-fast"] is False, name
        assert "fromJSON(needs.targets.outputs.matrix)" in str(
            _jobs()[name]["strategy"]["matrix"]["target"]
        ), name


def test_the_write_steps_run_the_gated_official_entry_point() -> None:
    commands = [str(step.get("run", "")) for step in _steps(_jobs()["file-and-close"])]
    assert any("file-upstream-defects" in c and "--file" in c for c in commands)
    assert any("redetect-upstream-defects" in c and "--close" in c for c in commands)


def test_the_analysis_path_runs_only_dry_run_forms_of_the_entry_point() -> None:
    commands = [str(step.get("run", "")) for step in _steps(_jobs()["analyse"])]
    assert any("file-upstream-defects" in c for c in commands)
    assert all("--file" not in c and "--close" not in c and "--apply" not in c for c in commands)


# ---------------------------------------------------------------------------
# Per-handoff owner approval: the variable is a kill switch, never an authorization
# ---------------------------------------------------------------------------


def test_the_write_job_counts_approved_handoffs_before_it_mints_anything() -> None:
    steps = _steps(_jobs()["file-and-close"])
    counting = [i for i, st in enumerate(steps) if st.get("id") == "approvals"]
    minting = [i for i, st in enumerate(steps) if str(st.get("uses", "")).startswith(MINT)]
    assert len(counting) == 1
    assert minting and all(counting[0] < i for i in minting)
    run = str(steps[counting[0]]["run"])
    assert "file-upstream-defects" in run and "--count-writable" in run
    assert "--approvals-ref" in run and '--repo "$REPO"' in run


def test_every_mint_and_every_write_step_requires_a_counted_approval() -> None:
    for step in _steps(_jobs()["file-and-close"]):
        text = _text(step)
        is_mint = str(step.get("uses", "")).startswith(MINT)
        if is_mint or WRITE_TOKEN in text:
            assert step.get("if") == HAS_APPROVAL, step.get("name")


def test_the_filing_step_is_bound_to_one_target_and_reads_approvals_from_the_trigger() -> None:
    filing = [
        str(st["run"])
        for st in _steps(_jobs()["file-and-close"])
        if "file-upstream-defects" in str(st.get("run", "")) and "--file" in str(st.get("run", ""))
    ]
    assert len(filing) == 1
    assert '--repo "$REPO"' in filing[0]
    assert '--approvals-ref "$APPROVALS_REF"' in filing[0]
    for step in _steps(_jobs()["file-and-close"]):
        if "APPROVALS_REF" in (step.get("env") or {}):
            assert step["env"]["APPROVALS_REF"] == "${{ github.sha }}"


def test_approval_readers_check_out_full_history_without_persisting_credentials() -> None:
    for name in ("analyse", "file-and-close"):
        checkout = next(
            st
            for st in _steps(_jobs()[name])
            if str(st.get("uses", "")).startswith("actions/checkout@")
        )
        assert checkout["with"]["fetch-depth"] == 0, name
        assert checkout["with"]["persist-credentials"] is False, name


def test_no_job_can_commit_an_approval_record() -> None:
    """A run must not be able to create the approval it would consume: no write grant on
    contents, no persisted checkout credential, and no step that commits or pushes."""
    for name, job in _jobs().items():
        assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}, name
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False, name
            if str(step.get("uses", "")).startswith(MINT):
                assert "permission-contents" not in step["with"] or (
                    step["with"]["permission-contents"] == "read"
                ), name
            run = str(step.get("run", ""))
            for forbidden in ("git commit", "git push", "ops/issue_approvals", "git add"):
                assert forbidden not in run, (name, forbidden)


# ---------------------------------------------------------------------------
# Closing an upstream issue is a write: its own approval, read from the trigger commit
# ---------------------------------------------------------------------------


def test_the_close_step_is_bound_to_one_target_and_reads_close_approvals_from_the_trigger() -> None:
    closing = [
        st
        for st in _steps(_jobs()["file-and-close"])
        if "redetect-upstream-defects" in str(st.get("run", "")) and "--close" in str(st["run"])
    ]
    assert len(closing) == 1
    step = closing[0]
    assert '--repo "$REPO"' in str(step["run"])
    assert '--approvals-ref "$APPROVALS_REF"' in str(step["run"])
    assert step["env"]["APPROVALS_REF"] == "${{ github.sha }}"
    assert step.get("if") == HAS_APPROVAL
    assert step["env"][GATE_VARIABLE] == "1"
    assert WRITE_TOKEN in step["env"]


def test_the_dry_run_redetection_reads_close_approvals_from_the_trigger_too() -> None:
    dry = [
        str(st["run"])
        for st in _steps(_jobs()["analyse"])
        if "redetect-upstream-defects" in str(st.get("run", ""))
    ]
    assert len(dry) == 1
    assert '--approvals-ref "$APPROVALS_REF"' in dry[0]
    assert "--close" not in dry[0]


def test_the_header_names_json_approval_records_and_the_issues_mode_gate() -> None:
    header = "\n".join(
        line for line in WORKFLOW.read_text(encoding="utf-8").splitlines() if line.startswith("#")
    )
    assert "ops/issue_approvals/<handoff-id>.json" in header
    assert ".yaml" not in header
    assert "issues_mode" in header


# ---------------------------------------------------------------------------
# TC-ISS-09/11: the batch is bounded and paced in the workflow itself, not only by CLI defaults
# ---------------------------------------------------------------------------


def test_the_filing_step_states_its_per_repository_caps_and_pacing_explicitly() -> None:
    filing = next(
        str(st["run"])
        for st in _steps(_jobs()["file-and-close"])
        if "file-upstream-defects" in str(st.get("run", "")) and "--file" in str(st.get("run", ""))
    )
    for flag in ("--daily-cap", "--open-cap", "--pace-seconds"):
        assert flag in filing, f"the filing step must state {flag} so a reviewer sees the bound"
    tokens = filing.split()
    daily = int(tokens[tokens.index("--daily-cap") + 1])
    opened = int(tokens[tokens.index("--open-cap") + 1])
    assert 1 <= daily <= opened


# ---------------------------------------------------------------------------
# TC-ISS-10: the lifecycle in the workflow - update comments are owner-enabled and gated like a
# filing; the read-only analysis publishes the resume contract for the sealing plan.
# ---------------------------------------------------------------------------

COMMENTS_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED"
COMMENTS_MIRROR = "${{ vars.REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED }}"


def test_the_update_step_is_gated_by_a_counted_approval_and_the_owners_comment_switch() -> None:
    steps = [
        st for st in _steps(_jobs()["file-and-close"]) if "--comment" in str(st.get("run", ""))
    ]
    assert len(steps) == 1
    step = steps[0]
    assert step.get("if") == HAS_APPROVAL
    assert '--repo "$REPO"' in str(step["run"]) and "redetect-upstream-defects" in str(step["run"])
    env = step["env"]
    assert env[GATE_VARIABLE] == "1" and WRITE_TOKEN in env
    # The comments switch is only ever mirrored from the owner's variable, never a literal.
    assert env[COMMENTS_VARIABLE] == COMMENTS_MIRROR


def test_the_comments_switch_is_never_a_literal_anywhere() -> None:
    for name, job in _jobs().items():
        for step in _steps(job):
            value = (step.get("env") or {}).get(COMMENTS_VARIABLE, COMMENTS_MIRROR)
            assert value == COMMENTS_MIRROR, name


def test_the_approval_count_includes_filed_issues_only_while_comments_are_enabled() -> None:
    counting = next(st for st in _steps(_jobs()["file-and-close"]) if st.get("id") == "approvals")
    assert counting["env"][COMMENTS_VARIABLE] == COMMENTS_MIRROR
    run = str(counting["run"])
    assert "--with-updates" in run and COMMENTS_VARIABLE in run


def test_the_analysis_publishes_the_resume_contract_without_any_write() -> None:
    steps = _steps(_jobs()["analyse"])
    producing = [st for st in steps if "--resume-out" in str(st.get("run", ""))]
    assert len(producing) == 1
    assert "--close" not in str(producing[0]["run"]) and "--comment" not in str(producing[0]["run"])
    uploads = [st for st in steps if "resume" in str((st.get("with") or {}).get("path", ""))]
    assert uploads, "the resume contract must be kept as a run artifact"


# ---------------------------------------------------------------------------
# TC-ISS-11: the funnel and the age alert are visible every cycle, with no credential at all
# ---------------------------------------------------------------------------


def test_the_targets_job_reports_the_funnel_and_aged_handoffs_with_full_history() -> None:
    job = _jobs()["targets"]
    checkout = next(
        st for st in _steps(job) if str(st.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout["with"]["fetch-depth"] == 0  # a handoff's age is when git first saw it
    assert checkout["with"]["persist-credentials"] is False
    funnel = [st for st in _steps(job) if "issue-funnel" in str(st.get("run", ""))]
    assert len(funnel) == 1
    assert "--max-pending-days" in str(funnel[0]["run"])
    assert WRITE_TOKEN not in _text(job) and "GH_TOKEN" not in _text(job)

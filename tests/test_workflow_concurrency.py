"""Each hosted workflow that can spend provider calls or write durable state declares a concurrency
group with the right cancel setting, parsed from the YAML itself (hosted YAML cannot run offline;
tests/test_sealing_workflow.py takes the same approach).

What these pin: monitor.yml is one read-only group that a newer run may cancel; present.yml is one
group per target repository that is never cancelled mid-transaction; sealing-scheduled.yml's seal
job is one group per target repository, never cancelled, and its group names never equal the
reusable present.yml's own, so the nested call cannot wait on its caller.
"""

from __future__ import annotations

from typing import Any

import yaml

from support import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{name} is not a YAML mapping"
    return loaded


def test_monitor_is_one_read_only_group_that_a_newer_run_may_cancel() -> None:
    assert _load("monitor.yml")["concurrency"] == {"group": "monitor", "cancel-in-progress": True}


def test_present_is_one_group_per_target_repository_and_never_cancelled_mid_transaction() -> None:
    concurrency = _load("present.yml")["concurrency"]
    assert concurrency["cancel-in-progress"] is False
    group = str(concurrency["group"])
    assert group.startswith("present-")
    # Keyed to the target from every trigger: dispatch and workflow_call name it as an input,
    # repository_dispatch carries it in the client payload.
    assert "inputs.repository" in group
    assert "github.event.client_payload.repository" in group
    assert "matrix" not in group


def test_the_seal_job_is_one_group_per_target_and_never_cancelled() -> None:
    seal = _load("sealing-scheduled.yml")["jobs"]["seal"]
    assert seal["concurrency"] == {
        "group": "seal-${{ matrix.target.repository }}",
        "cancel-in-progress": False,
    }


def test_the_plan_job_is_not_grouped_because_it_spends_no_provider_calls() -> None:
    assert "concurrency" not in _load("sealing-scheduled.yml")["jobs"]["plan"]


def test_the_seal_group_cannot_collide_with_the_reusable_present_group() -> None:
    # A caller and its called workflow sharing one group would make the called run wait forever
    # for the caller that is waiting on it.
    seal_group = _load("sealing-scheduled.yml")["jobs"]["seal"]["concurrency"]["group"]
    present_group = str(_load("present.yml")["concurrency"]["group"])
    assert not seal_group.startswith("present-")
    assert not present_group.startswith("seal-")

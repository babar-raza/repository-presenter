"""TC-RSL-01: the pure parts of tools/reviewer/reseal_wave (queue, limits, row parsing, resume).

tools/ is never imported by src/; tests may import it (as tests/test_bundle_audits.py does). CI does
not run tools/ tests, so this lives here. Nothing here starts a process, worktree or provider call.
"""

from __future__ import annotations

import json

import pytest
import tools.reviewer.reseal_wave.reseal_wave as rw

REGISTRY = json.dumps(
    {
        "entries": [
            {
                "repository": "o/A-Py",
                "family": "words",
                "platform": "python",
                "mode": "full",
                "active": True,
            },
            {
                "repository": "o/B-Net",
                "family": "slides",
                "platform": "net",
                "mode": "dry_run",
                "active": True,
            },
            {
                "repository": "o/C-Off",
                "family": "cells",
                "platform": "go",
                "mode": "disabled",
                "active": True,
            },
            {
                "repository": "o/D-Inactive",
                "family": "pdf",
                "platform": "java",
                "mode": "dry_run",
                "active": False,
            },
        ]
    }
)
CUT = "0123456789abcdef0123456789abcdef01234567"


def test_enabled_excludes_disabled_and_inactive() -> None:
    assert [e.repository for e in rw.enabled(rw.parse_registry(REGISTRY))] == ["o/A-Py", "o/B-Net"]


def test_parallelism_limit() -> None:
    assert rw.check_parallelism(4) == 4
    assert rw.check_parallelism(8) == 8
    with pytest.raises(ValueError, match="ceiling"):
        rw.check_parallelism(9)
    with pytest.raises(ValueError):
        rw.check_parallelism(0)


def test_select_filters_and_rejects_unknown() -> None:
    entries = rw.parse_registry(REGISTRY)
    assert [e.repository for e in rw.select_entries(entries, families=["slides"])] == ["o/B-Net"]
    assert [e.repository for e in rw.select_entries(entries, repos=["o/B-Net", "o/A-Py"])] == [
        "o/B-Net",
        "o/A-Py",
    ]
    with pytest.raises(ValueError, match="o/C-Off"):
        rw.select_entries(entries, repos=["o/C-Off"])  # disabled is not silently skipped


def test_queue_skips_repositories_with_a_row_and_retries_only_on_request() -> None:
    selected = rw.select_entries(rw.parse_registry(REGISTRY))
    rows = [
        {"repository": "o/A-Py", "status": "SEALED"},
        {"repository": "o/B-Net", "status": "FAILED"},
    ]
    jobs, skipped = rw.build_queue(selected, rows, CUT)
    assert jobs == [] and len(skipped) == 2
    jobs, skipped = rw.build_queue(selected, rows, CUT, retry_failed=True)
    assert [j.entry.repository for j in jobs] == ["o/B-Net"]  # SEALED is never re-queued
    assert [e.repository for e, _ in skipped] == ["o/A-Py"]


def test_retry_takes_a_fresh_short_worktree_name() -> None:
    selected = rw.select_entries(rw.parse_registry(REGISTRY), repos=["o/B-Net"])
    taken = {"rs-slides-net", "rs-slides-net-2"}
    (job,) = rw.build_queue(selected, [], CUT, path_taken=lambda name: name in taken)[0]
    assert job.name == "rs-slides-net-3" and job.attempt == 3
    assert job.branch == "wt/rs-slides-net-3-01234567"
    assert len(job.name) < 24  # MAX_PATH is the reason names stay short


def test_latest_row_wins() -> None:
    rows = [{"repository": "x", "status": "FAILED"}, {"repository": "x", "status": "SEALED"}]
    assert rw.latest_rows(rows)["x"]["status"] == "SEALED"


def test_parse_present_output_reads_stage_counts_verdict_and_bundle() -> None:
    stdout = "\n".join(
        [
            "admitted: o/A-Py (mode full, ecosystem python, family words, platform python)",
            "snapshot: o/A-Py at abc in runs/clones/x (push disabled, verified)",
            "validation: runs/t/x/validation.json (pass 11, fail 0, pending 2; digest d)",
            "review: runs/t/x/review.json (verdict ACCEPT, findings 1, advisory 3, preserve 4; "
            "provider calls 3, model m; digest d)",
            "repair: none; rounds 1",
            "bundle: candidates/o__A-Py/abc "
            "(state READY_FOR_PROPOSAL, 14 files, provider calls 41; sealed)",
        ]
    )
    parsed = rw.parse_present_output(stdout)
    assert parsed["stage_reached"] == "bundle"
    assert (parsed["validation_pass"], parsed["validation_fail"], parsed["validation_pending"]) == (
        11,
        0,
        2,
    )
    assert (parsed["review_verdict"], parsed["review_findings"]) == ("ACCEPT", 1)
    assert parsed["bundle_state"] == "READY_FOR_PROPOSAL"
    assert parsed["bundle_path"] == "candidates/o__A-Py/abc"
    assert parsed["reported_provider_calls"] == 41


def test_parse_present_output_non_processable_and_validation_failure() -> None:
    assert (
        rw.parse_present_output(
            "NON_PROCESSABLE: insufficient_evidence (x) for o/A at abc; resume when y"
        )["stage_reached"]
        == "NON_PROCESSABLE"
    )
    failure = rw.parse_present_output(
        "plan: p (x)",
        "repository-presenter: validation: BC-10 failed at S6: claim unsupported; stands",
    )
    assert failure["failed_check"] == "BC-10" and failure["failed_stage"] == "S6"
    assert failure["stage_reached"] == "plan"


def test_count_provider_calls_only_counts_provider_calls_of_this_invocation() -> None:
    lines = [
        json.dumps({"disposition": "provider_call", "invocation_id": "a"}),
        json.dumps({"disposition": "provider_call", "invocation_id": "b"}),
        json.dumps({"disposition": "cache_reuse", "invocation_id": "b"}),
        json.dumps(
            {"disposition": "provider_call"}
        ),  # an unstamped record counts for any invocation
        "not json",
        "",
    ]
    assert rw.count_provider_calls(lines, "a") == 2
    assert rw.count_provider_calls(lines, "b") == 2
    assert rw.count_provider_calls(lines) == 3


def test_noop_verdicts() -> None:
    assert (
        rw.parse_noop_output(0, "no-op proof verified: rerun x ... 0 provider calls", "")
        == "VERIFIED"
    )
    assert rw.parse_noop_output(0, "no-op proof not applicable: both runs", "") == "NOT_APPLICABLE"
    assert (
        rw.parse_noop_output(
            1, "", "repository-presenter: no-op proof failed [NONZERO_PROVIDER_CALLS]: 3"
        )
        == "FAILED:NONZERO_PROVIDER_CALLS"
    )
    assert rw.parse_noop_output(None, "", "") == "NOT_RUN"


@pytest.mark.parametrize(
    ("phase", "timed_out", "parsed", "text", "expected"),
    [
        ("present-1", True, {}, "", "timeout"),
        ("preflight", False, {}, "boom", "gateway"),
        ("present-1", False, {"failed_check": "BC-14", "failed_stage": "S4"}, "", "BC-14"),
        ("present-1", False, {}, "FileNotFoundError: dotnet", "toolchain"),
        ("present-1", False, {}, "the gateway did not answer after the bounded retries", "gateway"),
        ("present-1", False, {}, "fatal: repository not found", "clone"),
        ("present-1", False, {}, "something else", "unknown"),
        ("noop", False, {}, "no-op proof failed", "noop_proof"),
    ],
)
def test_failure_class_guess(
    phase: str, timed_out: bool, parsed: dict, text: str, expected: str
) -> None:
    assert rw.classify_failure(phase, 1, timed_out, parsed, text)[0] == expected


def test_failure_stage_comes_from_the_failed_check() -> None:
    assert (
        rw.classify_failure(
            "present-1", 1, False, {"failed_check": "BC-14", "failed_stage": "S4"}, ""
        )[1]
        == "S4"
    )


def test_row_status_requires_ready_state_accept_and_noop_proof() -> None:
    ready = {"bundle_state": "READY_FOR_PROPOSAL", "review_verdict": "ACCEPT"}
    assert rw.row_status(0, 0, "VERIFIED", ready, ready, False) == "SEALED"
    assert (
        rw.row_status(
            0,
            0,
            "VERIFIED",
            {"bundle_state": "READY_FOR_PROPOSAL", "review_verdict": "REJECT"},
            ready,
            False,
        )
        == "NOT_READY"
    )
    assert (
        rw.row_status(0, 0, "VERIFIED", {"bundle_state": "INVALIDATED"}, {}, False) == "NOT_READY"
    )
    assert rw.row_status(0, 0, "FAILED:SAME_PROCESS", ready, ready, False) == "FAILED"
    assert rw.row_status(1, None, "NOT_RUN", {}, {}, False) == "FAILED"
    assert (
        rw.row_status(0, None, "NOT_APPLICABLE", {}, {"stage_reached": "NON_PROCESSABLE"}, False)
        == "NON_PROCESSABLE"
    )
    assert rw.row_status(None, None, "NOT_RUN", {}, {}, True) == "TIMEOUT"


def test_outputs_round_trip_and_resume(tmp_path) -> None:
    rows = [
        {"repository": "o/A-Py", "status": "FAILED", "minutes": 1.0, "changed_paths": ["a"]},
        {
            "repository": "o/A-Py",
            "status": "SEALED",
            "minutes": 2.0,
            "changed_paths": ["candidates/x", "y"],
        },
    ]
    (tmp_path / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    loaded = rw.load_rows(tmp_path)
    rw.write_outputs(tmp_path, loaded, CUT)
    document = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert document["cut"] == CUT and [r["status"] for r in document["rows"]] == ["SEALED"]
    csv_text = (tmp_path / "results.csv").read_text(encoding="utf-8")
    assert csv_text.splitlines()[0].startswith("repository,status") and "candidates/x;y" in csv_text
    jobs, skipped = rw.build_queue(rw.select_entries(rw.parse_registry(REGISTRY)), loaded, CUT)
    assert [j.entry.repository for j in jobs] == ["o/B-Net"] and len(skipped) == 1


def test_environment_prepends_node_to_the_subprocess_path_only(tmp_path, monkeypatch) -> None:
    node = tmp_path / "nodejs"
    node.mkdir()
    monkeypatch.setenv("PATH", "base")
    runner = rw.Runner(
        control_root=tmp_path,
        main_root=tmp_path,
        python="py",
        bash="bash",
        cut=CUT,
        results_dir=tmp_path,
        timeout_seconds=1,
        extra_path=[str(node), str(tmp_path / "absent")],
        gh_token="tok",
    )
    env = runner.env_for(tmp_path / "wt")
    assert env["PATH"] == f"{node}{rw.os.pathsep}base"
    assert env["PYTHONPATH"] == str(tmp_path / "wt" / "src") and env["GH_TOKEN"] == "tok"
    assert rw.os.environ["PATH"] == "base"  # the machine's own PATH is untouched


def test_invalidated_bundle_line_is_read() -> None:
    parsed = rw.parse_present_output(
        "bundle: candidates/o__A/abc (state INVALIDATED; BC-05 failed at EXTRACTING)"
    )
    assert parsed["bundle_state"] == "INVALIDATED"
    assert parsed["bundle_path"] == "candidates/o__A/abc"
    assert "reported_provider_calls" not in parsed


FAKE_MAIN = r"""
import json, os, sys, time
args = sys.argv[1:]
mode = os.environ.get("FAKE_MODE", "ok")
cmd = args[0]
if cmd == "preflight":
    print("gateway: reachable")
elif cmd == "present":
    record = args[args.index("--invocation-record") + 1]
    n = 2 if os.path.exists("runs/ledger-1.jsonl") else 1
    if mode == "hang" and n == 1:
        time.sleep(600)
    calls = 3 if n == 1 else 0
    with open(f"runs/ledger-{n}.jsonl", "w") as ledger:
        for _ in range(calls):
            line = {"disposition": "provider_call", "invocation_id": f"i{n}"}
            ledger.write(json.dumps(line) + "\n")
    with open(record, "w") as handle:
        json.dump({"invocation_id": f"i{n}", "ledger": f"runs/ledger-{n}.jsonl"}, handle)
    if mode == "fail":
        print("plan: p (x)")
        print("validation: v (pass 9, fail 1, pending 0; digest d)")
        print("bundle: candidates/o__A/abc (state INVALIDATED; BC-10 failed at S6)")
        print("repository-presenter: validation: BC-10 failed at S6: claim", file=sys.stderr)
        sys.exit(1)
    print("validation: v (pass 11, fail 0, pending 0; digest d)")
    print("review: r (verdict ACCEPT, findings 0, advisory 0, preserve 1; digest d)")
    print("bundle: candidates/o__A/abc (state READY_FOR_PROPOSAL, 14 files,"
          f" provider calls {calls}; ok)")
elif cmd == "verify-noop-proof":
    print("no-op proof verified: rerun i2 is a different process; 0 provider calls")
"""


def _fake_runner(tmp_path, monkeypatch, mode: str, timeout: float = 60):
    worktree = tmp_path / "wt"
    package = worktree / "src" / "repository_presenter"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(FAKE_MAIN, encoding="utf-8")
    (worktree / "runs").mkdir()
    monkeypatch.setenv("FAKE_MODE", mode)
    runner = rw.Runner(
        control_root=tmp_path,
        main_root=tmp_path,
        python=rw.sys.executable,
        bash="bash",
        cut=CUT,
        results_dir=tmp_path,
        timeout_seconds=timeout,
        extra_path=[],
        gh_token=None,
    )
    monkeypatch.setattr(runner, "create_worktree", lambda job: worktree)
    monkeypatch.setattr(runner, "worktree_path", lambda name: worktree)
    entry = rw.Entry("o/A", "words", "python", "full", True)
    return runner, rw.Job(entry, 1, "rs-words-python", "wt/x")


def test_run_job_success_path_runs_two_presents_and_the_noop_proof(tmp_path, monkeypatch) -> None:
    runner, job = _fake_runner(tmp_path, monkeypatch, "ok")
    row = rw.run_job(runner, job)
    assert row["status"] == "SEALED", row
    assert (row["exit_preflight"], row["exit_present1"], row["exit_present2"]) == (0, 0, 0)
    assert (row["provider_calls_run1"], row["provider_calls_run2"]) == (3, 0)
    assert row["noop_proof"] == "VERIFIED" and row["bundle_state"] == "READY_FOR_PROPOSAL"
    assert (row["validation_pass"], row["review_verdict"]) == (11, "ACCEPT")
    assert (tmp_path / "wt" / "runs" / "reseal-logs" / "present-2.out").is_file()


def test_run_job_records_a_validation_failure_and_stops_before_the_second_run(
    tmp_path, monkeypatch
) -> None:
    runner, job = _fake_runner(tmp_path, monkeypatch, "fail")
    row = rw.run_job(runner, job)
    assert row["status"] == "FAILED" and row["failure_class"] == "BC-10"
    assert row["failure_stage"] == "S6" and row["exit_present2"] is None
    assert row["provider_calls_run1"] == 3 and row["noop_proof"] == "NOT_RUN"
    assert row["bundle_state"] == "INVALIDATED"


def test_run_job_times_out_and_kills_the_run(tmp_path, monkeypatch) -> None:
    runner, job = _fake_runner(tmp_path, monkeypatch, "hang", timeout=8)
    row = rw.run_job(runner, job)
    assert row["status"] == "TIMEOUT" and row["failure_class"] == "timeout"
    assert runner.live == set()  # nothing left running

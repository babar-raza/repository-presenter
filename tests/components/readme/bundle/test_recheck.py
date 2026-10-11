"""The consumed-scope recheck: currency states, per-scope rechecks, receipts, and the status split.

Docs/investigations/13-bump-cost-and-recheck-design.md section 6.6 (G7-W25). The fixture is a real
committed bundle (the smallest one that keeps its raw reads), copied beside the registry and prompts
into a scratch root; each test moves one recorded input or mutates one piece of running code and
asserts the currency, so nothing here depends on which README the bundle happens to say.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.readme.bundle import recheck
from repository_presenter.components.readme.bundle.dry_run import code_derived_dependencies
from repository_presenter.components.readme.bundle.recheck import (
    CURRENT,
    RECHECKED_CURRENT,
    UNVERIFIED,
    UPDATE_OPTIONAL,
    UPDATE_REQUIRED,
    ScopeResult,
    classify,
    recheck_bundle,
    recheck_portfolio,
    recheck_scope,
    render_lines,
    reverse_apply,
)
from repository_presenter.components.readme.bundle.seal import code_dependencies
from repository_presenter.components.readme.composition import audience
from repository_presenter.components.readme.composition.renderer import render_patch
from repository_presenter.components.readme.validation import deferrals
from repository_presenter.core.candidates import BundleError, verify_bundle
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.loader import find_entry, load_registry
from support import REPO_ROOT, write_cursor

DIRECTORY = "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python"
REPOSITORY = "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python"
MANIFESTS = load_manifests(REPO_ROOT / "prompts")
CODE = code_dependencies(MANIFESTS)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class Fixture:
    """A scratch project root holding one committed bundle, with helpers that keep the manifest's
    inventory true after an edit, so ``verify_bundle`` passes unless a test tampers on purpose."""

    def __init__(self, root: Path) -> None:
        self.root = root
        source = REPO_ROOT / "candidates" / DIRECTORY
        shutil.copytree(source, root / "candidates" / DIRECTORY)
        (root / "data").mkdir()
        shutil.copy(REPO_ROOT / "data" / "registry.json", root / "data" / "registry.json")
        write_cursor(root, recorded_candidates=1)
        shutil.copytree(REPO_ROOT / "prompts", root / "prompts")
        self.bundle = (
            root
            / "candidates"
            / DIRECTORY
            / (root / "candidates" / DIRECTORY / "CURRENT").read_text(encoding="utf-8").strip()
        )

    @property
    def dependencies(self) -> dict[str, Any]:
        return json.loads((self.bundle / "dependencies.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def _redigest(self, *names: str) -> None:
        manifest_path = self.bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name in names:
            path = self.bundle / name
            if path.is_file():
                data = path.read_bytes()
                manifest["files"][name] = {"sha256": _sha256(data), "bytes": len(data)}
            else:
                manifest["files"].pop(name, None)
        _write_json(manifest_path, manifest)

    def set_dependencies(self, document: dict[str, Any]) -> None:
        _write_json(self.bundle / "dependencies.json", document)
        self._redigest("dependencies.json")

    def freshen(self) -> None:
        """The record a seal under the running code would have written: nothing differs."""
        sealed = self.dependencies
        fresh = {
            **sealed,
            **{key: value for key, value in CODE.items() if key != "environment"},
            "environment": {**sealed["environment"], **CODE["environment"]},
        }
        self.set_dependencies(fresh)

    def move(self, *path: str, to: Any) -> None:
        """Set one recorded input to ``to`` (a stale constant), leaving the rest current."""
        document = self.dependencies
        target = document
        for part in path[:-1]:
            target = target[part]
        if to is None:
            target.pop(path[-1], None)
        else:
            target[path[-1]] = to
        self.set_dependencies(document)

    def drop_artifact(self, name: str) -> None:
        (self.bundle / name).unlink()
        self._redigest(name)

    def recheck(self, **keywords: Any) -> recheck.Recheck:
        entry = find_entry(load_registry(self.root / "data" / "registry.json"), REPOSITORY)
        keywords.setdefault("use_receipts", False)
        return recheck_bundle(
            self.root, DIRECTORY, CODE, entry=entry, manifests=MANIFESTS, **keywords
        )


@pytest.fixture
def fixture(tmp_path: Path) -> Fixture:
    built = Fixture(tmp_path)
    built.freshen()
    return built


def _scope(result: recheck.Recheck, name: str) -> ScopeResult:
    return next(scope for scope in result.scopes if scope.scope == name)


# --- currency states -----------------------------------------------------------------------------


def test_a_bundle_sealed_on_the_running_code_is_current_and_nothing_runs(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_arguments: Any, **_keywords: Any) -> Any:
        raise AssertionError("a current bundle must not re-run any scope")

    monkeypatch.setattr(recheck, "render_readme", forbidden)
    monkeypatch.setattr(recheck.validation, "validate_candidate", forbidden)
    monkeypatch.setattr(recheck, "review_document", forbidden)
    result = fixture.recheck()
    assert (result.currency, result.cost, result.scopes) == (CURRENT, None, ())


def _without_the_audience_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    """The committed BarCode-Python bundle was sealed before the audience rule, and its opening
    says "Developers use it to automate barcode generation in reports, inventory systems, and
    packaging workflows", which no fact says. A test about a currency state that is not that rule
    switches it off here; ``test_a_sealed_opening_naming_an_unsupported_audience_...`` pins what
    the rule does to this very bundle."""
    monkeypatch.setattr(audience, "AUDIENCE_SECTIONS", frozenset())


def _without_the_deferral_escalations(monkeypatch: pytest.MonkeyPatch) -> None:
    """The committed BarCode-Python bundle was sealed before an advisory deferral had to be backed
    by the README: its Enterprise Edition paragraph, whose link the upstream's own README verified,
    was deferred as "no verified target" and never rendered. A test about a currency state that is
    not that rule switches it off here; ``test_a_sealed_deferral_the_readme_does_not_back_...``
    pins what the rule does to this very bundle."""
    monkeypatch.setattr(deferrals, "ESCALATIONS", {})


def test_constants_bumped_with_no_behavior_change_leave_the_bundle_rechecked_current(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the whole design: a version moved, nothing the bundle consumed changed."""
    _without_the_audience_rule(monkeypatch)
    _without_the_deferral_escalations(monkeypatch)
    fixture.move("components", "renderer", to="0")
    fixture.move("components", "normalisation", to="0")
    fixture.move("validator_version", to="0")
    fixture.move("validators", "BC-02", to="0")
    result = fixture.recheck()
    assert result.currency == RECHECKED_CURRENT, [s.to_json() for s in result.scopes]
    assert {s.scope for s in result.scopes} == {"presentation", "authoring", "validator"}
    assert all(s.outcome == "PASSED" for s in result.scopes)
    assert _scope(result, "validator").partial  # the judges that see less than a real run say so


def test_a_prompt_or_label_difference_is_provenance_and_an_optional_update(
    fixture: Fixture,
) -> None:
    fixture.move("prompts", "section_authoring", "sha256", to="0" * 64)
    fixture.move("contract_version", to="readme-contract-vOLD")
    fixture.move("acceptance_profile_version", to=None)
    fixture.move("policy", "version", to="0")
    result = fixture.recheck()
    assert result.currency == UPDATE_OPTIONAL
    assert [s.scope for s in result.scopes] == ["provenance"]
    assert set(result.scopes[0].triggers) >= {"prompts.section_authoring", "contract_version"}
    assert result.counted


def test_a_difference_the_recheck_has_no_row_for_raises_rather_than_guessing() -> None:
    with pytest.raises(Exception, match="no recheck for the dependency 'surprise'"):
        recheck_scope("surprise")
    assert recheck_scope("prompts.anything") == "provenance"
    assert recheck_scope("environment.inherited_units_version") == "extraction"


# --- one mutation per scope gives UPDATE_REQUIRED ----------------------------------------------


def test_a_mutated_renderer_gives_update_required(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("components", "renderer", to="0")
    real = recheck.render_readme
    monkeypatch.setattr(recheck, "render_readme", lambda *a, **k: real(*a, **k) + "\nmutated\n")
    result = fixture.recheck()
    assert result.currency == UPDATE_REQUIRED
    assert _scope(result, "presentation").outcome == "FAILED"
    assert not result.counted


def _force_check(monkeypatch: pytest.MonkeyPatch, check_id: str) -> None:
    real = recheck.validation.validate_candidate

    def judged(candidate: Any, transaction: Path, secrets: Any) -> dict[str, Any]:
        document: dict[str, Any] = real(candidate, transaction, secrets)
        for check in document["checks"]:
            if check["id"] == check_id:
                check["verdict"] = "FAIL"
                check["details"] = ["forced by the test"]
        return document

    monkeypatch.setattr(recheck.validation, "validate_candidate", judged)


def test_a_judge_forced_to_fail_gives_update_required_and_recompose(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("validators", "BC-07", to="0")
    _force_check(monkeypatch, "BC-07")
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "recompose")
    assert "BC-07: forced by the test" in _scope(result, "validator").failures


def test_a_tightened_authoring_gate_gives_update_required(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("components", "normalisation", to="0")
    _force_check(monkeypatch, "BC-04")
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "recompose")
    assert _scope(result, "authoring").outcome == "FAILED"


def test_a_sealed_opening_naming_an_unsupported_audience_gives_update_required(
    fixture: Fixture,
) -> None:
    """Wave-3 acceptance review, U-AUDIENCE: a sealed opening that says who uses the library and
    for what, with no fact behind it, is not left "current" when the authoring gate tightens - the
    recheck finds it and the bundle needs a recompose (the same road BC-12 took), never a silent
    pass and never a blanket invalidation of bundles the rule does not touch."""
    fixture.move("components", "normalisation", to="0")
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "recompose")
    assert _scope(result, "authoring").outcome == "FAILED"
    assert any("audience" in failure for failure in _scope(result, "authoring").failures)


def test_a_sealed_deferral_the_readme_does_not_back_gives_update_required(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave-3 acceptance review: an advisory deferral that hid a true loss. The sealed bundle
    deferred its Enterprise Edition paragraph for want of a target although the upstream's own link
    was verified; the validator scope finds it when the validator moves, and the bundle needs the
    extraction fix and a recompose rather than a silent pass."""
    _without_the_audience_rule(monkeypatch)
    fixture.move("validator_version", to="0")
    fixture.move("validators", "BC-05", to="0")
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "recompose")
    failures = _scope(result, "validator").failures
    assert any("ENTERPRISE_NO_VERIFIED_TARGET" in failure for failure in failures)


def test_a_presentation_only_difference_is_the_cheap_rerender_only_update(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-render passes every deterministic judge but the bytes change: one fresh review read."""
    fixture.move("components", "renderer", to="0")
    real = recheck.render_readme
    monkeypatch.setattr(recheck, "render_readme", lambda *a, **k: real(*a, **k).rstrip() + "\n\n")
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "rerender_only")
    assert [(s.scope, s.outcome) for s in result.scopes] == [("presentation", "FAILED")]


def test_the_reviewer_replay_matches_a_faithful_fold_and_fails_a_mutated_one(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("components", "reviewer_logic", to="0")
    sealed = json.loads((fixture.bundle / "review.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(recheck, "review_document", lambda *a, **k: sealed)
    faithful = fixture.recheck()
    assert _scope(faithful, "reviewer").outcome == "PASSED"
    assert faithful.currency == RECHECKED_CURRENT

    flipped = {**sealed, "verdict": "REJECT_PRESENTATION"}
    monkeypatch.setattr(recheck, "review_document", lambda *a, **k: flipped)
    mutated = fixture.recheck()
    assert (mutated.currency, mutated.cost) == (UPDATE_REQUIRED, "recompose")
    assert _scope(mutated, "reviewer").outcome == "FAILED"


def test_a_bundle_with_no_retained_raw_reads_has_an_unverified_reviewer_scope(
    fixture: Fixture,
) -> None:
    fixture.drop_artifact("raw_calls.json")
    fixture.move("components", "reviewer_logic", to="0")
    result = fixture.recheck()
    assert result.currency == UNVERIFIED
    assert _scope(result, "reviewer").outcome == "UNVERIFIED"
    assert not result.counted  # an unverified reviewer scope is not independently accepted


def test_a_failing_scope_outranks_an_unverified_one(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.drop_artifact("raw_calls.json")
    fixture.move("components", "reviewer_logic", to="0")
    fixture.move("components", "renderer", to="0")
    real = recheck.render_readme
    monkeypatch.setattr(recheck, "render_readme", lambda *a, **k: real(*a, **k) + "x")
    assert fixture.recheck().currency == UPDATE_REQUIRED


# --- a check or key the sealed record lacks must be run, not skipped ------------------------------


def test_a_check_the_sealed_record_lacks_is_run_and_its_failure_is_reported(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BC-12 failed on 3 sealed bundles and was never reported: the record had no BC-12 row."""
    _without_the_audience_rule(monkeypatch)
    _without_the_deferral_escalations(monkeypatch)
    fixture.move("validators", "BC-12", to=None)
    validation = json.loads((fixture.bundle / "validation.json").read_text(encoding="utf-8"))
    validation["checks"] = [c for c in validation["checks"] if c["id"] != "BC-12"]
    _write_json(fixture.bundle / "validation.json", validation)
    fixture._redigest("validation.json")

    passing = fixture.recheck()
    assert passing.unrecorded == ("validators.BC-12",)
    assert passing.currency == RECHECKED_CURRENT
    assert "no sealed baseline, must pass" in _scope(passing, "validator").detail

    _force_check(monkeypatch, "BC-12")
    failing = fixture.recheck()
    assert (failing.currency, failing.cost) == (UPDATE_REQUIRED, "recompose")
    assert "BC-12: forced by the test" in _scope(failing, "validator").failures


# --- extraction ------------------------------------------------------------------------------


def test_an_inherited_units_version_that_regenerates_identically_is_rechecked_current(
    fixture: Fixture,
) -> None:
    fixture.move("environment", "inherited_units_version", to="0")
    result = fixture.recheck()
    assert result.currency == RECHECKED_CURRENT
    assert _scope(result, "extraction").outcome == "PASSED"


def test_regenerated_inherited_units_that_differ_would_re_extract_never_invalidate(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("environment", "inherited_units_version", to="0")
    real = recheck.inherited_unit_facts

    def altered(*arguments: Any, **keywords: Any) -> list[Any]:
        facts = list(real(*arguments, **keywords))
        return facts[1:]  # one unit gone

    monkeypatch.setattr(recheck, "inherited_unit_facts", altered)
    result = fixture.recheck()
    assert (result.currency, result.cost) == (UPDATE_REQUIRED, "recompose")
    assert "1 removed" in _scope(result, "extraction").detail
    # the bundle is untouched: a recheck reports, it never records INVALIDATED
    assert json.loads((fixture.bundle / "manifest.json").read_text("utf-8"))["state"] == (
        "READY_FOR_PROPOSAL"
    )


def test_an_extractor_version_change_needs_a_clone_for_the_other_fact_kinds(
    fixture: Fixture,
) -> None:
    fixture.move("environment", "extractor_version", to="0")
    result = fixture.recheck()
    assert result.currency == UNVERIFIED
    assert "need a clone" in _scope(result, "extraction").detail


# --- integrity first, receipts as a cache -------------------------------------------------


def test_a_tampered_file_fails_integrity_before_any_scope_runs(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("components", "renderer", to="0")
    (fixture.bundle / "README.md").write_text("tampered\n", encoding="utf-8")

    def forbidden(*_arguments: Any, **_keywords: Any) -> Any:
        raise AssertionError("no scope may run on a bundle that fails integrity")

    monkeypatch.setattr(recheck, "render_readme", forbidden)
    with pytest.raises(BundleError, match="corrupt"):
        fixture.recheck()
    (row,) = recheck_portfolio(fixture.root, CODE)
    assert row.currency == UNVERIFIED and row.error is not None
    assert row.error.startswith("integrity:") and not row.counted


def test_a_receipt_is_a_cache_keyed_by_the_manifest_digest_and_the_running_constants(
    fixture: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture.move("components", "renderer", to="0")
    manifest_sha = _sha256((fixture.bundle / "manifest.json").read_bytes())
    computed = fixture.recheck()
    receipt = recheck.write_receipt(fixture.root, computed, manifest_sha)
    assert receipt == fixture.root / "candidates" / DIRECTORY / "rechecks" / (
        fixture.bundle.name + ".json"
    )
    verify_bundle(fixture.bundle)  # a receipt lives beside the bundle, never inside it

    def forbidden(*_arguments: Any, **_keywords: Any) -> Any:
        raise AssertionError("a valid receipt must be reused, not recomputed")

    monkeypatch.setattr(recheck, "render_readme", forbidden)
    cached = fixture.recheck(use_receipts=True)
    assert cached.cached and cached.currency == computed.currency
    assert [s.to_json() for s in cached.scopes] == [s.to_json() for s in computed.scopes]


def test_a_receipt_under_another_key_or_with_a_forged_body_is_ignored(
    fixture: Fixture,
) -> None:
    fixture.move("components", "renderer", to="0")
    manifest_sha = _sha256((fixture.bundle / "manifest.json").read_bytes())
    computed = fixture.recheck()
    path = recheck.write_receipt(fixture.root, computed, manifest_sha)
    key = computed.key

    # another running code: the constants the scopes consumed differ, so the key does
    other = {**CODE, "components": {**CODE["components"], "renderer": "9999"}}
    assert recheck.receipt_key(manifest_sha, other) != key
    assert recheck.read_receipt(fixture.root, DIRECTORY, fixture.bundle.name, key) is not None
    assert (
        recheck.read_receipt(
            fixture.root,
            DIRECTORY,
            fixture.bundle.name,
            recheck.receipt_key(manifest_sha, other),
        )
        is None
    )
    # another manifest digest (the state moved, say) is another key as well
    assert recheck.receipt_key("0" * 64, CODE) != key

    # a forged receipt: the currency edited by hand no longer hashes to its own digest
    document = json.loads(path.read_text(encoding="utf-8"))
    document["currency"] = CURRENT
    path.write_text(json.dumps(document), encoding="utf-8")
    assert recheck.read_receipt(fixture.root, DIRECTORY, fixture.bundle.name, key) is None
    path.write_text("not json", encoding="utf-8")
    assert recheck.read_receipt(fixture.root, DIRECTORY, fixture.bundle.name, key) is None
    # ... and the recompute is what the caller gets
    assert fixture.recheck(use_receipts=True).currency == computed.currency


def test_the_portfolio_recheck_without_compute_reads_receipts_only(fixture: Fixture) -> None:
    fixture.move("components", "renderer", to="0")
    (row,) = recheck_portfolio(fixture.root, CODE, compute=False)
    assert row.currency == UNVERIFIED and "no receipt" in (row.error or "")
    (written,) = recheck_portfolio(fixture.root, CODE, write_receipts=True)
    (cached,) = recheck_portfolio(fixture.root, CODE, compute=False)
    assert cached.cached and cached.currency == written.currency


# --- the CLI ---------------------------------------------------------------------------


def test_the_recheck_command_reports_read_only_and_writes_receipts_only_on_request(
    fixture: Fixture, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture.move("components", "renderer", to="0")
    before = (fixture.bundle / "manifest.json").read_bytes()
    argv = ["recheck", "--root", str(fixture.root), "--repo", REPOSITORY, "--json"]
    assert main(argv) == EXIT_OK
    document = json.loads(capsys.readouterr().out)
    assert set(document["counts"]) == {
        "CURRENT",
        "RECHECKED_CURRENT",
        "UPDATE_OPTIONAL",
        "UPDATE_REQUIRED",
        "UNVERIFIED",
    }
    (entry,) = document["bundles"]
    assert entry["repository_dir"] == DIRECTORY
    assert not (fixture.root / "candidates" / DIRECTORY / "rechecks").exists()

    assert main(["recheck", "--root", str(fixture.root), "--write-receipts"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "currency:" in out and DIRECTORY in out
    assert (
        fixture.root / "candidates" / DIRECTORY / "rechecks" / f"{fixture.bundle.name}.json"
    ).is_file()
    assert (
        fixture.bundle / "manifest.json"
    ).read_bytes() == before  # the sealed bundle is untouched


def test_the_recheck_command_refuses_a_repository_with_no_bundle(
    fixture: Fixture, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["recheck", "--root", str(fixture.root), "--repo", "owner/none"]) != EXIT_OK
    assert "no current bundle" in capsys.readouterr().err


def test_status_counts_a_rechecked_current_bundle_and_splits_the_rest(
    fixture: Fixture, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture.move("components", "renderer", to="0")  # behind the running code's recorded versions
    assert main(["status", "--root", str(fixture.root), "--json"]) == 0
    before = json.loads(capsys.readouterr().out)
    assert before["recheck"]["currency"] == {DIRECTORY: UNVERIFIED}  # no receipt yet
    assert before["portfolio"]["buckets"]["update_unverified"] == 1
    assert sum(before["portfolio"]["buckets"].values()) == before["portfolio"]["denominator"]

    assert main(["recheck", "--root", str(fixture.root), "--write-receipts"]) == EXIT_OK
    capsys.readouterr()
    assert main(["status", "--root", str(fixture.root), "--json"]) == 0
    after = json.loads(capsys.readouterr().out)
    assert after["recheck"]["currency"] == {DIRECTORY: RECHECKED_CURRENT}
    assert after["progress"]["independently_accepted_stale_excluded"] == (
        before["progress"]["independently_accepted_stale_excluded"] + 1
    )
    assert after["portfolio"]["buckets"]["update_unverified"] == 0
    assert after["portfolio"]["buckets"]["update_required"] == 0
    assert sum(after["portfolio"]["buckets"].values()) == after["portfolio"]["denominator"]


# --- pure pieces ---------------------------------------------------------------------------


def _result(scope: str, outcome: str) -> ScopeResult:
    return ScopeResult(scope, outcome, ("x",))


@pytest.mark.parametrize(
    ("scopes", "currency", "cost"),
    [
        ([], CURRENT, None),
        ([_result("provenance", "PROVENANCE")], UPDATE_OPTIONAL, None),
        ([_result("validator", "PASSED")], RECHECKED_CURRENT, None),
        (
            [_result("validator", "PASSED"), _result("provenance", "PROVENANCE")],
            RECHECKED_CURRENT,
            None,
        ),
        ([_result("reviewer", "UNVERIFIED")], UNVERIFIED, None),
        ([_result("presentation", "FAILED")], UPDATE_REQUIRED, "rerender_only"),
        (
            [_result("presentation", "FAILED"), _result("validator", "FAILED")],
            UPDATE_REQUIRED,
            "recompose",
        ),
        ([_result("reviewer", "FAILED")], UPDATE_REQUIRED, "recompose"),
        (
            [_result("reviewer", "UNVERIFIED"), _result("authoring", "FAILED")],
            UPDATE_REQUIRED,
            "recompose",
        ),
    ],
)
def test_the_currency_follows_the_scope_outcomes(
    scopes: list[ScopeResult], currency: str, cost: str | None
) -> None:
    assert classify(scopes) == (currency, cost)


def test_the_original_readme_is_recovered_only_when_the_patch_round_trips() -> None:
    original = "# Title\n\nold line\nkept\n"
    candidate = "# Title\n\nnew line\nkept\nadded\n"
    patch = render_patch(original, candidate)
    assert reverse_apply(candidate, patch) == original
    assert recheck.original_readme(candidate, patch) == original
    # a patch that is not the diff of what it recovers is not trusted
    assert recheck.original_readme(candidate, patch.replace("@@ -1,4", "@@ -1,9")) is None
    assert recheck.original_readme(candidate, patch + "-extra\n") is None


def test_the_committed_bundle_recovers_its_original_readme(fixture: Fixture) -> None:
    readme = (fixture.bundle / "README.md").read_text(encoding="utf-8")
    patch = (fixture.bundle / "README.patch").read_text(encoding="utf-8")
    original = recheck.original_readme(readme, patch)
    assert original is not None and render_patch(original, readme) == patch


def test_the_rendering_names_every_state_and_the_split() -> None:
    row = recheck.Recheck(DIRECTORY, "a" * 40, UPDATE_REQUIRED, "recompose", (), (), (), "k")
    text = "\n".join(render_lines([row]))
    assert "UPDATE_REQUIRED (recompose)" in text and "recompose 1" in text
    assert "counted 0 of 1" in text


def test_the_dry_run_derivation_keeps_the_unrecorded_checks_out_of_the_routing() -> None:
    sealed: dict[str, Any] = {"validators": {"BC-01": "1"}, "environment": {}}
    merged = code_derived_dependencies(sealed, CODE)
    assert set(merged["validators"]) == {"BC-01"}  # the routing never sees a check it did not seal

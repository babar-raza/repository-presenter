"""core/probes.py: probe records serialise deterministically and round-trip the sealed bytes.

probes.json is sealed beside the facts it informed and is never hashed into dependencies.json, so
its only contract is byte stability for a given set of records: the same records, in any order,
must always write the same document. The canary's sealed probes.json is the real-world oracle
for that contract - reading it back and writing it again must reproduce its bytes exactly.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from repository_presenter.core.probes import PROBES_FILENAME, ProbeRecord, write_probes
from support import REPO_ROOT

CANARY_PROBES = (
    REPO_ROOT
    / "candidates"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "65b1f577c0f16d0d9112bb6c1153d3024543ac02"
    / PROBES_FILENAME
)


def _records() -> list[ProbeRecord]:
    return [
        ProbeRecord(
            kind="package_registry", target="pypi:aspose-3d", outcome="RESOLVED", status=200
        ),
        ProbeRecord(
            kind="link",
            target="https://example.invalid/b",
            outcome="MISSING",
            status=404,
            elapsed_ms=12,
        ),
        ProbeRecord(
            kind="link",
            target="https://example.invalid/a",
            outcome="RESOLVED",
            status=200,
            elapsed_ms=7,
        ),
    ]


def test_records_are_written_ordered_by_kind_then_target(tmp_path: Path) -> None:
    path = tmp_path / PROBES_FILENAME
    write_probes(_records(), path)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [(row["kind"], row["target"]) for row in rows] == [
        ("link", "https://example.invalid/a"),
        ("link", "https://example.invalid/b"),
        ("package_registry", "pypi:aspose-3d"),
    ]


def test_output_bytes_do_not_depend_on_input_order(tmp_path: Path) -> None:
    forward = tmp_path / "forward.json"
    reverse = tmp_path / "reverse.json"
    write_probes(_records(), forward)
    write_probes(list(reversed(_records())), reverse)
    assert forward.read_bytes() == reverse.read_bytes()


def test_document_is_sorted_indented_json_with_a_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / PROBES_FILENAME
    write_probes(_records()[:1], path)
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert raw == (json.dumps(json.loads(raw), indent=2, sort_keys=True) + "\n").encode("utf-8")


def test_unset_optional_fields_serialise_as_null(tmp_path: Path) -> None:
    path = tmp_path / PROBES_FILENAME
    write_probes([ProbeRecord(kind="link", target="t", outcome="UNKNOWN")], path)
    (row,) = json.loads(path.read_text(encoding="utf-8"))
    assert row["status"] is None
    assert row["elapsed_ms"] is None
    assert row["observation"] is None


def test_missing_parent_directories_are_created(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "bundle" / PROBES_FILENAME
    write_probes(_records(), path)
    assert path.is_file()


def test_probe_records_are_immutable() -> None:
    record = ProbeRecord(kind="link", target="t", outcome="RESOLVED")
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.outcome = "MISSING"  # type: ignore[misc]


def test_the_canary_sealed_probes_round_trip_byte_for_byte(tmp_path: Path) -> None:
    sealed = CANARY_PROBES.read_bytes()
    rows = json.loads(sealed)
    records = [ProbeRecord(**row) for row in rows]
    rewritten = tmp_path / PROBES_FILENAME
    write_probes(records, rewritten)
    assert rewritten.read_bytes() == sealed

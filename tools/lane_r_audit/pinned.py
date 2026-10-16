"""The pinned reader: the 30 sealed bundles as git blobs at one control revision.

A ratchet that reads ``candidates/*/CURRENT`` measures whatever the sealing workflows last wrote.
This reader instead takes (repository, revision, manifest sha256) triples from ``pins.json`` and
reads each file with ``git cat-file`` at the control revision, so the inputs cannot move. It never
falls back: a control revision that is not in the checkout, a blob that is missing, or a manifest
whose hash is not the pinned one raises ``PinnedInputError``. Hosted CI must fetch the revision;
a test that cannot reach it fails, it never skips.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.acceptance import judge
from repository_presenter.components.readme.bundle.recheck import original_readme

REPO_ROOT = Path(__file__).resolve().parents[2]
PINS_PATH = REPO_ROOT / "data" / "lane_r_corpus" / "pins.json"
SURVEY_PATH = REPO_ROOT / "data" / "readme_standard" / "survey.json"
# The sealed files the metrics read (never calls.jsonl, dependencies.json or examples.json: large
# and not needed; a bundle's manifest hash still covers the bundle's identity).
BUNDLE_FILES: tuple[str, ...] = (
    "README.md",
    "README.patch",
    "manifest.json",
    "validation.json",
    "review.json",
    "facts.json",
    "dispositions.json",
    "content_units.json",
    "plan.json",
)


class PinnedInputError(RuntimeError):
    """The pinned inputs cannot be read exactly as pinned. Never to be skipped around."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo_root: Path, *args: str, stdin: bytes | None = None) -> bytes:
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            input=stdin,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise PinnedInputError(f"git cannot be run: {exc}") from exc
    if done.returncode != 0:
        raise PinnedInputError(
            f"git {' '.join(args[:3])} failed ({done.returncode}): "
            f"{done.stderr.decode('utf-8', 'replace').strip()[:200]}"
        )
    return done.stdout


def require_revision(repo_root: Path, revision: str) -> None:
    """The control revision must be in this checkout (CI fetches it); otherwise fail loudly."""
    try:
        _git(repo_root, "cat-file", "-e", f"{revision}^{{commit}}")
    except PinnedInputError as exc:
        raise PinnedInputError(
            f"control revision {revision} is not in this checkout; fetch it "
            f"(git fetch origin {revision}) - the pinned reader never skips: {exc}"
        ) from exc


def read_blobs(repo_root: Path, specs: list[str]) -> dict[str, bytes | None]:
    """``git cat-file --batch`` over ``<revision>:<path>`` specs; a missing blob is None."""
    if not specs:
        return {}
    out = _git(repo_root, "cat-file", "--batch", stdin=("\n".join(specs) + "\n").encode())
    blobs: dict[str, bytes | None] = {}
    position = 0
    for spec in specs:
        end = out.index(b"\n", position)
        header = out[position:end].decode("utf-8", "replace").split()
        position = end + 1
        if header and header[-1] == "missing":
            blobs[spec] = None
            continue
        if len(header) != 3 or header[1] != "blob":
            raise PinnedInputError(f"{spec} is not a blob: {' '.join(header)}")
        size = int(header[2])
        blobs[spec] = out[position : position + size]
        position += size + 1
    return blobs


@dataclass(frozen=True)
class Pin:
    repository: str
    directory: str
    revision: str
    manifest_sha256: str
    live_readme_sha256: str | None = None


@dataclass(frozen=True)
class Pins:
    control_revision: str
    survey_sha256: str
    bundles: tuple[Pin, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "control_revision": self.control_revision,
            "survey_sha256": self.survey_sha256,
            "bundles": [
                {
                    "repository": pin.repository,
                    "directory": pin.directory,
                    "revision": pin.revision,
                    "manifest_sha256": pin.manifest_sha256,
                    "live_readme_sha256": pin.live_readme_sha256,
                }
                for pin in self.bundles
            ],
        }


def load_pins(path: Path = PINS_PATH) -> Pins:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Pins(
            raw["control_revision"],
            raw["survey_sha256"],
            tuple(
                Pin(
                    row["repository"],
                    row["directory"],
                    row["revision"],
                    row["manifest_sha256"],
                    row.get("live_readme_sha256"),
                )
                for row in raw["bundles"]
            ),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PinnedInputError(f"{path} cannot be read as pins: {exc}") from exc


@dataclass(frozen=True)
class PinnedBundle:
    """One sealed bundle as pinned: the judge's reader view plus the plan and content units."""

    pin: Pin
    sealed: judge._Bundle
    content_units: dict[str, Any] | None
    plan: dict[str, Any] | None
    readme: str
    live: str | None
    facts_by_id: dict[str, dict[str, Any]] = field(default_factory=dict, compare=False, repr=False)

    @property
    def repository(self) -> str:
        return self.pin.repository


def _object(data: bytes | None) -> dict[str, Any] | None:
    if data is None:
        return None
    try:
        loaded = json.loads(data.decode("utf-8"))
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _text(data: bytes | None) -> str | None:
    try:
        return None if data is None else data.decode("utf-8")
    except ValueError:
        return None


def read_bundles(pins: Pins, repo_root: Path = REPO_ROOT) -> list[PinnedBundle]:
    """Every pinned bundle, verified against its manifest hash. Raises on any deviation."""
    require_revision(repo_root, pins.control_revision)
    specs = [
        f"{pins.control_revision}:candidates/{pin.directory}/{pin.revision}/{name}"
        for pin in pins.bundles
        for name in BUNDLE_FILES
    ]
    blobs = read_blobs(repo_root, specs)
    bundles: list[PinnedBundle] = []
    for pin in pins.bundles:
        base = f"{pins.control_revision}:candidates/{pin.directory}/{pin.revision}/"
        files = {name: blobs[base + name] for name in BUNDLE_FILES}
        manifest = files["manifest.json"]
        if manifest is None or sha256_hex(manifest) != pin.manifest_sha256:
            raise PinnedInputError(
                f"{pin.directory}: manifest.json is not the pinned bytes (sha256 differs)"
            )
        sealed = judge._Bundle(
            _text(files["README.md"]),
            _text(files["README.patch"]),
            _object(manifest),
            _object(files["validation.json"]),
            _object(files["review.json"]),
            _object(files["facts.json"]),
            _object(files["dispositions.json"]),
        )
        if sealed.readme is None or sealed.patch is None:
            raise PinnedInputError(f"{pin.directory}: README.md or README.patch is missing")
        try:
            live = original_readme(sealed.readme, sealed.patch)
        except (ValueError, IndexError):
            live = None
        if pin.live_readme_sha256 is not None and (
            live is None or sha256_hex(live.encode("utf-8")) != pin.live_readme_sha256
        ):
            raise PinnedInputError(f"{pin.directory}: the live README is not the pinned bytes")
        facts = {
            str(row["id"]): row
            for row in (sealed.facts or {}).get("facts", [])
            if isinstance(row, dict) and "id" in row
        }
        bundles.append(
            PinnedBundle(
                pin,
                sealed,
                _object(files["content_units.json"]),
                _object(files["plan.json"]),
                sealed.readme,
                live,
                facts,
            )
        )
    return bundles


def check_survey(pins: Pins, survey_path: Path = SURVEY_PATH) -> None:
    """J6's applicability comes from survey.json: it must be the pinned bytes."""
    try:
        actual = sha256_hex(survey_path.read_bytes())
    except OSError as exc:
        raise PinnedInputError(f"{survey_path} cannot be read: {exc}") from exc
    if actual != pins.survey_sha256:
        raise PinnedInputError(
            f"data/readme_standard/survey.json is not the pinned bytes ({actual[:12]} != "
            f"{pins.survey_sha256[:12]}); re-pin through `python -m tools.lane_r_audit pin`"
        )


def build_pins(control_revision: str, repo_root: Path = REPO_ROOT) -> Pins:
    """The pins for every ``candidates/<dir>/CURRENT`` at the control revision."""
    require_revision(repo_root, control_revision)
    listing = _git(repo_root, "ls-tree", "--name-only", f"{control_revision}:candidates/")
    directories = sorted(line for line in listing.decode("utf-8").splitlines() if line)
    current = read_blobs(
        repo_root, [f"{control_revision}:candidates/{name}/CURRENT" for name in directories]
    )
    revisions = {
        name: (current[f"{control_revision}:candidates/{name}/CURRENT"] or b"").decode().strip()
        for name in directories
    }
    manifest_spec = {
        name: f"{control_revision}:candidates/{name}/{revisions[name]}/manifest.json"
        for name in directories
    }
    manifests = read_blobs(repo_root, list(manifest_spec.values()))
    pins: list[Pin] = []
    for name in directories:
        manifest = manifests[manifest_spec[name]]
        if manifest is None:
            raise PinnedInputError(f"{name}: CURRENT names {revisions[name]} with no manifest")
        repository = (_object(manifest) or {}).get("repository")
        if not isinstance(repository, str):
            raise PinnedInputError(f"{name}: manifest.json names no repository")
        pins.append(Pin(repository, name, revisions[name], sha256_hex(manifest)))
    survey = sha256_hex(SURVEY_PATH.read_bytes())
    unhashed = Pins(control_revision, survey, tuple(pins))
    with_live: list[Pin] = []
    for bundle in read_bundles(unhashed, repo_root):
        live = bundle.live
        with_live.append(
            Pin(
                bundle.pin.repository,
                bundle.pin.directory,
                bundle.pin.revision,
                bundle.pin.manifest_sha256,
                None if live is None else sha256_hex(live.encode("utf-8")),
            )
        )
    return Pins(control_revision, survey, tuple(with_live))

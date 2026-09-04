"""No global control-plane hash, ever: a candidate is invalidated only through an input listed in
its own ``dependencies.json`` (project/loop-prompt.md section 6 rule 2).

The legacy system folded its whole control plane - every prompt, validator, component, and policy
file - into one digest, so changing any of them reopened every candidate, including the ones that
never consumed the changed input. Two shapes produce such a digest, and this module rejects both
anywhere under ``src/``: a hash object accumulated across a loop, and a digest taken over a
comprehension that walks a whole control-plane collection. The sealed canary's dependency record
is held to the same rule from the other side: its keys are the per-candidate classes and nothing
that spans candidates.

Every digest in ``src/`` today is taken over one value, so "no hash accumulated in a loop" is a
bright line here. Chunked hashing of a single large file would take the same shape; if a work item
ever needs it, this rule gains a narrow exemption for that call and keeps its bite everywhere else,
rather than being deleted.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from pathlib import Path

from support import REPO_ROOT

SOURCE_ROOT = REPO_ROOT / "src/repository_presenter"
SEALED_CANARY = (
    REPO_ROOT
    / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "65b1f577c0f16d0d9112bb6c1153d3024543ac02"
)
# The dependency classes a candidate records; each names the earliest state its change reopens.
PER_CANDIDATE_CLASSES = frozenset(
    {
        "schema_version",
        "source",
        "facts",
        "prompts",
        "components",
        "validators",
        "validator_version",
        "policy",
        "contract_version",
        "acceptance_profile_version",
        "protected_content_fingerprint",
    }
)
# Identifier tokens that name a whole control-plane set rather than one candidate's own inputs.
CONTROL_PLANE_TOKENS = frozenset(
    {
        "catalog",
        "check",
        "checks",
        "component",
        "components",
        "config",
        "manifest",
        "manifests",
        "model",
        "models",
        "policies",
        "policy",
        "prompt",
        "prompts",
        "registry",
        "schema",
        "schemas",
        "settings",
        "validator",
        "validators",
    }
)
_HASH_CONSTRUCTORS = frozenset({"blake2b", "blake2s", "md5", "new", "sha1", "sha256", "sha512"})


def _is_digest_call(node: ast.AST) -> bool:
    """Whether the node constructs a hash: ``hashlib.sha256(...)`` or a local ``_sha256(...)``."""
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute):
        return node.func.attr in _HASH_CONSTRUCTORS
    if isinstance(node.func, ast.Name):
        return node.func.id.lstrip("_") in _HASH_CONSTRUCTORS
    return False


def _tokens(node: ast.AST) -> set[str]:
    """Every identifier token an expression mentions, split on underscores and lowercased."""
    found: set[str] = set()
    for child in ast.walk(node):
        name = None
        if isinstance(child, ast.Name):
            name = child.id
        elif isinstance(child, ast.Attribute):
            name = child.attr
        if name:
            found.update(part for part in name.lower().split("_") if part)
    return found


def _iterated_tokens(node: ast.AST) -> set[str]:
    """The identifier tokens of everything a loop or comprehension inside this subtree walks."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.comprehension | ast.For | ast.AsyncFor):
            found |= _tokens(child.iter)
    return found


def _accumulated_digests(tree: ast.Module) -> list[tuple[int, str]]:
    """Hash objects created empty and fed inside a loop: the classic whole-set digest."""
    accumulators = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and _is_digest_call(node.value)
        for target in node.targets
        if isinstance(target, ast.Name) and not getattr(node.value, "args", None)
    }
    if not accumulators:
        return []
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
            continue
        body: Iterable[ast.AST] = (
            node.body if isinstance(node, ast.For | ast.AsyncFor) else [node.iter]
        )
        for statement in body:
            for call in ast.walk(statement):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "update"
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id in accumulators
                ):
                    found.append(
                        (
                            call.lineno,
                            f"the hash {call.func.value.id} is accumulated inside a loop, "
                            "which digests a whole set into one value",
                        )
                    )
    return found


def _assignments(scope: ast.AST) -> dict[str, list[ast.AST]]:
    """What each plain name in this scope was assigned, so a digest built across statements
    is read as the expression it actually digests."""
    found: dict[str, list[ast.AST]] = {}
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found.setdefault(target.id, []).append(node.value)
    return found


def _scopes(tree: ast.Module) -> list[ast.AST]:
    return [
        tree,
        *(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)),
    ]


def _set_wide_digests(tree: ast.Module) -> list[tuple[int, str]]:
    """Digests taken over a whole control-plane collection, directly or through one local name."""
    module_names = _assignments(tree)
    found: list[tuple[int, str]] = []
    for scope in _scopes(tree):
        local = {**module_names, **_assignments(scope)}
        for node in ast.walk(scope):
            if not _is_digest_call(node):
                continue
            walked = _iterated_tokens(node)
            for name in {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}:
                for value in local.get(name, []):
                    walked |= _iterated_tokens(value)
            named = walked & CONTROL_PLANE_TOKENS
            if named:
                found.append(
                    (
                        node.lineno,
                        f"the digest folds over the control plane ({', '.join(sorted(named))}), "
                        "so changing any member would reopen candidates that never consumed it",
                    )
                )
    return found


def global_hashes(root: Path) -> list[str]:
    """Every place under ``root`` that folds a control-plane set into a single digest."""
    findings: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        anchor = REPO_ROOT if path.is_relative_to(REPO_ROOT) else root
        relative = path.relative_to(anchor).as_posix()
        # A module scope walk covers its functions, so the same call can be seen twice.
        seen = dict.fromkeys(_accumulated_digests(tree) + _set_wide_digests(tree))
        for line, reason in sorted(seen):
            findings.append(f"{relative}:{line}: {reason}")
    return findings


def test_no_module_folds_the_control_plane_into_a_single_hash() -> None:
    assert SOURCE_ROOT.is_dir(), "the source tree is where the rule applies"
    assert global_hashes(SOURCE_ROOT) == []


def test_an_accumulated_digest_over_the_prompt_set_is_flagged(tmp_path: Path) -> None:
    module = tmp_path / "control_plane.py"
    module.write_text(
        "import hashlib\n"
        "\n"
        "\n"
        "def control_plane_version(prompts):\n"
        "    digest = hashlib.sha256()\n"
        "    for manifest in prompts:\n"
        "        digest.update(manifest.read_bytes())\n"
        "    return digest.hexdigest()\n",
        encoding="utf-8",
    )
    findings = global_hashes(tmp_path)
    assert len(findings) == 1
    assert findings[0].endswith(
        "the hash digest is accumulated inside a loop, which digests a whole set into one value"
    )


def test_a_digest_folded_over_every_validator_is_flagged(tmp_path: Path) -> None:
    module = tmp_path / "fingerprint.py"
    module.write_text(
        "import hashlib\n"
        "\n"
        "\n"
        "def validators_fingerprint(validators):\n"
        '    joined = "".join(sorted(check.source for check in validators))\n'
        '    return hashlib.sha256(joined.encode("utf-8")).hexdigest()\n',
        encoding="utf-8",
    )
    findings = global_hashes(tmp_path)
    assert len(findings) == 1
    assert "the digest folds over the control plane (validators)" in findings[0]


def test_the_sealed_canary_depends_only_on_per_candidate_classes() -> None:
    # The rule from the other side: the record lists what this candidate consumed, so no key
    # can carry a value shared with candidates that consumed something else.
    record = json.loads((SEALED_CANARY / "dependencies.json").read_text(encoding="utf-8"))
    assert set(record) == PER_CANDIDATE_CLASSES

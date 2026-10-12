"""The build receipt: proof that a chain of commands ran on a clean clone, and how it travels.

A receipt records one run of one ``chain.ChainPlan`` against one revision: each step's command and
exit code, the toolchains that ran it, and whether the clone was clean. It is written next to the
correction run (``store``), and the correction path folds what it says into the *facts*
(``apply_plan``): the command facts gain the attributes ``add_dev_commands`` reads
(``ci_job_contiguous``, ``build_receipt``) or the reason they do not. That is how the proof reaches
the typed gate, which re-derives a correction from the bundle's ``facts.json`` alone.

``stable_digest`` covers only what a re-run must reproduce - repository, revision, the chain, each
command's exit code, the toolchains - never a duration or output line, so two runs of the same
chain on the same machine class carry the same ``build_receipt``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.commands import PRECONDITION_ATTRIBUTE
from repository_presenter.components.readme_correction.chain import (
    CHAIN_ATTRIBUTE,
    CI_CONTIGUOUS_ATTRIBUTE,
    CI_JOB,
    COMMAND_FACT_IDS,
    EXCLUDED_ATTRIBUTE,
    RECEIPT_ATTRIBUTE,
    RECEIPT_FAILURE_ATTRIBUTE,
    RECEIPT_PLATFORM_ATTRIBUTE,
    ChainPlan,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

EXECUTED = "EXECUTED"
FAILED = "FAILED"
TIMED_OUT = "TIMED_OUT"
NOT_VERIFIED = "NOT_VERIFIED"
RECEIPT_SCHEMA = 1
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class StepResult:
    command: str
    outcome: str  # EXECUTED, FAILED, TIMED_OUT or NOT_VERIFIED (not run)
    exit_code: int | None = None
    seconds: float = 0.0
    tail: str = ""  # the last lines of output, scrubbed of machine paths and secrets


@dataclass(frozen=True)
class Receipt:
    repository: str
    revision: str
    plan_digest: str
    outcome: str
    detail: str
    steps: tuple[StepResult, ...] = ()
    toolchain: dict[str, str] = field(default_factory=dict)
    platform: str = ""
    clean_clone: bool = True

    def stable_digest(self) -> str:
        body = {
            "schema": RECEIPT_SCHEMA,
            "repository": self.repository,
            "revision": self.revision,
            "plan": self.plan_digest,
            "outcome": self.outcome,
            "steps": [[step.command, step.exit_code] for step in self.steps],
            "toolchain": dict(sorted(self.toolchain.items())),
            "platform": self.platform,
            "clean_clone": self.clean_clone,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        document = {
            "schema_version": RECEIPT_SCHEMA,
            "kind": "build_receipt",
            "digest": self.stable_digest(),
            **asdict(self),
        }
        return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def from_json(text: str) -> Receipt:
    document = json.loads(text)
    return Receipt(
        repository=document["repository"],
        revision=document["revision"],
        plan_digest=document["plan_digest"],
        outcome=document["outcome"],
        detail=document["detail"],
        steps=tuple(StepResult(**step) for step in document["steps"]),
        toolchain=dict(document["toolchain"]),
        platform=document["platform"],
        clean_clone=bool(document["clean_clone"]),
    )


def receipt_path(directory: Path, repository: str, revision: str, plan: ChainPlan) -> Path:
    slug = _SLUG.sub("-", repository.replace("/", "__"))
    return directory / slug / f"{revision[:12]}-{plan.digest()[:12]}.json"


def load_receipt(path: Path, repository: str, revision: str, plan: ChainPlan) -> Receipt | None:
    """The stored receipt for exactly this repository, revision and chain, or ``None``: one for
    another revision or another chain proves nothing about this one."""
    try:
        receipt = from_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if (receipt.repository, receipt.revision, receipt.plan_digest) != (
        repository,
        revision,
        plan.digest(),
    ):
        return None
    return receipt


def store_receipt(path: Path, receipt: Receipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(receipt.to_json(), encoding="utf-8", newline="\n")


def _where(receipt: Receipt) -> str:
    """Where the chain ran, in words a pull request can use: the platform, or the container."""
    image = receipt.toolchain.get("container image")
    return f"Linux container {image}" if image else receipt.platform


def _summary(receipt: Receipt) -> str:
    ran = ", ".join(f"`{step.command}`" for step in receipt.steps)
    tools = ", ".join(f"{name} {version}" for name, version in sorted(receipt.toolchain.items()))
    return (
        f"ran on a clean clone of revision {receipt.revision[:12]} ({receipt.platform}"
        f"{'; ' + tools if tools else ''}): {ran}, every step exited 0; "
        f"receipt {receipt.stable_digest()[:16]}"
    )


def apply_plan(facts: FactsDocument, plan: ChainPlan, receipt: Receipt | None) -> FactsDocument:
    """``facts`` with the chain's findings on the build and test command facts.

    * a command the chain leaves out carries ``chain_excluded`` (the reason);
    * a command in the chain carries ``command_chain`` (and ``ci_job_contiguous`` for a CI job),
      its setup lines as ``precondition`` (so the block prints exactly what was run), and either
      ``build_receipt`` (the receipt's digest, with a line of evidence saying what ran) or
      ``build_receipt_failed`` (why there is none).

    The facts stay SUPPORTED: they are true of the clone; what the attributes withhold is the
    right to print them."""
    reasons = {item.fact_id: item.reason for item in plan.excluded}
    updated: list[Fact] = []
    for fact in facts.facts:
        if fact.id not in COMMAND_FACT_IDS or fact.polarity != "SUPPORTED":
            updated.append(fact)
            continue
        attributes = dict(fact.attributes or {})
        evidence = fact.evidence
        if fact.id in reasons:
            attributes[EXCLUDED_ATTRIBUTE] = reasons[fact.id]
        elif fact.id in plan.included:
            attributes[CHAIN_ATTRIBUTE] = plan.kind
            if plan.kind == CI_JOB:
                attributes[CI_CONTIGUOUS_ATTRIBUTE] = "true"
            setup = plan.setup_before(fact.id)
            if setup:
                attributes[PRECONDITION_ATTRIBUTE] = "\n".join(setup)
            else:
                attributes.pop(PRECONDITION_ATTRIBUTE, None)
            if receipt is None:
                attributes[RECEIPT_FAILURE_ATTRIBUTE] = (
                    "NOT_RUN: the chain has not been run on a clean clone"
                )
            elif receipt.outcome == EXECUTED:
                attributes[RECEIPT_ATTRIBUTE] = receipt.stable_digest()
                attributes[RECEIPT_PLATFORM_ATTRIBUTE] = _where(receipt)
                evidence = (*evidence, Evidence(evidence[0].path, _summary(receipt)))
            else:
                attributes[RECEIPT_FAILURE_ATTRIBUTE] = f"{receipt.outcome}: {receipt.detail}"
        updated.append(replace(fact, evidence=evidence, attributes=attributes))
    return FactsDocument(
        facts.repository, facts.source_revision, tuple(updated), facts.schema_version
    )

"""Which README code blocks are examples to verify: fenced blocks in the ecosystem's language."""

from __future__ import annotations

from repository_presenter.components.readme.evidence.facts.inherited import inventory_units
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.examples import ExampleCandidate


def _fence_parts(source: str) -> tuple[str, str] | None:
    """The info string and body of a fenced block, or ``None`` for an indented block."""
    lines = source.splitlines()
    if len(lines) < 2 or not lines[0].startswith(("```", "~~~")):
        return None
    fence = lines[0][:3]
    info = lines[0][3:].strip().split()
    language = info[0].lower() if info else ""
    body = lines[1:-1] if lines[-1].strip().startswith(fence) else lines[1:]
    return language, "\n".join(body) + "\n"


def select_examples(
    readme_path: str, readme_bytes: bytes, ecosystem: str
) -> list[ExampleCandidate]:
    """Every fenced code block of the README whose language belongs to ``ecosystem``."""
    # The spec owns the fence vocabulary. A table here knew only Python, so a ```csharp block
    # was not an example at all and the whole .NET cohort found zero candidates
    # (measured 2026-09-06; section 29.2 F6).
    aliases = spec_for(ecosystem).example_fences
    candidates: list[ExampleCandidate] = []
    text = readme_bytes.decode("utf-8", errors="replace")
    for unit in inventory_units(text):
        if unit.unit_type != "code_block":
            continue
        parts = _fence_parts(unit.source)
        if parts is None or parts[0] not in aliases or not parts[1].strip():
            continue
        candidates.append(
            ExampleCandidate(
                ordinal=len(candidates) + 1,
                language=parts[0],
                code=parts[1],
                source_path=readme_path,
                start_line=unit.start_line,
                end_line=unit.end_line,
                unit_id=f"inherited_unit:{unit.ordinal:03d}.code_block",
            )
        )
    return candidates

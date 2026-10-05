"""Which README code blocks are examples to verify: fenced blocks in the ecosystem's language."""

from __future__ import annotations

from repository_presenter.components.readme.evidence.facts.inherited import inventory_units
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.examples import ExampleCandidate, collapse_blank_runs


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


def _normalized_body(code: str) -> str:
    """``code`` with blank lines and trailing whitespace collapsed, so two fenced blocks that
    demonstrate the identical thing are recognised as the same example even when the upstream
    README repeats it with only incidental reformatting between the two occurrences.

    Measured live on ``aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`` at revision
    ``bb3c67d17884ce130870e7a510c611ee66c6c8ae``: two fenced blocks - one the README's own
    "Export a PDF page to SVG, PNG, HTML, Markdown, and DOCX" walkthrough, the other a second,
    later occurrence of the exact same code differing only by one blank line after the
    ``import`` - were both admitted as distinct ``SUPPORTED`` ``example`` facts (``example:001``
    and ``example:093``). Presentation planning's own completeness backstop
    (``composition/planning.py::_missing_additional_examples``) then placed both into
    ``additional_example_ids`` since neither disposition ever cited the second one, and
    authoring correctly wrote the identical task heading for both, since the code is the same
    demonstration - ``BC-07`` rejects the resulting reused heading with no ``section_id``, so
    repair has nothing to route it to (``repair/rounds.py``'s "no failing check names an
    LLM-owned section" backstop, `repairs.json` `"outcome": "unrepairable"`). The defect's
    earliest causal stage is here: two fenced blocks should never mint two separate ``example``
    facts for what is, modulo formatting, the same demonstration.
    """
    return "\n".join(line.rstrip() for line in code.splitlines() if line.strip())


def select_examples(
    readme_path: str, readme_bytes: bytes, ecosystem: str
) -> list[ExampleCandidate]:
    """Every fenced code block of the README whose language belongs to ``ecosystem``, once each.

    A second fenced block that repeats an earlier one's demonstration verbatim (modulo blank
    lines and trailing whitespace) is not selected again - see ``_normalized_body``. The unit
    itself is untouched: ``evidence/facts/inherited.py``'s own, separate inventory pass still
    carries it, so it still receives its own disposition; it is simply never minted as a second,
    redundant ``example`` fact of its own.
    """
    # The spec owns the fence vocabulary. A table here knew only Python, so a ```csharp block
    # was not an example at all and the whole .NET cohort found zero candidates
    # (measured 2026-09-06; section 29.2 F6).
    aliases = spec_for(ecosystem).example_fences
    candidates: list[ExampleCandidate] = []
    seen_bodies: set[str] = set()
    text = readme_bytes.decode("utf-8", errors="replace")
    for unit in inventory_units(text):
        if unit.unit_type != "code_block":
            continue
        parts = _fence_parts(unit.source)
        if parts is None or parts[0] not in aliases or not parts[1].strip():
            continue
        normalized = _normalized_body(parts[1])
        if normalized in seen_bodies:
            continue
        seen_bodies.add(normalized)
        candidates.append(
            ExampleCandidate(
                ordinal=len(candidates) + 1,
                language=parts[0],
                code=collapse_blank_runs(parts[1]),
                source_path=readme_path,
                start_line=unit.start_line,
                end_line=unit.end_line,
                unit_id=f"inherited_unit:{unit.ordinal:03d}.code_block",
            )
        )
    return candidates

"""The third, narrower ask of a twice-rejected job, as a plain value.

``Narrowing`` is data and callables only. It lives apart from ``jobs.py`` (which sends the
requests and so imports the openai SDK through the transport) so that a component that merely
builds a ``Narrowing`` - ``reconciliation/dispositions.py`` is also read by the deterministic
README correction path - does not load a model client by importing it
(``tests/components/readme_correction/test_engine.py``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Narrowing:
    """A third, narrower ask for the part of a twice-rejected reply that is still wrong.

    The universal re-ask returns the whole reply, and a reply that fixes what it was told so often
    breaks or keeps one other unit that the job fails (wave 3: nine of thirty-six repositories
    ended at "output rejected twice", six of them with one or two units left). A ``Narrowing``
    lets a job name those units and ask for them alone, keeping the rest exactly as the second
    reply gave it.

    ``pending(content, rejection)`` names the parts of the second reply still wrong (unit IDs,
    slots); empty when none can be named, and nothing is then asked. ``ask(parts, content,
    rejection, repeated)`` is the narrowed packet and call schema (the same prompt, narrowed to
    ``parts``, with the defects of ``rejection`` that concern them). ``merge(content, narrowed,
    parts)`` is the whole reply with ``parts`` taken from the narrowed reply. The merged reply is
    judged by the job's ordinary schema, binding and checks, so nothing is accepted unjudged.
    ``subject`` completes the failure message ("... a narrowed ask for the silent units").

    ``repeated(first, second, parts)`` names the ``parts`` the second reply gave exactly as the
    first did. The re-ask carried the complete defect list and the model answered it with the same
    units, so asking for them again with the same defects would be a third equivalent attempt
    (AGENTS.md "Implementation Discipline"; wave 4: Slides-Java and Slides-Cpp returned the same
    text a third time). ``ask`` is handed those parts as its last argument so that the narrowed
    request changes the evidence - it says the earlier text was returned twice and rejected twice -
    instead of repeating the question. ``None`` for a job whose narrowed ask already shows the
    model what the re-ask did not (the silent units of a ``unit_ids`` job)."""

    pending: Callable[[str, Sequence[str]], list[str]]
    ask: Callable[
        [Sequence[str], str, Sequence[str], Sequence[str]],
        tuple[Mapping[str, Any], dict[str, Any] | None],
    ]
    merge: Callable[[str, str, Sequence[str]], str]
    subject: str = "the silent units"
    repeated: Callable[[str, str, Sequence[str]], list[str]] | None = None

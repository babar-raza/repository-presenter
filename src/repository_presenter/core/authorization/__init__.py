"""Effect-authorization contracts (``docs/REPOSITORY_LAYOUT.md``'s ``core/authorization/``).

Typed, deterministic structures that bind an exact effect to the evidence it was minted from -
never an LLM output, never inferred from credential presence, per ``AGENTS.md``'s agentic/
deterministic boundary and "Security and Effects" sections. ``proposal.py`` is the first contract
here, for G6-W02's README-proposal PR effect.
"""

from __future__ import annotations

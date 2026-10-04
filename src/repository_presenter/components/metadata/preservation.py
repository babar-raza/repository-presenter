"""Deterministic rules deciding when a repository's existing GitHub metadata may be replaced, and
which existing topics may be removed (plans/idea.md, Central Agent: "preventing automated product
updates from replacing strong content with generic or inconsistent text").

The default is **preserve**. A maintainer-authored value is replaced only when one rule below
proves it weak, and every verdict names the rule that fired, so a proposal and an apply can be
audited. No LLM is consulted anywhere here (AGENTS.md "Agentic and Deterministic Boundary": this is
a deterministic gate, not editorial judgment).

Weak description - replaced (first matching rule wins):

``empty``
    ``None`` or whitespace only.
``placeholder``
    A known placeholder: GitHub's auto-text ("Contribute to <repo> development by creating an
    account on GitHub"), or a phrase from ``_PLACEHOLDER_PHRASES`` ("work in progress", ...).
``bare_name_or_filler``
    Every word is either a word of the repository's own ``owner/name`` or filler that carries no
    product information (``_FILLER``: articles, "description", "project", "test", "library", ...).
    "Aspose.3D FOSS for Python" and "Old description." are weak; "Reads and writes STL files" has
    content words, so it is not.
``contradicted_by_verified_platform``
    Names a platform from ``_PLATFORM_DESCRIPTION_PATTERNS`` but not the registry-verified
    ``identity:platform`` of this repository (e.g. says ".NET" on the Python repository). Mentioning
    the verified platform alongside another one ("Python bindings for a Java engine") is not a
    contradiction.

Anything else is ``maintainer-authored`` and kept, even if the sealed README suggests different
wording; the differing suggestion stays visible in the proposal as advisory text.

Weak homepage - replaced: ``empty``; ``invalid_url`` (not an ``http(s)`` URL with a dotted host);
``reserved_placeholder_host`` (``example.com``/``.org``/``.net``, ``*.example``, ``*.test``,
``*.invalid``, ``localhost``); ``self_reference`` (the repository's own ``github.com`` page, which
GitHub already shows). A live site of any other kind is maintainer-authored and kept.

Topics are never replaced. ``merge_topics`` keeps every existing topic and appends verified
additions; an existing topic is removed only when ``justified_topic_removals`` finds that it names a
platform other than the registry-verified ``identity:platform`` fact, which is then cited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit

MAINTAINER_AUTHORED: Final = "maintainer-authored"
GITHUB_TOPIC_LIMIT: Final = 20  # GitHub's own cap on topics per repository

_TOKEN = re.compile(r"[a-z0-9]+")

_PLACEHOLDER_PHRASES: Final = frozenset(
    {
        "work in progress",
        "coming soon",
        "under construction",
        "lorem ipsum dolor sit amet",
        "no description provided",
        "add a description",
        "short description",
        "project description",
        "first commit",
        "initial commit",
        "my first repository",
        "my first repo",
    }
)
_GITHUB_AUTOTEXT = re.compile(r"^contribute to .+ development by creating an account on github\.?$")

# Words that carry no product information. Deliberately small and generic; a description with even
# one word outside this set and outside the repository's own name is treated as real content.
_FILLER: Final = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "for",
        "and",
        "or",
        "to",
        "in",
        "on",
        "is",
        "this",
        "my",
        "our",
        "new",
        "old",
        "stale",
        "outdated",
        "description",
        "desc",
        "repo",
        "repository",
        "project",
        "test",
        "testing",
        "sample",
        "example",
        "placeholder",
        "todo",
        "tbd",
        "wip",
        "default",
        "readme",
        "untitled",
        "empty",
        "none",
        "null",
        "na",
        "lorem",
        "ipsum",
        "initial",
        "commit",
        "first",
        "add",
        "no",
        "provided",
        "short",
        "github",
        "foss",
        "free",
        "open",
        "source",
        "library",
        "lib",
        "package",
        "module",
        "sdk",
        "api",
        "tool",
        "tools",
        "software",
        "code",
    }
)

# Canonical registry ``platform`` value -> patterns for a description naming that platform.
_PLATFORM_DESCRIPTION_PATTERNS: Final[dict[str, tuple[re.Pattern[str], ...]]] = {
    "python": (re.compile(r"(?<![\w])python(?![\w])"), re.compile(r"(?<![\w])pypi(?![\w])")),
    "net": (
        re.compile(r"(?<![\w])\.net(?![\w])"),
        re.compile(r"(?<![\w])dotnet(?![\w])"),
        re.compile(r"(?<![\w])c#"),
        re.compile(r"(?<![\w])nuget(?![\w])"),
    ),
    "java": (re.compile(r"(?<![\w])java(?![\w])"),),
    "cpp": (re.compile(r"(?<![\w])c\+\+"), re.compile(r"(?<![\w])cpp(?![\w])")),
    "typescript": (
        re.compile(r"(?<![\w])typescript(?![\w])"),
        re.compile(r"(?<![\w])node\.?js(?![\w])"),
    ),
    "go": (re.compile(r"(?<![\w])golang(?![\w])"),),
    "rust": (re.compile(r"(?<![\w])rust(?![\w])"),),
}

# Canonical platform -> GitHub topic slugs that name it.
_PLATFORM_TOPIC_SLUGS: Final[dict[str, frozenset[str]]] = {
    "python": frozenset({"python"}),
    "net": frozenset({"dotnet", "net", "csharp"}),
    "java": frozenset({"java"}),
    "cpp": frozenset({"cpp", "c-plus-plus"}),
    "typescript": frozenset({"typescript"}),
    "go": frozenset({"go", "golang"}),
    "rust": frozenset({"rust"}),
}


@dataclass(frozen=True)
class Verdict:
    """``weak`` with the ``rule`` that proved it, or ``maintainer-authored`` (``weak`` false)."""

    weak: bool
    rule: str


@dataclass(frozen=True)
class TopicRemoval:
    """An existing topic removed, and the verified fact that justifies it."""

    topic: str
    fact_id: str
    fact_value: str
    reason: str


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _normalized(text: str) -> str:
    return " ".join(_tokens(text))


def _platform_mentions(description: str) -> set[str]:
    lowered = description.lower()
    return {
        platform
        for platform, patterns in _PLATFORM_DESCRIPTION_PATTERNS.items()
        if any(pattern.search(lowered) for pattern in patterns)
    }


def assess_description(
    observed: str | None, repository: str, verified_platform: str | None
) -> Verdict:
    """Is ``observed`` weak enough to replace? ``repository`` is ``owner/name``;
    ``verified_platform`` the SUPPORTED ``identity:platform`` fact value, or ``None``."""
    if observed is None or not observed.strip():
        return Verdict(True, "empty")
    normalized = _normalized(observed)
    if normalized in _PLACEHOLDER_PHRASES or _GITHUB_AUTOTEXT.match(observed.strip().lower()):
        return Verdict(True, "placeholder")
    words = _tokens(observed)
    repository_words = set(_tokens(repository))
    if not words or all(word in repository_words or word in _FILLER for word in words):
        return Verdict(True, "bare_name_or_filler")
    platform = (verified_platform or "").strip().lower()
    mentions = _platform_mentions(observed)
    if platform in _PLATFORM_DESCRIPTION_PATTERNS and mentions and platform not in mentions:
        return Verdict(True, "contradicted_by_verified_platform")
    return Verdict(False, MAINTAINER_AUTHORED)


_RESERVED_HOST = re.compile(
    r"^(localhost|(.+\.)?example(\.(com|org|net))?|(.+\.)?(test|invalid|localhost))$"
)


def assess_homepage(observed: str | None, repository: str) -> Verdict:
    """Is ``observed`` weak enough to replace? ``repository`` is ``owner/name``."""
    if observed is None or not observed.strip():
        return Verdict(True, "empty")
    try:
        parts = urlsplit(observed.strip())
        host = (parts.hostname or "").lower()
    except ValueError:
        return Verdict(True, "invalid_url")
    if parts.scheme not in ("http", "https") or ("." not in host and host != "localhost"):
        return Verdict(True, "invalid_url")
    if _RESERVED_HOST.match(host):
        return Verdict(True, "reserved_placeholder_host")
    if host in ("github.com", "www.github.com"):
        segments = [s for s in parts.path.lower().split("/") if s]
        if segments == repository.lower().split("/"):
            return Verdict(True, "self_reference")
    return Verdict(False, MAINTAINER_AUTHORED)


def merge_topics(existing: tuple[str, ...], additions: tuple[str, ...]) -> tuple[str, ...]:
    """Existing topics first, in their order (never reordered, never dropped here), then each
    verified addition not already present, up to GitHub's cap. Existing topics are never truncated
    to make room; if they already fill the cap, nothing is added."""
    merged = list(dict.fromkeys(existing))
    for topic in additions:
        if topic not in merged and len(merged) < GITHUB_TOPIC_LIMIT:
            merged.append(topic)
    return tuple(merged)


def justified_topic_removals(
    existing: tuple[str, ...], platform_fact_id: str | None, verified_platform: str | None
) -> tuple[TopicRemoval, ...]:
    """The only removal rule: an existing topic that names a platform other than the registry-
    verified one (e.g. ``java`` on the Python repository), citing the platform fact. No verified
    platform, or one this module has no topic table for, justifies no removal."""
    platform = (verified_platform or "").strip().lower()
    if platform_fact_id is None or platform not in _PLATFORM_TOPIC_SLUGS:
        return ()
    own = _PLATFORM_TOPIC_SLUGS[platform]
    removals: list[TopicRemoval] = []
    for topic in dict.fromkeys(existing):
        if topic in own:
            continue
        for other, slugs in _PLATFORM_TOPIC_SLUGS.items():
            if other != platform and topic in slugs:
                removals.append(
                    TopicRemoval(
                        topic=topic,
                        fact_id=platform_fact_id,
                        fact_value=platform,
                        reason=(
                            f"names platform {other!r}, but {platform_fact_id} "
                            f"verifies {platform!r}"
                        ),
                    )
                )
                break
    return tuple(removals)

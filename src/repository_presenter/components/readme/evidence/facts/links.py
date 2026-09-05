"""Link targets of the existing README, each resolved and recorded as a fact.

External links get one bounded HTTP request each (HEAD, then GET when HEAD is refused), retried
only on transient failures; anchors are checked against the README's own headings; relative
paths against the tree inventory. A link that resolves is SUPPORTED, one that is gone is
CONTRADICTED, and one that cannot be checked is UNRESOLVED, never assumed.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal
from urllib.parse import unquote, urlsplit

import httpx
from markdown_it import MarkdownIt
from markdown_it.token import Token

from repository_presenter.core.facts import Evidence, Fact, Polarity, fact_id
from repository_presenter.core.probes import ProbeRecord
from repository_presenter.core.retry import RetryableOperationError, run_with_retry

LinkKind = Literal["external", "anchor", "relative", "mailto", "other"]
LinkOutcome = Literal["RESOLVED", "MISSING", "UNCHECKED"]
REQUEST_TIMEOUT_SECONDS = 15.0
USER_AGENT = "repository-presenter (+https://github.com/babar-raza/repository-presenter)"
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
_HEAD_REFUSED_STATUSES = frozenset({403, 405, 501})
_ACCESS_GATED_STATUSES = frozenset({401, 403})
_SLUG_STRIP = re.compile(r"[^\w\- ]")
_POLARITY: dict[LinkOutcome, Polarity] = {
    "RESOLVED": "SUPPORTED",
    "MISSING": "CONTRADICTED",
    "UNCHECKED": "UNRESOLVED",
}


@dataclass(frozen=True)
class LinkTarget:
    """One distinct link of the README, at its first occurrence."""

    ordinal: int
    href: str
    kind: LinkKind
    line: int
    text: str


@dataclass(frozen=True)
class LinkResult:
    outcome: LinkOutcome
    detail: str
    # What the read cost and what it returned, for the probe record; a local check has neither.
    status: int | None = None
    elapsed_ms: int | None = None


def _classify(href: str) -> LinkKind:
    lowered = href.lower()
    if lowered.startswith(("http://", "https://")):
        return "external"
    if lowered.startswith("mailto:"):
        return "mailto"
    if href.startswith("#"):
        return "anchor"
    if "://" in href or lowered.startswith(("javascript:", "data:", "tel:")):
        return "other"
    return "relative"


def _attr(token: Token, name: str) -> str:
    value = token.attrGet(name)
    return "" if value is None else str(value)


def _inline_links(inline: Token, line: int, found: list[tuple[str, int, str]]) -> None:
    children = inline.children or []
    index = 0
    while index < len(children):
        child = children[index]
        if child.type == "image":
            found.append((_attr(child, "src"), line, child.content))
        elif child.type == "link_open":
            href = _attr(child, "href")
            text_parts: list[str] = []
            index += 1
            while index < len(children) and children[index].type != "link_close":
                inner = children[index]
                if inner.type == "image":
                    found.append((_attr(inner, "src"), line, inner.content))
                    text_parts.append(inner.content)
                elif inner.type in {"text", "code_inline"}:
                    text_parts.append(inner.content)
                index += 1
            found.append((href, line, "".join(text_parts).strip()))
        index += 1


def extract_links(readme_text: str) -> list[LinkTarget]:
    """Every distinct link or image target in document order, with its line and link text."""
    tokens = MarkdownIt("commonmark").enable(["table", "strikethrough"]).parse(readme_text)
    found: list[tuple[str, int, str]] = []
    line = 1
    for token in tokens:
        if token.map is not None:
            line = token.map[0] + 1
        if token.type == "inline":
            _inline_links(token, line, found)
    targets: list[LinkTarget] = []
    seen: set[str] = set()
    for href, at_line, text in found:
        if not href or href in seen:
            continue
        seen.add(href)
        targets.append(LinkTarget(len(targets) + 1, href, _classify(href), at_line, text))
    return targets


def heading_slug(text: str) -> str:
    """GitHub's anchor form of a heading: lowercase, punctuation dropped, spaces to hyphens."""
    return _SLUG_STRIP.sub("", text.strip().lower()).replace(" ", "-")


def heading_slugs(readme_text: str) -> set[str]:
    tokens = MarkdownIt("commonmark").parse(readme_text)
    slugs: set[str] = set()
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            slugs.add(heading_slug(tokens[index + 1].content))
    return slugs


def fetch_status(url: str) -> tuple[int, str]:
    """HEAD then GET if refused; the final status and URL after redirects."""
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = client.head(url)
        if response.status_code in _HEAD_REFUSED_STATUSES:
            with client.stream("GET", url) as streamed:
                return streamed.status_code, str(streamed.url)
        return response.status_code, str(response.url)


def check_external(
    href: str,
    *,
    fetch: Callable[[str], tuple[int, str]] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> LinkResult:
    """Resolve one external link, retrying transient failures under the link_check policy."""
    fetcher = fetch or fetch_status

    def attempt() -> tuple[int, str]:
        try:
            status, final = fetcher(href)
        except httpx.TransportError as exc:
            raise RetryableOperationError(f"{type(exc).__name__}: {exc}") from exc
        if status in _TRANSIENT_STATUSES:
            raise RetryableOperationError(f"HTTP {status}")
        return status, final

    started = time.monotonic()

    def since_start() -> int:
        return int((time.monotonic() - started) * 1000)

    try:
        status, final = run_with_retry("link_check", attempt, sleep=sleep or time.sleep)
    except RetryableOperationError as exc:
        return LinkResult("UNCHECKED", f"unreachable: {exc}", elapsed_ms=since_start())
    elapsed = since_start()
    redirected = f" via {final}" if final != href else ""
    if 200 <= status < 300:
        return LinkResult("RESOLVED", f"HTTP {status}{redirected}", status, elapsed)
    if status in _ACCESS_GATED_STATUSES:
        return LinkResult("UNCHECKED", f"HTTP {status} (access-gated){redirected}", status, elapsed)
    return LinkResult("MISSING", f"HTTP {status}{redirected}", status, elapsed)


def check_relative(href: str, tree_paths: Sequence[str]) -> LinkResult:
    """A repository path (or directory) the tree inventory must contain."""
    path = unquote(urlsplit(href).path)
    while path.startswith("./"):
        path = path[2:]
    path = path.strip("/")
    if not path:
        return LinkResult("MISSING", "empty path")
    if path in tree_paths or any(entry.startswith(path + "/") for entry in tree_paths):
        return LinkResult("RESOLVED", f"tree contains {path}")
    return LinkResult("MISSING", f"tree does not contain {path}")


# The anchor text an existing README gave a link, recorded in the fact's evidence by the
# extractor that read it.
_LINK_TEXT = re.compile(r"text '(.*)'$")


def link_text(fact: Fact) -> str:
    """The words a reader clicks: the anchor text the source gave this target, else the URL.

    The renderer prints it and the authoring packet shows it, so a unit is told what is already
    on the page rather than restating it (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC1).
    """
    for evidence in fact.evidence:
        match = _LINK_TEXT.search(evidence.detail or "")
        if match and match.group(1):
            return match.group(1)
    return fact.value


def check_anchor(href: str, slugs: set[str]) -> LinkResult:
    slug = unquote(href[1:]).lower()
    if slug in slugs:
        return LinkResult("RESOLVED", f"heading #{slug} exists")
    return LinkResult("MISSING", f"no heading #{slug}")


def link_facts(
    readme_path: str,
    readme_bytes: bytes,
    tree_paths: Sequence[str],
    *,
    fetch: Callable[[str], tuple[int, str]] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> tuple[list[Fact], list[ProbeRecord]]:
    """One ``link_target`` fact per distinct link, resolved by its kind, and one probe record
    per link read over the network.

    ``fetch`` is looked up at call time so a test's patched ``fetch_status`` always applies.
    The timing a probe record carries never reaches a fact: it differs on every run, and a fact's
    evidence is hashed (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC7).
    """
    text = readme_bytes.decode("utf-8", errors="replace")
    slugs = heading_slugs(text)
    facts: list[Fact] = []
    probes: list[ProbeRecord] = []
    for target in extract_links(text):
        if target.kind == "external":
            result = check_external(target.href, fetch=fetch, sleep=sleep)
            where = target.href
            probes.append(
                ProbeRecord(
                    "link",
                    target.href,
                    result.outcome,
                    status=result.status,
                    elapsed_ms=result.elapsed_ms,
                )
            )
        elif target.kind == "anchor":
            result = check_anchor(target.href, slugs)
            where = readme_path
        elif target.kind == "relative":
            result = check_relative(target.href, tree_paths)
            where = readme_path
        else:
            result = LinkResult("UNCHECKED", f"{target.kind} link not checked")
            where = readme_path
        label = target.text[:60] or "(no text)"
        facts.append(
            Fact(
                fact_id("link_target", f"{target.ordinal:03d}"),
                "link_target",
                target.href,
                (
                    Evidence(readme_path, f"line {target.line}; {target.kind}; text {label!r}"),
                    Evidence(where, f"{result.outcome}: {result.detail}"),
                ),
                polarity=_POLARITY[result.outcome],
                confidence=1.0 if result.outcome != "UNCHECKED" else 0.5,
            )
        )
    return facts, probes

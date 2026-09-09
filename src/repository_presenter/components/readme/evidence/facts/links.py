"""Link targets of the existing README, each resolved and recorded as a fact.

External links get one bounded HTTP request each (HEAD, then GET when HEAD is refused), retried
only on transient failures; anchors are checked against the README's own headings; relative
paths against the tree inventory. A link that resolves is SUPPORTED, one that is gone is
CONTRADICTED, and one that cannot be checked is UNRESOLVED, never assumed.

`extract_links` also discovers a target written as raw HTML - `<a href="...">text</a>` or a bare
`<img src="...">` - that markdown-it tokenizes as `html_inline` when it sits inside ordinary
paragraph prose (TB-09, external review D9, 2026-09-08: previously invisible to link checking, a
gap regex/attribute parsing closes without a new dependency). This reaches the common inline
prose case and a raw-HTML anchor wrapping a raw-HTML image (a badge/logo link), matching how
markdown-it itself tokenizes each. A tag CommonMark instead classifies as a whole `html_block` -
one occupying an entire line by itself, or wrapped in a block-level container tag like `<p>` - is
a distinct token shape this fix does not reach; no candidate in the sealed portfolio uses one
(checked directly, 2026-09-09), and closing that gap too is future work, not silently assumed
covered here.

A link target is untrusted: it is prose from a README this codebase did not write. Before every
outbound request `fetch_status` makes - the original URL and, since `follow_redirects=True`,
every hop a redirect leads to - it resolves the target host and refuses to connect if the
resolved address is loopback, link-local, or otherwise private/reserved (TB-08, external review
D8, 2026-09-08: neither check existed before this fix, so a link to a private/internal address,
directly or via a redirect, was fetched like any other). Refused the same way an access-gated
response already is: UNCHECKED, never a new outcome value, since the boundary is "we would not
ask", not "this link is broken". A host that fails to resolve at all is not refused here - there
is nothing to protect against reaching if the name resolves to nothing - and is left to fail
naturally at the transport layer, exactly as before this fix.
"""

from __future__ import annotations

import ipaddress
import re
import socket
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
# A status HEAD alone may not be believed on: the host may refuse the method (403, 405, 501) or
# answer it with 404 while serving the page perfectly well, which nuget.org does.
_HEAD_UNCONFIRMED_STATUSES = frozenset({403, 404, 405, 501})
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


_HTML_OPEN_TAG = re.compile(r"(?is)^<(a|img)\b(.*)>\s*$")
_HTML_ATTR = re.compile(r"""(?is)([a-zA-Z][\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")


def _html_attrs(attrs_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, double, single, bare in _HTML_ATTR.findall(attrs_text):
        values[name.lower()] = double or single or bare
    return values


def _html_tag(html: str) -> tuple[str, dict[str, str]] | None:
    """(tag name, attributes) of a raw HTML fragment's own opening ``<a>`` or ``<img>`` tag, or
    None for anything else - a closing tag, or an unrelated element. A narrow regex, not a
    general HTML parse: the one shape a README's raw HTML ever needs for a link target."""
    match = _HTML_OPEN_TAG.match(html.strip())
    if match is None:
        return None
    return match.group(1).lower(), _html_attrs(match.group(2))


def _is_html_close(token: Token, name: str) -> bool:
    return token.type == "html_inline" and token.content.strip().lower() == f"</{name}>"


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
        elif child.type == "html_inline":
            # TB-09, D9: a target only ever written as raw HTML - `<a href="...">text</a>` or a
            # bare `<img src="...">` - is invisible to the CommonMark-native cases above, which
            # markdown-it tokenizes as `html_inline`, never `link_open`/`image`.
            tag = _html_tag(child.content)
            if tag is None:
                pass
            elif tag[0] == "img":
                found.append((tag[1].get("src", ""), line, tag[1].get("alt", "")))
            else:  # tag[0] == "a"
                href = tag[1].get("href", "")
                text_parts = []
                index += 1
                while index < len(children) and not _is_html_close(children[index], "a"):
                    inner = children[index]
                    if inner.type == "image":
                        found.append((_attr(inner, "src"), line, inner.content))
                        text_parts.append(inner.content)
                    elif inner.type in {"text", "code_inline"}:
                        text_parts.append(inner.content)
                    elif inner.type == "html_inline":
                        inner_tag = _html_tag(inner.content)
                        if inner_tag is not None and inner_tag[0] == "img":
                            found.append(
                                (inner_tag[1].get("src", ""), line, inner_tag[1].get("alt", ""))
                            )
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


class PrivateAddressError(Exception):
    """A link target resolved to a loopback, link-local, or otherwise private/reserved address."""


def _is_private_address(raw: str) -> bool:
    address = ipaddress.ip_address(raw)
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _reject_private_targets(request: httpx.Request) -> None:
    """An ``httpx`` request event hook: fires for the original request and, since
    ``fetch_status`` follows redirects, for every hop - so a redirect to a private address is
    caught exactly like a direct link to one."""
    host = request.url.host
    try:
        resolved = {str(info[4][0]) for info in socket.getaddrinfo(host, None)}
    except OSError:
        return
    private = {ip for ip in resolved if _is_private_address(ip)}
    if private:
        raise PrivateAddressError(f"{host} resolves to a private/reserved address ({private!r})")


def fetch_status(url: str) -> tuple[int, str]:
    """HEAD, then GET whenever HEAD's answer would condemn the link.

    HEAD is an optimisation, and a negative verdict has to come from the method a reader would
    actually use. Measured 2026-09-06: `https://www.nuget.org/packages/Aspose.3D.FOSS/` answers
    HEAD with 404 and GET with 200, so BC-06 called the NuGet badge's own target missing and
    failed the whole Aspose.3D candidate at EXTRACTING. Confirming costs one extra request only
    where the first answer was already a failure.
    """
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        event_hooks={"request": [_reject_private_targets]},
    ) as client:
        response = client.head(url)
        if response.status_code in _HEAD_UNCONFIRMED_STATUSES:
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
    except PrivateAddressError as exc:
        # Never retried: a private/reserved address does not become a public one by asking
        # again (TB-08, external review D8, 2026-09-08).
        return LinkResult("UNCHECKED", f"rejected: {exc}", elapsed_ms=since_start())
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

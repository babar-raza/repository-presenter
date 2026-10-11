"""Doc-comment text: inline markup resolved to what a reader sees, a summary with a hole refused.

A public symbol's description is the first sentence of its own documentation, and that sentence
reaches the API Reference table verbatim. Three defects put a visible gap in it, measured by the
independent acceptance review of the wave-3 reseal (f69f75c7, 2026-10-11):

1. The vendored C# reader mishandles inline XML tags it meets: ``<see langword="null"/>`` and
   ``<seealso cref=.../>`` vanish, ``<see cref="X">label</see>`` loses its separator ("Xlabel"),
   and ``cref="M:Ns.Type.Method(System.Int32)"`` reads "Int32)". The vendored engine is never
   edited (``tests/test_vendor_boundary.py``), so :func:`normalise_source_docs` rewrites the
   doc-comment lines of the source the engine is handed - line for line, so every line number the
   engine reports is unchanged - and the engine then reads text with no markup left to mishandle.
   The same pass ends a C# summary at ``</summary>`` (a summary with no final period otherwise
   ran into the ``<param>`` text below it) and resolves ``{@link X}`` inside a JSDoc/TSDoc block.
2. The upstream comment itself has a hole: Aspose.3D for .NET ships "Base class for  and",
   "The  contains the transformation matrix for a bone node" and 40 more, written after an
   editor stripped each ``<see cref>`` and left its separators behind. Nothing in the repository
   can say which words went missing, so :func:`doc_defect` recognises the shapes a lost word
   leaves (a double space inside a sentence, a sentence ending on a word that cannot end one, a
   copula with no subject, an unresolved tag) and :func:`usable_doc` returns nothing for them.
   A symbol without a usable summary is an undocumented symbol: a type is described from its
   verified signature, a member is not described at all (README_CONTRACT.md row 14).
3. The vendored engine cuts a summary that has no sentence-ending punctuation at 200 characters,
   mid-word ("... a knot vector The w component in co"). A cut is recognised the same way.

The checks are structural and language-neutral; they read no fact and decide nothing about
whether a sentence is true.
"""

from __future__ import annotations

import re
from dataclasses import replace

from repository_presenter.core.facts import Fact

# --- inline markup --------------------------------------------------------------------------

_ATTRIBUTE = re.compile(r"""([A-Za-z_:][\w:.-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_GENERIC_ARGUMENTS = re.compile(r"\{[^{}]*\}|`+\d*")
_PARAMETER_LIST = re.compile(r"\(.*\)\s*$")
_REFERENCE_PREFIX = re.compile(r"^[A-Za-z]:")


def reference_name(reference: str) -> str:
    """The name a reader recognises in a code reference: ``M:Ns.Type.Run(System.Int32)`` reads
    ``Run``, ``List{T}`` reads ``List``, ``Type#member`` (Javadoc/JSDoc) reads ``member``, and a
    constructor reads as its type."""
    text = _REFERENCE_PREFIX.sub("", reference.strip())
    text = _PARAMETER_LIST.sub("", text)
    while True:
        stripped = _GENERIC_ARGUMENTS.sub("", text)
        if stripped == text:
            break
        text = stripped
    parts = [part for part in re.split(r"[.#:]+", text) if part]
    if parts and parts[-1].lstrip("#") in {"ctor", "cctor"} and len(parts) > 1:
        return parts[-2]
    return parts[-1] if parts else ""


def _attribute(attributes: str, name: str) -> str:
    for found in _ATTRIBUTE.finditer(attributes):
        if found.group(1).lower() == name:
            return (found.group(2) if found.group(2) is not None else found.group(3)) or ""
    return ""


def _reference(match: re.Match[str]) -> str:
    """The visible text of one ``<see>``/``<seealso>``: its own text, else what it refers to."""
    attributes = match.group("attrs") or ""
    own = " ".join((match.group("body") or "").split())
    if own:
        return own
    cref = _attribute(attributes, "cref")
    if cref:
        return reference_name(cref)
    return _attribute(attributes, "langword") or _attribute(attributes, "href")


_XML_REFERENCE = re.compile(
    r"<(?P<tag>seealso|see)\b(?P<attrs>[^<>]*?)\s*"
    r"(?:/>|>(?P<body>(?:(?!</?(?:see|seealso)\b).)*?)</(?P=tag)\s*>|>)",
    re.IGNORECASE | re.DOTALL,
)
_XML_NAMED = re.compile(r"<(?:paramref|typeparamref)\b(?P<attrs>[^<>]*?)\s*/?>", re.IGNORECASE)
_JS_INLINE = re.compile(
    r"\{@(?P<tag>link|linkcode|linkplain|code|literal|value)\b(?P<arg>[^{}]*)\}"
)
_JS_EMPTY = re.compile(r"\{@(?:inheritDoc|docRoot)\s*\}")
_RST_ROLE = re.compile(r":(?:[A-Za-z_]+:)?[A-Za-z_]+:`(?P<target>[^`]+)`")


def resolve_xml_inline(text: str) -> str:
    """``text`` with every XML-doc inline reference replaced by its visible text, never by nothing.

    ``<see cref="X"/>`` reads the name ``X`` refers to, ``<see cref="X">label</see>`` reads
    ``label``, ``<see langword="null"/>`` reads ``null``, ``<paramref name="p"/>`` reads ``p``.
    Presentation tags (``<c>``, ``<para>``) are left for the engine, which keeps their content.
    """
    text = _XML_REFERENCE.sub(_reference, text)
    return _XML_NAMED.sub(lambda m: _attribute(m.group("attrs"), "name"), text)


def _jsdoc_inline(match: re.Match[str]) -> str:
    argument = match.group("arg").strip()
    if match.group("tag") in {"code", "literal", "value"}:
        return argument
    if "|" in argument:
        target, _, label = argument.partition("|")
    else:
        target, _, label = argument.partition(" ")
    label = label.strip()
    if label:
        return label
    target = target.strip()
    return (
        target
        if re.match(r"[a-z][a-z0-9+.-]*://", target, re.IGNORECASE)
        else (target.replace("#", ".").lstrip("."))
    )


def resolve_jsdoc_inline(text: str) -> str:
    """``text`` with every ``{@link X}`` family tag replaced by its label or its target."""
    return _JS_INLINE.sub(_jsdoc_inline, _JS_EMPTY.sub("", text))


def resolve_rst_roles(text: str) -> str:
    """``text`` with every Sphinx role (``:class:`~pkg.Foo```) replaced by the name it shows."""

    def role(match: re.Match[str]) -> str:
        target = match.group("target").strip()
        titled = re.fullmatch(r"(?P<title>.+?)\s*<(?P<ref>[^<>]+)>", target)
        if titled:
            return titled.group("title").strip()
        if target.startswith("~"):
            return target.lstrip("~").rsplit(".", 1)[-1]
        return target.lstrip("!")

    return _RST_ROLE.sub(role, text)


# --- the source the engine reads ------------------------------------------------------------


def _split_eol(line: str) -> tuple[str, str]:
    body = line.rstrip("\r\n")
    return body, line[len(body) :]


def _visible(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text).strip()


def _csharp_block(block: list[str]) -> list[str]:
    """One run of ``///`` lines: inline tags resolved, the summary closed, the rest blanked."""
    prefixes: list[str] = []
    bodies: list[str] = []
    endings: list[str] = []
    for line in block:
        body, ending = _split_eol(line)
        prefix = body[: body.index("///") + 3]
        prefixes.append(prefix)
        bodies.append(resolve_xml_inline(body[len(prefix) :]))
        endings.append(ending)
    closing = next((i for i, body in enumerate(bodies) if "</summary>" in body.lower()), None)
    if closing is not None:
        position = bodies[closing].lower().index("</summary>")
        head, tail = bodies[closing][:position], bodies[closing][position:]
        last = closing
        while last > 0 and not _visible(head if last == closing else bodies[last]):
            last -= 1
        text = _visible(head if last == closing else bodies[last])
        if text and text[-1] not in ".!?":
            if last == closing:
                head = head.rstrip() + "."
            else:
                bodies[last] = bodies[last].rstrip() + "."
        bodies[closing] = head + tail
        for i in range(closing + 1, len(bodies)):
            bodies[i] = ""
    return [p + b + e for p, b, e in zip(prefixes, bodies, endings, strict=True)]


def _normalise_csharp(source: str) -> str:
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("///"):
            out.append(lines[index])
            index += 1
            continue
        end = index
        while end < len(lines) and lines[end].lstrip().startswith("///"):
            end += 1
        out.extend(_csharp_block(lines[index:end]))
        index = end
    return "".join(out)


def _normalise_jsdoc(source: str) -> str:
    out: list[str] = []
    inside = False
    for line in source.splitlines(keepends=True):
        opens = not inside and "/**" in line
        if inside or opens:
            body, ending = _split_eol(line)
            line = resolve_jsdoc_inline(body) + ending
            # The comment ends on this line when a closer follows the opener (or, on a
            # continuation line, anywhere).
            tail = body[body.find("/**") + 3 :] if opens else body
            inside = "*/" not in tail
        out.append(line)
    return "".join(out)


_NORMALISERS = {
    "csharp": _normalise_csharp,
    "typescript": _normalise_jsdoc,
    "javascript": _normalise_jsdoc,
    "tsx": _normalise_jsdoc,
}


def normalise_source_docs(source: bytes, language: str) -> bytes:
    """``source`` with its doc comments' inline markup resolved, same lines, same line count.

    Only the languages whose vendored reader loses text are rewritten; every other language's
    source is returned untouched. A file that is not UTF-8 is returned untouched too.
    """
    normaliser = _NORMALISERS.get(language)
    if normaliser is None:
        return source
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return source
    return normaliser(text).encode("utf-8")


# --- a summary with a hole ------------------------------------------------------------------

# A word that cannot end a sentence: where one does, the word that completed it is gone. A
# preposition a sentence may legitimately end on ("the format it was saved in") is left out.
_DANGLING = frozenset(
    {
        *("a", "an", "the", "of", "for", "to", "and", "or", "nor", "but", "that", "which", "who"),
        *("whose", "between", "per", "via", "with", "from", "by", "is", "are", "was", "were"),
        *("be", "been", "as", "than", "if", "when", "while", "where", "into", "onto"),
    }
)
_ABBREVIATION_ENDINGS = ("e.g.", "i.e.", "vs.", "cf.", "viz.")
_DOUBLE_SPACE = re.compile(r"(?<=[\w)\]]) {2,}(?=\S)")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"(?<=\w) +[.,;:](?=\s|$)")
_LEFTOVER_MARKUP = re.compile(
    r"\{@|</?(?:see|seealso|paramref|typeparamref|c|code)\b|</?\w+\s*/>", re.IGNORECASE
)
_BLOCK_TAG = re.compile(
    r"(?:^|\s)@(?:param|returns?|throws?|exception|example|see|since|deprecated|remarks|author"
    r"|version|typeparam)\b"
)
_ORPHAN_CONTINUATION = re.compile(
    r"\b(?:the|a|an|of|to|for|and|or|with|by|in|on|is|are|that|which) (?:The|This|These)\b"
)
_SUBJECTLESS = re.compile(r"^(?:is|are|was|were|has|have|had|can|will|contains|does|do)\b")
_EMPTY_PAIR = re.compile(r"(?<=\s)(?:\(\s*\)|\[\s*\]|\"\")")
_STRANDABLE = frozenset({"to", "for", "with", "from", "by"})
_RELATIVE = re.compile(r"\b(?:that|which|whom|whose|where|what|how|who)\b", re.IGNORECASE)
# "... is anchored to.", "... belongs to.", "... is set to.": a passive or intransitive verb
# whose preposition the sentence leaves stranded on purpose.
_VERB_THEN_TO = re.compile(
    r"\b(?:\w+(?:ed|en)|belongs|refers|applies|points|corresponds|relates|responds|set|equal"
    r"|due|next|close) to$",
    re.IGNORECASE,
)
_LAST_WORD = re.compile(r"([A-Za-z']+)$")
_NAME_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_COPIED_STUB = re.compile(r"^Description copied from\b", re.IGNORECASE)
_TRAILING_COMMENT_CLOSE = re.compile(r"\s*\*?/\s*$")
_OPENED_ABBREVIATION = re.compile(r"[\s,(]*\b(?:e\.g|i\.e|vs|cf|viz)\.$", re.IGNORECASE)
_CUT_LENGTH = 190


def _name_tail(symbol: str) -> str:
    """The last word of a symbol's own name (``LastModifiedBy`` -> ``by``, ``getA`` -> ``a``).

    A description generated from a name ends on that name's last word ("Gets or sets the last
    modified by."), and that word is not a stranded one.
    """
    words = _NAME_WORDS.findall(symbol.rsplit(".", 1)[-1])
    return words[-1].lower() if words else ""


def doc_defect(text: str, symbol: str = "") -> str | None:
    """Why ``text`` cannot be quoted as the description of ``symbol``, or None when it can.

    The defects are the shapes a lost or cut word leaves; a sentence that merely reads awkwardly
    is not one.
    """
    stripped = text.strip()
    if not stripped:
        return None
    if _COPIED_STUB.match(stripped):
        return "an inherited-description stub, not a description"
    if _LEFTOVER_MARKUP.search(stripped) or _BLOCK_TAG.search(stripped):
        return "unresolved markup"
    if _DOUBLE_SPACE.search(stripped):
        return "a word is missing inside the sentence"
    if _SPACE_BEFORE_PUNCTUATION.search(stripped) or _EMPTY_PAIR.search(stripped):
        return "a word is missing before punctuation"
    if _ORPHAN_CONTINUATION.search(stripped):
        return "two sentences are joined where a word is missing"
    if _SUBJECTLESS.match(stripped):
        return "the sentence has no subject"
    core = stripped.rstrip(".!?:;, ")
    tail = _LAST_WORD.search(core)
    if tail is not None and tail.group(1).lower() in _DANGLING:
        word = tail.group(1).lower()
        # A preposition is stranded on purpose when a relative clause opened earlier is what it
        # completes ("Gets the scene that this object belongs to."), when a passive verb takes
        # it ("the cell this comment is anchored to."), or when it is the last word of the
        # symbol's own name ("Gets or sets the last modified by.").
        clause = re.split(r"[,;:]", core[: tail.start()])[-1]
        stranded = word in _STRANDABLE and (
            _RELATIVE.search(clause) is not None
            or (word == "to" and _VERB_THEN_TO.search(core) is not None)
        )
        if not stranded and word != _name_tail(symbol):
            return "the sentence ends on a word that cannot end it"
    if stripped.lower().endswith(_ABBREVIATION_ENDINGS):
        return "the sentence is cut at an abbreviation"
    if len(stripped) >= _CUT_LENGTH and stripped[-1] not in ".!?":
        return "the summary is cut mid-sentence"
    return None


def _before_block_tags(text: str) -> str:
    """``text`` up to its first ``@param``/``@return``-style block tag, as a closed sentence.

    The vendored engine hands a Javadoc or JSDoc comment over whole when its first line has no
    sentence end, so "Merge current bounding box with given point @param pt The point to merge /"
    arrives with its tags and the comment's closing slash. The description is what precedes the
    first tag.
    """
    found = _BLOCK_TAG.search(text)
    head = text[: found.start()] if found else text
    head = _TRAILING_COMMENT_CLOSE.sub("", head).strip()
    # The engine ends a sentence at the first period and space, which "(e.g. a, b)" contains: what
    # arrives is the clause before the parenthesis plus its opening, and the clause is whole.
    opened = _OPENED_ABBREVIATION.search(head)
    if opened:
        head = head[: opened.start()].rstrip()
    if (found or opened) and head and head[-1] not in ".!?":
        head += "."
    return head


def usable_doc(text: str, symbol: str = "") -> str:
    """``text`` once its inline markup is resolved, or an empty string when it has a hole."""
    resolved = resolve_rst_roles(resolve_jsdoc_inline(resolve_xml_inline(text))).strip()
    resolved = _before_block_tags(resolved)
    return "" if doc_defect(resolved, symbol) else " ".join(resolved.split())


def usable_symbol_docs(facts: list[Fact]) -> list[Fact]:
    """``facts`` with each public symbol's ``docstring`` replaced by its usable form, or dropped.

    A symbol whose summary has a hole keeps every other attribute; it simply has no documentation
    a table row may quote.
    """
    cleaned: list[Fact] = []
    for fact in facts:
        attributes = fact.attributes or {}
        original = attributes.get("docstring")
        if fact.kind != "public_symbol" or not original:
            cleaned.append(fact)
            continue
        usable = usable_doc(original, fact.value)
        if usable == original:
            cleaned.append(fact)
            continue
        kept = {key: value for key, value in attributes.items() if key != "docstring"}
        if usable:
            kept["docstring"] = usable
        cleaned.append(replace(fact, attributes=kept or None))
    return cleaned

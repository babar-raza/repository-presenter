"""Render the tables of docs/README_STANDARD.md from the data files, so prose never restates them.

The document holds blocks of the form::

    <!-- generated:NAME -->
    ...table...
    <!-- /generated:NAME -->

``render_blocks`` produces every table from ``common.yaml``, the archetypes, ``assignments.yaml``
and ``observations.yaml``; ``check_profiles`` fails when a block in the document differs from its
rendering and ``check_profiles --write-doc`` rewrites the blocks in place. An element's headline
frequency is its first listed observation.

Owner/reviewer tooling (tools/README.md): never imported by src/, never read by a product stage.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

BLOCK = re.compile(
    r"(?P<open><!-- generated:(?P<name>[a-z0-9-]+) -->)\n"
    r"(?P<body>.*?)\n?"
    r"(?P<close><!-- /generated:(?P=name) -->)",
    re.DOTALL,
)
PLACEHOLDER = re.compile(r"\{obs:([a-z0-9_]+)\}")
RULE_GROUPS = {
    "rules-prc": ("PRC", "Principles"),
    "rules-str": ("STR", "Structure and composition"),
    "rules-lnk": ("LNK", "Links"),
    "rules-ton": ("TON", "Tone"),
    "rules-det": ("DET", "Details"),
}


CODE_SPAN = re.compile(r"(`[^`]*`)")
LINE_BREAK = "@@BR@@"  # a deliberate <br> inside a cell, protected from the angle-bracket escape


def _escape_angles(text: str) -> str:
    """Outside code spans, a literal < or > must not read as an HTML tag."""
    parts = CODE_SPAN.split(text)
    return "".join(
        part if index % 2 else part.replace("<", "&lt;").replace(">", "&gt;")
        for index, part in enumerate(parts)
    )


def _cell(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return _escape_angles(text).replace("|", "\\|").replace(LINE_BREAK, "<br>")


def _table(header: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def short_name(repository: str) -> str:
    """'aspose-cells-foss/Aspose.Cells-FOSS-for-.NET' -> 'Cells .NET'."""
    name = repository.split("/", 1)[1]
    match = re.match(r"^Aspose[.-](?P<family>.+?)[.-]FOSS-for-(?P<platform>.+)$", name)
    if not match:
        return name
    return f"{match['family']} {match['platform']}"


def _counts(observation_file: dict[str, Any]) -> dict[str, tuple[int, int]]:
    return {o["id"]: (o["count"], o["of"]) for o in observation_file["observations"]}


def _frequency(counts: dict[str, tuple[int, int]], ref: str) -> str:
    count, of = counts[ref]
    return f"{count}/{of}"


def elements_table(common: dict[str, Any], counts: dict[str, tuple[int, int]]) -> str:
    rows = []
    for element in sorted(common["elements"], key=lambda e: e["order"]):
        heading = f"`## {element['heading']}`" if element["heading"] else "none (see summary)"
        if element["id"] == "identity_h1":
            heading = "`# <product name>`"
        refs = element.get("observations", [])
        headline = _frequency(counts, refs[0]) if refs else "n/a"
        rows.append(
            [
                element["order"],
                f"`{element['id']}`",
                heading,
                element["structure"],
                element["requirement"]
                + (f" ({element['condition']})" if "condition" in element else ""),
                " + ".join(element["basis"]),
                headline,
                element["summary"],
            ]
        )
    return _table(
        ["#", "Element", "Heading", "Structure", "Requirement", "Basis", "Live", "What it is"], rows
    )


def rules_table(common: dict[str, Any], prefix: str) -> str:
    rows = []
    for rule in common["rules"]:
        if not rule["id"].startswith(prefix):
            continue
        rows.append(
            [
                rule["id"],
                f"`{rule['element']}`",
                " + ".join(rule["basis"]),
                rule["severity"],
                rule["statement"],
                rule["detector"],
            ]
        )
    return _table(["ID", "Element", "Basis", "Severity", "Rule", "Deterministic detector"], rows)


def defects_table(common: dict[str, Any]) -> str:
    rows = []
    for defect in common["defect_classes"]:
        repositories = ", ".join(short_name(r) for r in defect["repositories"]) or "none"
        detector = defect["detector"]
        rows.append(
            [
                defect["id"],
                defect["name"],
                f"{len(defect['repositories'])}: {repositories}",
                f"{detector['kind']}: {detector['ref']}",
                defect["correction"],
                defect.get("preserves", ""),
            ]
        )
    return _table(
        ["ID", "Defect class", "Live READMEs", "Detector", "Correction", "Preserves"], rows
    )


def decisions_table(common: dict[str, Any]) -> str:
    rows = [
        [
            d["id"],
            d["question"],
            f"owner-ruled {d['ruled']}" if d["status"] == "owner_ruled" else "open",
            d["ruling"],
            d["migration"],
            ", ".join(d.get("rules", [])),
        ]
        for d in common["decisions"]
    ]
    header = ["ID", "Question", "Status", "Ruling", "Code gate that still encodes the old rule", "Rules"]
    return _table(header, rows)


def kinds_table(common: dict[str, Any]) -> str:
    """The two kinds of structure, each with the elements of that kind."""
    rows = []
    for kind, meaning in common["structure_kinds"].items():
        members = [
            f"`{e['id']}`"
            for e in sorted(common["elements"], key=lambda e: e["order"])
            if e["structure"] == kind
        ]
        rows.append([kind, meaning, ", ".join(members)])
    return _table(["Kind", "Meaning", "Elements of this kind"], rows)


def inherited_policy_table(archetypes: dict[str, Any]) -> str:
    rows = [
        [f"`{archetype_id}`", archetypes[archetype_id]["inherited_additions"]]
        for archetype_id in sorted(archetypes)
    ]
    return _table(["Archetype", "How inherited additions are handled"], rows)


def inherited_table(assignments: dict[str, Any]) -> str:
    """Per repository, the live headings outside the twelve standard names: retained in place."""
    rows = [
        [
            short_name(entry["repository"]),
            f"`{entry['archetype']}`",
            "; ".join(entry["inherited_headings"]),
        ]
        for entry in assignments["assignments"]
        if entry.get("inherited_headings")
    ]
    header = ["Repository", "Archetype", "Live headings outside the twelve standard names"]
    return _table(header, rows)


def axes_table(common: dict[str, Any]) -> str:
    rows = [
        [f"`{axis}`", f"`{value}`", meaning]
        for axis, values in common["axes"].items()
        for value, meaning in values.items()
    ]
    return _table(["Axis", "Value", "Meaning"], rows)


def precedence_table(common: dict[str, Any]) -> str:
    rows = [[p["rank"], p["name"], p["statement"]] for p in common["precedence"]]
    return _table(["Rank", "Source", "Rule"], rows)


def archetypes_table(archetypes: dict[str, Any], assignments: dict[str, Any]) -> str:
    members = Counter(a["archetype"] for a in assignments["assignments"])
    rows = []
    for archetype_id in sorted(archetypes, key=lambda i: (-members[i], i)):
        profile = archetypes[archetype_id]
        rows.append(
            [
                f"`{archetype_id}`",
                profile["mode"],
                ", ".join(profile["install_channels"]),
                members[archetype_id],
                profile["summary"],
            ]
        )
    return _table(["Archetype", "Mode", "Install channels", "Repositories", "What it is"], rows)


def matrix_table(archetypes: dict[str, Any], common: dict[str, Any]) -> str:
    ids = sorted(archetypes)
    rows = []
    for element in sorted(common["elements"], key=lambda e: e["order"]):
        rows.append(
            [f"`{element['id']}`"] + [archetypes[a]["elements"][element["id"]] for a in ids]
        )
    return _table(["Element"] + [f"`{a}`" for a in ids], rows)


def better_table(archetypes: dict[str, Any]) -> str:
    rows = []
    for archetype_id in sorted(archetypes):
        for target in archetypes[archetype_id]["better_than_live"]:
            rows.append(
                [
                    f"`{archetype_id}`",
                    target["id"],
                    target["statement"],
                    target["measured_by"],
                    ", ".join(target.get("defect_classes", [])),
                ]
            )
    return _table(["Archetype", "ID", "Better than live means", "Measured by", "Defects"], rows)


def channel_table(archetypes: dict[str, Any]) -> str:
    rows = []
    for archetype_id in sorted(archetypes):
        variant = archetypes[archetype_id]["channel_variant"]
        rows.append(
            [
                f"`{archetype_id}`",
                "; ".join(variant["install_forms"]),
                "; ".join(variant["verification"]),
                "; ".join(variant["required_statements"]) or "none",
            ]
        )
    return _table(["Archetype", "Install forms", "Verification", "Required statements"], rows)


def assignments_table(assignments: dict[str, Any]) -> str:
    rows = []
    for entry in assignments["assignments"]:
        rows.append(
            [
                short_name(entry["repository"]),
                entry["family"],
                entry["ecosystem"],
                f"`{entry['archetype']}`",
                entry["install_channel"],
                entry["api_size_class"],
                entry["voice"],
                ", ".join(entry["surfaces"]),
                ", ".join(entry["special_structures"]) or "none",
            ]
        )
    return _table(
        [
            "Repository",
            "Family",
            "Ecosystem",
            "Archetype",
            "Channel",
            "API",
            "Voice",
            "Surfaces",
            "Special structures",
        ],
        rows,
    )


def forms_table(common: dict[str, Any]) -> str:
    rows = []
    for element in sorted(common["elements"], key=lambda e: e["order"]):
        forms = LINE_BREAK.join(f"`{f}`" for f in element.get("forms", [])) or "none observed"
        rows.append([f"`{element['id']}`", forms, element.get("preferred_form", "the live form")])
    return _table(["Element", "Forms observed", "Preferred form"], rows)


def render_blocks(
    common: dict[str, Any],
    archetypes: dict[str, Any],
    assignments: dict[str, Any],
    observation_file: dict[str, Any],
) -> dict[str, str]:
    counts = _counts(observation_file)
    blocks = {
        "precedence": precedence_table(common),
        "kinds": kinds_table(common),
        "elements": elements_table(common, counts),
        "forms": forms_table(common),
        "defects": defects_table(common),
        "decisions": decisions_table(common),
        "axes": axes_table(common),
        "archetypes": archetypes_table(archetypes, assignments),
        "matrix": matrix_table(archetypes, common),
        "channels": channel_table(archetypes),
        "better": better_table(archetypes),
        "assignments": assignments_table(assignments),
        "inherited-policy": inherited_policy_table(archetypes),
        "inherited": inherited_table(assignments),
    }
    for name, (prefix, _title) in RULE_GROUPS.items():
        blocks[name] = rules_table(common, prefix)
    # {obs:ID} in a data text is replaced by the observation's current count/of.
    return {
        name: PLACEHOLDER.sub(lambda m: _frequency(counts, m[1]), body)
        for name, body in blocks.items()
    }


def extract_blocks(text: str) -> dict[str, str]:
    """The generated blocks the document currently holds, by name."""
    return {m["name"]: m["body"].strip() for m in BLOCK.finditer(text)}


def apply_blocks(text: str, blocks: dict[str, str]) -> str:
    """The document with every generated block replaced by its rendering."""

    def replace(match: re.Match[str]) -> str:
        name = match["name"]
        if name not in blocks:
            return match.group(0)
        return f"{match['open']}\n{blocks[name]}\n{match['close']}"

    return BLOCK.sub(replace, text)

"""Validate data/readme_standard/ against its schema, the registry, the survey and the document.

    python -X utf8 -m tools.readme_standard.check_profiles            # check; exit 1 on any error
    python -X utf8 -m tools.readme_standard.check_profiles --write-counts   # refresh observations
    python -X utf8 -m tools.readme_standard.check_profiles --write-doc      # refresh the tables

What it proves (docs/README_STANDARD.md section 4 and section 8):

* every data file validates against ``schema.yaml``;
* every one of the registry's repositories is assigned to exactly one archetype, no unknown
  repository is assigned, every archetype exists and has at least one member, and each archetype
  defines every element of the common schema exactly once;
* every cross-reference (elements, rules, defect classes, observations, axes) resolves;
* the survey covers exactly the registry, and each assignment's derived axes agree with it;
* every observation's declared counts equal the counts recomputed from ``survey.json``;
* every ``N/M (obs:ID)`` frequency and ``[stat:ID=VALUE]`` statistic in README_STANDARD.md
  equals its recomputed value, and the rule, defect and decision identifiers in the document and
  in ``common.yaml`` are the same set.

Owner/reviewer tooling (tools/README.md): never imported by src/, never read by a product stage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

try:
    from tools.readme_standard import observations as obs
    from tools.readme_standard import render_tables
except ModuleNotFoundError:  # run as a script from another directory
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.readme_standard import observations as obs
    from tools.readme_standard import render_tables

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "readme_standard"
REGISTRY = REPO_ROOT / "data" / "registry.json"
DOCUMENT = REPO_ROOT / "docs" / "README_STANDARD.md"

# Rule, defect and decision identifiers: the document and common.yaml must name the same set.
ID_TOKEN = re.compile(r"\b(?:PRC|STR|LNK|TON|DET|DEF|OD)-\d{2}\b")
FREQUENCY_TAG = re.compile(r"(\d+)/(\d+) \(obs:([a-z0-9_]+)\)")
OBS_TAG = re.compile(r"\(obs:([a-z0-9_]+)\)")
PLACEHOLDER = render_tables.PLACEHOLDER
STAT_TAG = re.compile(r"\[stat:([a-z0-9_]+)=(-?[0-9]+(?:\.[0-9])?)\]")
AXES = ("install_channel", "api_size_class", "voice")
OBSERVATIONS_HEADER = (
    "# Machine-maintained: `python -X utf8 -m tools.readme_standard.check_profiles"
    " --write-counts`\n"
    "# rewrites every count and `of` from survey.json. Edit a definition (id, note, where, among)\n"
    "# by hand; never edit a count. docs/README_STANDARD.md quotes these as `N/M (obs:ID)`.\n"
)


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def size_class(api_rows: int) -> str:
    """The API size class, derived from the listed API entries: table rows, or the top-level
    member bullets when the reference has no table (docs/README_STANDARD.md section 4)."""
    if api_rows <= 0:
        return "none"
    if api_rows < 50:
        return "S"
    if api_rows < 200:
        return "M"
    if api_rows < 500:
        return "L"
    return "XL"


def _schema_errors(instance: Any, schema: dict[str, Any], name: str, label: str) -> list[str]:
    wrapper = {"$ref": f"#/$defs/{name}", "$defs": schema["$defs"]}
    validator = Draft202012Validator(wrapper)
    return [
        f"{label}: {'/'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    ]


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def observation_counts(
    definition: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> tuple[int, int]:
    return obs.count_observation(rows, definition.get("where", {}), definition.get("among", {}))


def render_observations(document: dict[str, Any], rows: dict[str, dict[str, Any]]) -> str:
    """The observations file with every count recomputed, in a stable layout."""
    refreshed = []
    for definition in document["observations"]:
        count, of = observation_counts(definition, rows)
        entry = {
            key: definition[key] for key in ("id", "note", "where", "among") if key in definition
        }
        entry["count"] = count
        entry["of"] = of
        refreshed.append(entry)
    statistics = []
    for definition in document.get("statistics", []):
        entry = {
            key: definition[key]
            for key in ("id", "note", "feature", "statistic", "among")
            if key in definition
        }
        value = obs.compute_statistic(
            rows, definition["feature"], definition["statistic"], definition.get("among")
        )
        entry["value"] = value if value is not None else 0.0
        statistics.append(entry)
    body = yaml.safe_dump(
        {
            "schema_version": 1,
            "survey": document.get("survey", "survey.json"),
            "observations": refreshed,
            "statistics": statistics,
        },
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=None,
        width=100,
    )
    return OBSERVATIONS_HEADER + body


def check(
    data_dir: Path = DATA_DIR, registry: Path = REGISTRY, document: Path | None = DOCUMENT
) -> list[str]:
    """Every problem found, as one line each; an empty list means the standard is consistent."""
    errors: list[str] = []
    schema = load_yaml(data_dir / "schema.yaml")
    common = load_yaml(data_dir / "common.yaml")
    observation_file = load_yaml(data_dir / "observations.yaml")
    assignments = load_yaml(data_dir / "assignments.yaml")
    survey = json.loads((data_dir / "survey.json").read_text(encoding="utf-8"))
    archetype_paths = sorted((data_dir / "archetypes").glob("*.yaml"))
    archetypes = {path.stem: load_yaml(path) for path in archetype_paths}

    errors += _schema_errors(common, schema, "common", "common.yaml")
    errors += _schema_errors(observation_file, schema, "observations_file", "observations.yaml")
    errors += _schema_errors(assignments, schema, "assignments_file", "assignments.yaml")
    errors += _schema_errors(survey, schema, "survey_file", "survey.json")
    for stem, profile in archetypes.items():
        errors += _schema_errors(profile, schema, "archetype", f"archetypes/{stem}.yaml")
    if errors:
        return errors  # the structural checks below assume a schema-valid shape

    entries = json.loads(registry.read_text("utf-8"))["entries"]
    registered = [e["repository"] for e in entries]
    errors += _check_assignments(assignments, archetypes, registered, survey)
    errors += _check_identity(assignments, {e["repository"]: e for e in entries})
    errors += _check_axes(schema, common)
    errors += _check_archetypes(archetypes, common)
    errors += _check_common(common, observation_file, survey, registered)
    errors += _check_observations(observation_file, survey)
    if document is not None and not errors:  # rendering assumes cross-references resolve
        rendered = render_tables.render_blocks(common, archetypes, assignments, observation_file)
        errors += _check_document(document, common, observation_file, rendered)
    return errors


def load_all(data_dir: Path) -> tuple[Any, Any, Any, Any]:
    """(common, archetypes by id, assignments, observations) as parsed from ``data_dir``."""
    archetypes = {p.stem: load_yaml(p) for p in sorted((data_dir / "archetypes").glob("*.yaml"))}
    return (
        load_yaml(data_dir / "common.yaml"),
        archetypes,
        load_yaml(data_dir / "assignments.yaml"),
        load_yaml(data_dir / "observations.yaml"),
    )


def _check_assignments(
    assignments: dict[str, Any],
    archetypes: dict[str, Any],
    registered: list[str],
    survey: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    rows = survey["rows"]
    assigned = [entry["repository"] for entry in assignments["assignments"]]
    for repository in _duplicates(assigned):
        errors.append(f"assignments.yaml: {repository} is assigned more than once")
    for repository in sorted(set(registered) - set(assigned)):
        errors.append(f"assignments.yaml: registry repository {repository} is not assigned")
    for repository in sorted(set(assigned) - set(registered)):
        errors.append(f"assignments.yaml: {repository} is not a registry repository")
    for repository in _duplicates(registered):
        errors.append(f"registry: {repository} is listed more than once")
    used = Counter(entry["archetype"] for entry in assignments["assignments"])
    for entry in assignments["assignments"]:
        repository = entry["repository"]
        if entry["archetype"] not in archetypes:
            errors.append(
                f"assignments.yaml: {repository} names unknown archetype {entry['archetype']}"
            )
        row = rows.get(repository)
        if row is None:
            continue  # reported once by the survey coverage check
        listed = int(row.get("api_rows") or row.get("api_top_level_bullets") or 0)
        derived = size_class(listed) if row.get("readme") else "none"
        if entry["api_size_class"] != derived:
            errors.append(
                f"assignments.yaml: {repository} api_size_class {entry['api_size_class']} "
                f"but survey.json lists {listed} API entries ({derived})"
            )
    for archetype_id in sorted(archetypes):
        if used[archetype_id] == 0:
            errors.append(f"archetypes/{archetype_id}.yaml: no repository is assigned to it")
        declared = archetypes[archetype_id]["id"]
        if declared != archetype_id:
            errors.append(f"archetypes/{archetype_id}.yaml: id is {declared}, not the file name")
    return errors


def _check_identity(assignments: dict[str, Any], entries: dict[str, dict[str, Any]]) -> list[str]:
    """Family and ecosystem in an assignment are the registry's, never a second opinion."""
    errors: list[str] = []
    for entry in assignments["assignments"]:
        registered = entries.get(entry["repository"])
        if registered is None:
            continue  # reported once by the coverage check
        for field in ("family", "ecosystem"):
            if entry[field] != registered[field]:
                errors.append(
                    f"assignments.yaml: {entry['repository']} {field} is {entry[field]} but the "
                    f"registry says {registered[field]}"
                )
    return errors


def _check_axes(schema: dict[str, Any], common: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    item = schema["$defs"]["assignment"]["properties"]
    for axis in AXES:
        enum = set(item[axis]["enum"])
        described = set(common["axes"].get(axis, {}))
        if enum != described:
            errors.append(
                f"common.yaml: axes.{axis} describes {sorted(described)} but schema.yaml allows "
                f"{sorted(enum)}"
            )
    for axis in ("special_structures", "surfaces"):
        enum = set(item[axis]["items"]["enum"])
        described = set(common["axes"].get(axis, {}))
        if enum != described:
            errors.append(
                f"common.yaml: axes.{axis} describes {sorted(described)} but schema.yaml allows "
                f"{sorted(enum)}"
            )
    return errors


def _check_archetypes(archetypes: dict[str, Any], common: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    elements = {element["id"] for element in common["elements"]}
    rules = {rule["id"] for rule in common["rules"]}
    defects = {defect["id"] for defect in common["defect_classes"]}
    for stem, profile in archetypes.items():
        label = f"archetypes/{stem}.yaml"
        defined = set(profile["elements"])
        for missing in sorted(elements - defined):
            errors.append(f"{label}: element {missing} has no requirement")
        for unknown in sorted(defined - elements):
            errors.append(f"{label}: unknown element {unknown}")
        for target in profile["better_than_live"]:
            for rule in target.get("rules", []):
                if rule not in rules:
                    errors.append(f"{label}: {target['id']} cites unknown rule {rule}")
            for defect in target.get("defect_classes", []):
                if defect not in defects:
                    errors.append(f"{label}: {target['id']} cites unknown defect class {defect}")
        ids = [target["id"] for target in profile["better_than_live"]]
        for duplicate in _duplicates(ids):
            errors.append(f"{label}: better_than_live id {duplicate} is repeated")
    return errors


def _check_common(
    common: dict[str, Any],
    observation_file: dict[str, Any],
    survey: dict[str, Any],
    registered: list[str],
) -> list[str]:
    errors: list[str] = []
    elements = [element["id"] for element in common["elements"]]
    rules = [rule["id"] for rule in common["rules"]]
    defects = [defect["id"] for defect in common["defect_classes"]]
    decisions = [decision["id"] for decision in common["open_decisions"]]
    observation_ids = [definition["id"] for definition in observation_file["observations"]]
    for label, ids in (
        ("element", elements),
        ("rule", rules),
        ("defect class", defects),
        ("open decision", decisions),
        ("observation", observation_ids),
    ):
        for duplicate in _duplicates(ids):
            errors.append(f"{label} id {duplicate} is defined more than once")
    known_observations = set(observation_ids)
    features = set()
    for row in survey["rows"].values():
        features.update(row)
    for element in common["elements"]:
        for ref in element.get("observations", []):
            if ref not in known_observations:
                errors.append(
                    f"common.yaml: element {element['id']} cites unknown observation {ref}"
                )
    for rule in common["rules"]:
        if rule["element"] not in set(elements) | {"document"}:
            errors.append(f"common.yaml: rule {rule['id']} names unknown element {rule['element']}")
        for ref in rule.get("observations", []):
            if ref not in known_observations:
                errors.append(f"common.yaml: rule {rule['id']} cites unknown observation {ref}")
    for defect in common["defect_classes"]:
        for repository in defect.get("repositories", []):
            if repository not in registered:
                errors.append(
                    f"common.yaml: defect {defect['id']} names unknown repository {repository}"
                )
        measure = defect.get("detector", {}).get("measure")
        if measure and measure not in features:
            errors.append(f"common.yaml: defect {defect['id']} measures unknown feature {measure}")
        where = defect.get("detector", {}).get("where")
        if where is not None:
            selected = {
                repository
                for repository, row in survey["rows"].items()
                if row.get("readme") and obs.matches(row, where)
            }
            listed = set(defect["repositories"])
            for repository in sorted(listed - selected):
                errors.append(
                    f"common.yaml: defect {defect['id']} lists {repository}, which its detector "
                    "condition does not select in survey.json"
                )
            for repository in sorted(selected - listed):
                errors.append(
                    f"common.yaml: defect {defect['id']} omits {repository}, which its detector "
                    "condition selects in survey.json"
                )
        for rule in defect.get("rules", []):
            if rule not in set(rules):
                errors.append(f"common.yaml: defect {defect['id']} cites unknown rule {rule}")
    for decision in common["open_decisions"]:
        for rule in decision.get("rules", []):
            if rule not in set(rules):
                errors.append(f"common.yaml: decision {decision['id']} cites unknown rule {rule}")
    errors += _check_bases(common, observation_file)
    for placeholder in sorted(set(PLACEHOLDER.findall(json.dumps(common)))):
        if placeholder not in known_observations:
            errors.append(f"common.yaml: {{obs:{placeholder}}} names an unknown observation")
    survey_rows = set(survey["rows"])
    for repository in sorted(set(registered) - survey_rows):
        errors.append(f"survey.json: no row for registry repository {repository}")
    for repository in sorted(survey_rows - set(registered)):
        errors.append(f"survey.json: row for {repository}, which is not a registry repository")
    return errors


def _ratio(counts: dict[str, tuple[int, int]], ref: str) -> float | None:
    """count/of of an observation, or None when it is unknown or its population is empty."""
    if ref not in counts or not counts[ref][1]:
        return None
    return counts[ref][0] / counts[ref][1]


def _is_common(count: int, of: int) -> bool:
    """At least 80 percent do, or at least 80 percent do not (a defect-prevalence measure)."""
    return of > 0 and (count / of >= 0.8 or count / of <= 0.2)


def _check_bases(common: dict[str, Any], observation_file: dict[str, Any]) -> list[str]:
    """A rule or element claiming OBSERVED_COMMON must rest on a measure that is common."""
    errors: list[str] = []
    counts = {o["id"]: (o["count"], o["of"]) for o in observation_file["observations"]}
    for element in common["elements"]:
        refs = element.get("observations", [])
        ratio = _ratio(counts, refs[0]) if refs else None
        if "OBSERVED_COMMON" in element["basis"] and not (ratio is not None and ratio >= 0.8):
            errors.append(
                f"common.yaml: element {element['id']} claims OBSERVED_COMMON but its headline "
                f"observation {refs[0] if refs else '(none)'} is below 80 percent"
            )
    for rule in common["rules"]:
        refs = [r for r in rule.get("observations", []) if r in counts]
        if "OBSERVED_COMMON" in rule["basis"] and not any(_is_common(*counts[r]) for r in refs):
            errors.append(
                f"common.yaml: rule {rule['id']} claims OBSERVED_COMMON but none of its "
                "observations is 80 percent either way"
            )
    return errors


def _check_observations(observation_file: dict[str, Any], survey: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = survey["rows"]
    for definition in observation_file["observations"]:
        count, of = observation_counts(definition, rows)
        if (definition["count"], definition["of"]) != (count, of):
            errors.append(
                f"observations.yaml: {definition['id']} declares {definition['count']}/"
                f"{definition['of']} but survey.json gives {count}/{of} "
                "(run with --write-counts after a deliberate change)"
            )
    for definition in observation_file["statistics"]:
        value = obs.compute_statistic(
            rows, definition["feature"], definition["statistic"], definition.get("among")
        )
        if value is None or abs(value - float(definition["value"])) > 0.05:
            errors.append(
                f"observations.yaml: statistic {definition['id']} declares {definition['value']} "
                f"but survey.json gives {value} (run with --write-counts after a deliberate change)"
            )
    return errors


def _check_document(
    document: Path,
    common: dict[str, Any],
    observation_file: dict[str, Any],
    rendered: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    if not document.is_file():
        return [f"{document}: the standard document does not exist"]
    text = document.read_text(encoding="utf-8").replace("\r\n", "\n")
    held = render_tables.extract_blocks(text)
    for name in sorted(set(rendered) - set(held)):
        errors.append(f"{document.name}: generated block '{name}' is missing")
    for name in sorted(set(held) - set(rendered)):
        errors.append(f"{document.name}: generated block '{name}' has no renderer")
    for name in sorted(set(held) & set(rendered)):
        if held[name] != rendered[name].strip():
            errors.append(
                f"{document.name}: generated block '{name}' is stale "
                "(run with --write-doc after a deliberate change)"
            )
    counts = {
        definition["id"]: (definition["count"], definition["of"])
        for definition in observation_file["observations"]
    }
    for match in FREQUENCY_TAG.finditer(text):
        count, of, ref = int(match.group(1)), int(match.group(2)), match.group(3)
        if ref not in counts:
            errors.append(f"{document.name}: {match.group(0)} names an unknown observation")
        elif counts[ref] != (count, of):
            errors.append(
                f"{document.name}: {match.group(0)} but observation {ref} is "
                f"{counts[ref][0]}/{counts[ref][1]}"
            )
    for match in OBS_TAG.finditer(text):
        if match.group(1) not in counts:
            errors.append(f"{document.name}: (obs:{match.group(1)}) names an unknown observation")
    values = {entry["id"]: float(entry["value"]) for entry in observation_file["statistics"]}
    for match in STAT_TAG.finditer(text):
        ref, quoted = match.group(1), float(match.group(2))
        if ref not in values:
            errors.append(f"{document.name}: {match.group(0)} names an unknown statistic")
        elif abs(values[ref] - quoted) > 0.05:
            errors.append(
                f"{document.name}: {match.group(0)} but statistic {ref} is {values[ref]:g}"
            )
    declared = {
        entry["id"]
        for key in ("rules", "defect_classes", "open_decisions")
        for entry in common[key]
    }
    used = set(ID_TOKEN.findall(text))
    for identifier in sorted(declared - used):
        errors.append(f"{document.name}: {identifier} is defined in common.yaml but never named")
    for identifier in sorted(used - declared):
        errors.append(f"{document.name}: {identifier} is named but not defined in common.yaml")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--document", type=Path, default=DOCUMENT)
    parser.add_argument(
        "--write-counts",
        action="store_true",
        help="rewrite observations.yaml with counts recomputed from survey.json, then check",
    )
    parser.add_argument(
        "--write-doc",
        action="store_true",
        help="rewrite the generated tables of README_STANDARD.md from the data files, then check",
    )
    args = parser.parse_args(argv)
    if args.write_counts:
        path = args.data_dir / "observations.yaml"
        survey = json.loads((args.data_dir / "survey.json").read_text(encoding="utf-8"))
        path.write_text(
            render_observations(load_yaml(path), survey["rows"]), encoding="utf-8", newline="\n"
        )
    if args.write_doc:
        common, archetypes, assignments, observation_file = load_all(args.data_dir)
        blocks = render_tables.render_blocks(common, archetypes, assignments, observation_file)
        text = args.document.read_text(encoding="utf-8").replace("\r\n", "\n")
        args.document.write_text(
            render_tables.apply_blocks(text, blocks), encoding="utf-8", newline="\n"
        )
    problems = check(args.data_dir, args.registry, args.document)
    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    assignments = load_yaml(args.data_dir / "assignments.yaml")["assignments"]
    observed = load_yaml(args.data_dir / "observations.yaml")["observations"]
    archetype_count = len(list((args.data_dir / "archetypes").glob("*.yaml")))
    print(
        f"OK: {len(assignments)} repositories assigned once each to {archetype_count} archetypes; "
        f"{len(observed)} observations match survey.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

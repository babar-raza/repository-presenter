"""Version and install-name claims: corrected only against the registry, never the manifest."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.validation.claims import claim_findings
from repository_presenter.components.readme_correction.detectors.claims import (
    claim_identity,
    claim_publication,
    claim_version,
)

README = """# Aspose 3D

Install it:

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

```xml
<dependency>
  <groupId>org.aspose</groupId>
  <artifactId>aspose-3d-foss</artifactId>
  <version>26.5.0</version>
</dependency>
```

```kotlin
implementation("org.aspose:aspose-3d-foss:26.5.0")
```

The `26.5.0` release predates a fix, so read the notes first.
"""


def test_stale_versions_attached_to_the_package_are_corrected(make_context: Any) -> None:
    ctx = make_context(README)
    result = claim_version(ctx)
    assert [(e.original, e.replacement) for e in result.edits] == [("26.5.0", "26.7.0")] * 3
    assert {fid for e in result.edits for fid in e.fact_ids} == {
        "package:name",
        "package:published_version",
    }
    # Each edit points at the exact characters: the unattached prose mention is untouched.
    for edit in result.edits:
        assert ctx.readme[edit.start : edit.end] == "26.5.0"
        assert "predates" not in ctx.readme[edit.start - 5 : edit.end + 5]


def test_the_corrected_text_is_clean_under_bc14(make_context: Any) -> None:
    ctx = make_context(README)
    assert any("shown at version" in f.detail for f in claim_findings(README, ctx.facts))
    fixed = README
    for edit in sorted(claim_version(ctx).edits, key=lambda e: -e.start):
        fixed = fixed[: edit.start] + edit.replacement + fixed[edit.end :]
    assert not [f for f in claim_findings(fixed, ctx.facts) if "shown at version" in f.detail]


def test_a_manifest_ahead_of_the_registry_is_never_corrected(
    make_context: Any, make_facts: Any
) -> None:
    # Aspose.Slides for Java: the tree says 26.8.0, Maven Central holds 26.7.0 (or nothing is
    # known), and the README says so. BC-14 would hold it to the manifest; a correction must not.
    readme = "```\nmvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n"
    ctx = make_context(readme, make_facts(drop=["package:published_version"]))
    assert claim_version(ctx).edits == ()


def test_a_floor_and_an_unattached_version_are_left_alone(make_context: Any) -> None:
    readme = "pip install org.aspose:aspose-3d-foss>=26.5.0\nVersion 26.5.0 added a thing.\n"
    assert claim_version(make_context(readme)).edits == ()


def test_a_correct_version_needs_no_edit(make_context: Any) -> None:
    readme = "```\nmvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n```\n"
    assert claim_version(make_context(readme)).edits == ()


def test_a_near_miss_install_name_is_corrected_and_an_unrelated_package_is_not(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("package:name", "aspose-note-foss"),
        make_fact("install_command:pip", "pip install aspose-note-foss"),
    )
    readme = "```bash\npip install aspose-note\npip install pytest\n```\n"
    ctx = make_context(readme, facts)
    edits = claim_identity(ctx).edits
    assert [(e.original, e.replacement) for e in edits] == [("aspose-note", "aspose-note-foss")]
    assert readme[edits[0].start : edits[0].end] == "aspose-note"


def test_an_unpublished_statement_is_reported_never_rewritten(make_context: Any) -> None:
    readme = "The package is not yet published on Maven Central.\n"
    result = claim_publication(make_context(readme))
    assert result.edits == ()
    assert len(result.findings) == 1 and result.findings[0].line == 1


def test_a_package_path_inside_the_module_is_not_a_near_miss(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    # Aspose.Cells for Go: `go get <module>/v26/aspose/cells_foss` installs a package of the module.
    module = "github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26"
    facts = make_facts(
        make_fact("package:name", module),
        make_fact("install_command:go", f"go get {module}"),
    )
    readme = f"```bash\ngo get {module}/aspose/cells_foss\n```\n"
    assert claim_identity(make_context(readme, facts)).edits == ()

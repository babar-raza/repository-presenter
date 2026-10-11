# README Standard

Status: normative from 2026-10-11 for how a README's structure, composition, links, tone and
detail are decided. It replaces `docs/README_CONTRACT.md` §2 as the structure and composition
standard and re-bases §8 (prose rules) on the live tone of §3.5; the code still encodes the old
table until the migration in §6 lands, so until then §2 of the contract is the legacy encoding of
what the code does, not the standard.  
Authority: the owner directive of 2026-10-11, quoted below, and `plans/idea.md` for the standing
constraints it does not amend (§1.3). Where this document and an older document disagree about how
a README should look, this document decides; where they disagree about truth, safety or effects,
`AGENTS.md` and the verified facts decide.  
Owns: the common schema (elements, order, composition, links, tone, details), the product-wise
differences schema (axes and archetypes), the improvement rules ("do better than live"), and the
migration plan. Does not own the assembly pipeline, the agentic decisions, the blocking checks, the
repair scope or the bundle layout (`docs/README_CONTRACT.md` §3 to §7, amended in §6 here), nor
build order (`docs/EXECUTION_STATE_MACHINE.md`).  
Machine-readable companions, validated by `tools/readme_standard/check_profiles.py`:
`data/readme_standard/` holds `schema.yaml`, `common.yaml` (elements, rules, defect classes, open
decisions), `archetypes/*.yaml`, `assignments.yaml` (every registry repository), `survey.json`
(the measured live READMEs) and `observations.yaml` (every frequency quoted here).

> **Owner directive, 2026-10-11.** `docs/README_CONTRACT.md` IS NOT THE STRUCTURE & COMPOSITION
> STANDARD. WE NEED TO FOLLOW THE LIVE UPSTREAM REPO README FOR EACH CASE. CORRECT THIS
> EVERYWHERE, ESPECIALLY IN README_CONTRACT.MD, SO NEXT TIME IT IS UPDATED. DEFINE A COMMON SCHEMA
> FOR OVERALL STRUCTURE AND COMPOSITION, LINKS, TONE, EVERYTHING, AND A SCHEMA FOR PRODUCT-WISE
> DIFFERENCES. WITH EVERY ITERATION WE NEED TO DO BETTER THAN WHAT IS CURRENTLY LIVE.

**Reading the numbers.** Every `N/M (obs:<id>)` and `[stat:<id>=<value>]` in this document is
recomputed from `data/readme_standard/survey.json` by the validator and fails the build when it
drifts; every table between `generated:` markers is rendered from the data files and cannot be
edited by hand.
The population is the repositories of `data/registry.json` at the survey: [stat:readme_count=42] have a
README and one has none (43 in all; the Node.js JMAP library joins as the 44th when it is admitted).
A rule carries one or more bases. **OBSERVED_COMMON** means at least 80 percent of the live
READMEs that could carry it do. **OBSERVED_VARIANT** means it is observed but below 80 percent or in
competing forms. **OWNER_RULE** means the owner stated it, in `plans/idea.md` or the directive.

## 1. Principles

### 1.1 The live README is the structural authority

The README at the default-branch head of the upstream repository is the starting point and the
authority for its own structure. The generator preserves its heading skeleton, section order,
voice, links, examples and wording. It does exactly three things to it (PRC-02):

1. **Correct** what a verified fact shows to be false, stale or broken.
2. **Add** verified information the README lacks, in the shape the portfolio already uses.
3. **Improve** where the result is measurably better (§5.1), and never where it is worse.

A candidate that does none of these is an empty patch, and an empty patch is a valid, preferred
outcome (PRC-06). For a repository that has a README a candidate is never a regeneration: the
2026-10-11 correction analysis measured regenerated candidates keeping about 40 percent of the
live lines, against 99 percent for minimal correction patches of about 12 changed lines per
repository (ten repositories; `correction-approach.md` §1 and §5 in the session scratchpad, not
part of the repository). That is the evidence behind PRC-01, not the rule itself; the rule is the
directive.

### 1.2 Precedence

When two sources disagree, the higher rank wins and the lower rank is not applied.

<!-- generated:precedence -->
| Rank | Source | Rule |
|---|---|---|
| 1 | verified truth | A fact verified at the exact upstream revision (registry answer, manifest, compiler output, the tree) beats any text, live or standard. Nothing false is kept and nothing unverified is added. |
| 2 | owner rules | Standing constraints of plans/idea.md and the 2026-10-11 directive: one factual H1, one badge row, Enterprise Edition as the only edition name, product explained before promotion, no assurance narration, no invented claims. Where a live README breaks one and a deterministic detector proves it, correct it with the smallest edit; where a rule and the live README disagree and the rule is not about truth or naming, the disagreement is an open decision and the live README stands (section 7). |
| 3 | the live README | Its heading skeleton, order, wording, voice, links, examples and tone are preserved. The standard never restructures, renames, reorders or rewrites what the maintainers wrote unless rank 1 or rank 2 forces a correction. |
| 4 | common conventions | OBSERVED_COMMON rules (at least 80 percent of the live READMEs) fill the gaps a live README leaves, in the shape the portfolio already uses. |
| 5 | variant conventions | OBSERVED_VARIANT rules apply only through the repository's archetype and axes (assignments.yaml), never as a portfolio-wide default. |
<!-- /generated:precedence -->

### 1.3 What this amends

`plans/idea.md` stays the product authority. The directive amends one sentence of it: L110 says
"the approved presentation template owns public tone, headings, organization, and formatting;
source tone and prose structure are not preservation obligations". The directive says the opposite,
so the directive governs (OD-04) and the owner may wish to edit L110. Everything else in
`plans/idea.md` stays in force as OWNER_RULE: one factual H1, one badge row, the complete canonical
product name, title-case headings, Enterprise Edition as the only edition name, product before
promotion, no assurance narration, preserved maintainer content, and the Aspose-link ceilings.

### 1.4 Principles as rules

<!-- generated:rules-prc -->
| ID | Element | Basis | Severity | Rule | Deterministic detector |
|---|---|---|---|---|---|
| PRC-01 | `document` | OWNER_RULE | blocking | The live README of the exact upstream revision is the structural authority: its heading skeleton, section order, voice and links are preserved. | NEW: skeleton diff of candidate against live (headings, levels, order); every difference carries an edit record |
| PRC-02 | `document` | OWNER_RULE | blocking | Exactly three operations are allowed: correct what is verified false, add verified information the README lacks, improve where measurably better. Anything else is not done. | NEW: edit ledger; each hunk is typed CORRECT, ADD or IMPROVE with its evidence |
| PRC-03 | `document` | OWNER_RULE | blocking | A change set is accepted only if it is a Pareto improvement over the live README on the measure vector of section 5.1: no defect count rises, no verified element is lost, and at least one measure strictly improves. | NEW: baseline-relative validation (run each BC and text predicate on live and candidate; no new failure) |
| PRC-04 | `document` | OWNER_RULE | blocking | Every edit ships with machine-reproducible evidence: compiler output, registry answer, tree path, grep line or predicate. Without it the finding becomes an issue or an advisory, not an edit. | NEW: edit ledger validation; existing facts, receipts and BC-02, BC-03, BC-14 |
| PRC-05 | `document` | OWNER_RULE | blocking | Valuable maintainer content is never removed: verified prose, examples, links, badges, limitations, capabilities, terminology and warnings stay unless a verified cause names them. | existing: BC-05 and BC-08 (extended to prose, links and badges); NEW: live-floor check |
| PRC-06 | `document` | OWNER_RULE | blocking | No change is a valid outcome. A README with no verified defect and no verified gap yields an empty patch; a cosmetic-only change never justifies a pull request. | NEW: empty-patch fast path; existing no-op proof (BC-11) |
| PRC-07 | `document` | OWNER_RULE | blocking | Only a repository with no README may be authored from scratch, from the standard skeleton and verified facts; a README or license-only placeholder returns insufficient_evidence. | existing: insufficient_evidence outcome in cli.py; NEW: greenfield gate |
| PRC-08 | `document` | OBSERVED_VARIANT + OWNER_RULE | blocking | A README that documents a source tree ahead of the published artifact says so, as Slides Java, Slides Python and Cells Go already do; the correction keeps the distinction and marks main-only features as unreleased instead of flattening to head. | NEW: published-versus-head claim model (registry versions against the tag diff) |
| PRC-09 | `document` | OWNER_RULE | blocking | The baseline of every iteration is the live README at the head the candidate is built against. A merged correction becomes the next baseline; the next iteration must beat it again or produce an empty patch, and it never reverts an accepted edit without a new verified cause. | existing: BC-01 source revision pinned; NEW: prior accepted edits kept in the ledger and checked for reversal |
<!-- /generated:rules-prc -->

## 2. Evidence: what the live portfolio is

**Population.** Aspose.GIS FOSS for .NET is the one registry repository without a README, and its
default branch carries no LICENSE either (DEF-26, DEF-07). Of the READMEs, 38/42
(obs:ten_sections_at_least_nine) carry at least nine of the ten sections of the owner's template
under their exact headings, 36/42 (obs:ten_sections_all) carry all ten, and 41/42
(obs:order_follows_standard) keep the standard headings in the standard order. The four that do
not carry the skeleton are Cells Python (a short form), Font Python (a persona and CLI pitch),
Slides .NET (a hand-written reference) and Words .NET (a provenance narrative). The live portfolio
is therefore one skeleton with a small set of deliberate departures, not 42 unrelated documents.

**The JMAP family.** The seven JMAP libraries admitted on 2026-10-11 are seven near-identical
READMEs on the full skeleton: Navigation, a Mermaid At a Glance, the three Dependencies buckets,
one Quick Start, a visible and a collapsed Additional Example, and the standard License paragraph.
They differ from the rest of the portfolio in what they lack, and each absence has one cause. No
Aspose product,
documentation or reference page exists for the family (the survey's GET of
`products.aspose.org/jmap/python/`, `docs.aspose.org/jmap/python/` and the `kb.` and `reference.`
equivalents answered 404, while the Email pages answered 200), so there is no banner, no Aspose
link, no docs trio and no Enterprise Edition paragraph, and the standard adds none (LNK-11). Their
API Reference is a prose paragraph with no listing (DEF-28), and none has published a package, which
each says in one plain sentence beside the intended package id. They need no archetype of their own:
six are `std-source` and one, C++, is `std-native`, and the `no_aspose_product_pages` structure
(§4.1) records the family condition.

**Size.** The median README is [stat:lines_median=541.0] lines of which [stat:visible_lines_median=236.5]
lie outside collapsed blocks; the longest is [stat:lines_max=4612.0] lines (PDF TypeScript). The
length is collapsed API and example material: 12/42 (obs:visible_lines_over_300) exceed the code's
300-line visible budget and 6/42 (obs:lines_over_1000) exceed 1,000 lines in total.

**How it was measured.** `tools/readme_standard/survey_features.py` turns one README into a flat
record of about 110 measures; `tools/readme_standard/build_survey.py` runs it over clones of the
registry repositories and writes `survey.json` with each repository's head commit and the SHA-256
of the committed README. The survey was captured on 2026-10-11. To re-measure after upstream
moves, clone the registry repositories read-only, run
`python -X utf8 -m tools.readme_standard.build_survey --root <clones> --captured <date>`, then
`python -X utf8 -m tools.readme_standard.check_profiles --write-counts --write-doc`, and review
the diff of the observations: a frequency that crosses the 80 percent line changes a rule's basis.

## 3. The common schema

### 3.1 Elements and order

Twenty elements make up the schema. An element's **requirement** is its default; the archetype
matrix in §4.2 refines it. `required` means present in the output (added from verified facts when
the live README lacks it); `expected` means added when verified facts are rich enough and its
absence is not a defect; `conditional` means required only when the stated condition holds;
`optional` and `preserve_only` mean kept when live and never added. (`expected` is the "typical"
tier: usual, but not a defect when absent.) The **Live** column is the element's headline
frequency among the READMEs that could carry it.

<!-- generated:elements -->
| # | Element | Heading | Requirement | Basis | Live | What it is |
|---|---|---|---|---|---|---|
| 1 | `identity_h1` | `# <product name>` | required | OBSERVED_COMMON + OWNER_RULE | 41/42 | Exactly one H1, the complete canonical product name. |
| 2 | `badge_row` | none (see summary) | required | OBSERVED_COMMON + OWNER_RULE | 42/42 | One badge paragraph under the H1; images only, each backed by a verified target. |
| 3 | `banner` | none (see summary) | optional | OBSERVED_VARIANT | 32/42 | A linked product banner between the badge row and the opening. |
| 4 | `opening` | none (see summary) | required | OBSERVED_COMMON + OWNER_RULE | 42/42 | Two to four sentences that start with the product name and say what it is and does, with its real entry-point types, before any promotion. |
| 5 | `navigation` | `## Navigation` | expected | OBSERVED_COMMON + OWNER_RULE | 39/42 | A flat list of in-page links to every H2 of the document, in document order. |
| 6 | `at_a_glance` | `## At a Glance` | expected (at least three verified core capabilities) | OBSERVED_COMMON + OWNER_RULE | 39/42 | A Mermaid flowchart: Starting Points, the product, Core Capabilities in at most two columns, Outputs; nothing else in the section. |
| 7 | `key_capabilities` | `## Key Capabilities` | required | OBSERVED_COMMON + OWNER_RULE | 38/42 | A bulleted list of what the library does, each bullet naming the real types it rests on. |
| 8 | `installation` | `## Installation` | required | OBSERVED_COMMON + OWNER_RULE | 40/42 | Every idiomatic install form of the ecosystem, then supported runtimes; when unpublished, the source install and a plain statement that no package exists. |
| 9 | `dependencies` | `## Dependencies` | expected | OBSERVED_COMMON + OWNER_RULE | 37/42 | Dependency buckets from the manifest: Required Package Dependencies, Optional Dependencies, Native and System Requirements, Development Dependencies. |
| 10 | `quick_start` | `## Quick Start` | expected (at least one example verified at this revision) | OBSERVED_COMMON + OWNER_RULE | 38/42 | One to three minimal examples that compile or run, each with a lead-in sentence. |
| 11 | `feature_showcase` | `## Feature Showcase` | optional | OBSERVED_VARIANT | 1/42 | A linked preview image of a repository-owned asset that proves a capability. |
| 12 | `additional_examples` | `## Additional Examples` | expected | OBSERVED_COMMON + OWNER_RULE | 39/42 | A lead-in, one visible flagship example, and a collapsed block of further task-named examples. |
| 13 | `project_structure` | `## Project Structure` | optional | OBSERVED_VARIANT | 4/42 | A fenced directory tree of the repository, kept current with the tree. |
| 14 | `api_reference` | `## API Reference` | expected (the repository exposes a public API) | OBSERVED_COMMON + OWNER_RULE | 39/42 | A short visible intro naming the entry-point types and the type count, then the complete public surface collapsed in a details block: Class \| Description tables and a Detailed Member Reference. |
| 15 | `docs_resources` | `## Documentation & Resources` | expected | OBSERVED_COMMON + OWNER_RULE | 39/42 | Getting started guide, How-to guides & FAQ and Full API reference on the Aspose sites, repository files that help a reader, and an Open an issue item. |
| 16 | `scope_limitations` | `## Scope and Limitations` | required | OBSERVED_COMMON + OWNER_RULE | 38/42 | Bulleted designed or declared limitations, each naming the mechanism, closed by the Enterprise Edition paragraph. |
| 17 | `enterprise_paragraph` | none (see summary) | conditional (a verified aspose.com product target exists for the family and platform) | OBSERVED_COMMON + OWNER_RULE | 30/31 | The final paragraph of Scope and Limitations: one to three sentences relating the FOSS scope to the Enterprise Edition, with one link to the verified product page. |
| 18 | `development_testing` | `## Development and Testing` | expected | OBSERVED_COMMON + OWNER_RULE | 39/42 | Build and test commands from the repository's own files, never collapsed. |
| 19 | `third_party_notices` | `## Third-Party Notices` | conditional (a third-party notices file exists in the tree) | OBSERVED_VARIANT + OWNER_RULE | 2/42 | A visible heading with a repository-relative link to the notices file. |
| 20 | `license` | `## License` | required | OBSERVED_COMMON + OWNER_RULE | 42/42 | A prose declaration of the license with a repository-relative link, never a bare link. |
<!-- /generated:elements -->

### 3.2 Composition per element

**Identity and badges.** One H1 in 41/42 (obs:h1_exactly_one), in the canonical form
`Aspose.<Family> FOSS for <Platform>` in 39/42 (obs:h1_canonical_name). The badge row is one
paragraph directly under the H1 in 42/42 (obs:badge_row_single_paragraph), median
[stat:badge_count_median=3.0] badges. What it holds varies with the product, which is why only the
license badge is common: license 39/42 (obs:badge_license), runtime floor 25/42 (obs:badge_runtime),
contributors 30/42 (obs:badge_contributors), package 21/42 (obs:badge_package), build status 9/42
(obs:badge_ci). The owner's order (package, runtime, build, license, contributors) is followed by
21/40 (obs:badge_order_ok) rows of two or more badges, so it governs added badges only (STR-04, OD-05).

**Banner.** A linked product banner sits between the badge row and the opening in 32/42
(obs:banner_present); its image is served from `products.aspose.org` in 31/32
(obs:banner_image_on_products_org) and it links to an Aspose product page in 32/32
(obs:banner_links_to_aspose). An Aspose link therefore precedes the first section in 32/42
(obs:aspose_link_before_opening), which `plans/idea.md` L79 would read as promotion before the
product is explained (OD-01). The banner is below the 80 percent line only because ten READMEs
have none: the seven JMAP READMEs, whose family has no product page to link (LNK-11), and three
off-template ones. The standard keeps a live banner exactly and never adds one (STR-05).

**Opening.** The first paragraph begins with the product name in 36/42
(obs:opening_starts_with_product), says the library is open source in 36/42
(obs:opening_free_open_source), runs two to four sentences in 38/42
(obs:opening_two_to_four_sentences), median [stat:opening_words_median=67.5] words, and names an
audience in only 3/42 (obs:opening_audience_phrase). It names the license in 15/42
(obs:opening_names_license), so a license mention is a variant, not a requirement. Three live
openings state what the library is not (PSD .NET, PSD Python and Slides .NET); that voice is kept
(`scope_forward` and `candid_handwritten`, §4.1). The opening is the maintainers' sentence; only a
false claim in it is corrected (STR-06).

**Navigation and At a Glance.** A Navigation section exists in 39/42 (obs:navigation_present),
links every H2 in 37/39 (obs:navigation_complete) and precedes At a Glance in 38/39
(obs:navigation_before_glance). At a Glance exists in 39/42 (obs:glance_present) and is a Mermaid
flowchart in 38/39 (obs:glance_mermaid) with the groups Starting Points 36/38
(obs:glance_starting_points), Core Capabilities 38/38 (obs:glance_core_capabilities) and Outputs
38/38 (obs:glance_outputs_group); the exception is an image with no text equivalent (PDF .NET,
DEF-18).

**Key Capabilities.** Present under that exact heading in 38/42 (obs:key_capabilities_present); the
other four list capabilities under another name (Features, What You Get, What it can do). The
visible bullet count has median [stat:capability_bullets_median=9.0] and maximum
[stat:capability_bullets_max=40.0]; only 16/38 (obs:capabilities_3_to_8) fall inside the legacy
three-to-eight range and 5/38 (obs:capabilities_over_12) exceed twelve, so the live count stands
(STR-09, OD-03).

**Installation and Dependencies.** Installation exists in 40/42 (obs:installation_present) and
shows a registry command in 28/40 (obs:install_registry_command), a clone-and-build path in 17/40
(obs:install_source_clone), a CMake path in 5/40 (obs:install_native_build) and a plain statement
that no package is published in 12/40 (obs:install_says_unpublished); these are the channels of §4.
Dependencies exists in 37/42 (obs:dependencies_present) with the buckets Required Package
Dependencies 37/37 (obs:deps_required_h3), Native and System Requirements 35/37
(obs:deps_native_h3), Development Dependencies 32/37 (obs:deps_development_h3) and Optional
Dependencies 5/37 (obs:deps_optional_h3); a verified-empty bucket reads "No required third-party
package dependencies." in 17/37 (obs:deps_zero_sentence). Two READMEs that carry the generated
skeleton lack Dependencies altogether (Cells .NET and Cells C++, DEF-19).

**Quick Start and examples.** Quick Start exists in 38/42 (obs:quick_start_present) and holds one
to three fenced blocks in 38/38 (obs:quick_start_one_to_three_examples). Additional Examples exists
in 39/42 (obs:additional_examples_present), sits in one collapsed block in 38/39
(obs:additional_examples_collapsed) and gives every example a task name, never a number, in 39/39
(obs:additional_examples_task_named); the median is [stat:additional_examples_median=5.0] examples.

**API Reference.** Present in 39/42 (obs:api_present). Where it lists the surface it is collapsed
and tabulated: collapsed in 32/39 (obs:api_collapsed), with a `Class | Description` table in 31/39
(obs:api_class_description_table), a Detailed Member Reference in 25/39
(obs:api_member_reference) and a stated type count in 21/39 (obs:api_states_type_count). The other
seven are the JMAP READMEs, whose API Reference is a prose paragraph naming the entry-point types
with no listing at all: 7/39 (obs:api_listing_absent), DEF-28. The summary line starts with "View"
wherever there is one (obs:api_summary_view_prefix), but the wording varies: "View the Supported
Public API Surface" is the most common at 11/39 (obs:api_summary_view_supported) and the
renderer's "View the Complete Public API Surface" appears in 1/39 (obs:api_summary_view_complete),
so the live wording is kept (STR-14). Listings range up to [stat:api_rows_max=1026.0] rows, median
[stat:api_rows_median=183.0].

**Documentation & Resources.** Present in 39/42 (obs:docs_present). Where the README links any
Aspose page the three Aspose sites are all linked in 31/32 (obs:docs_trio_when_aspose_linked); over
all READMEs with the section it is 31/39 (obs:docs_trio), because the seven JMAP READMEs list
only the issues item. The items read "Getting started guide" 30/39
(obs:docs_getting_started_guide), "How-to guides & FAQ" 28/39 (obs:docs_how_to_guides_faq) and
"Full API reference" 31/39 (obs:docs_full_api_reference); an "Open an issue" item is present in
36/39 (obs:docs_open_issue) and the issues page is linked from 41/42 (obs:issues_link). Repository
files that help a reader (PUBLISHING.md, CHANGELOG.md, docs/ guides, workflow files) are listed in
23/39 (obs:docs_repo_relative).

**Scope and Limitations and the Enterprise paragraph.** Present in 38/42 (obs:scope_present); the
median list has [stat:scope_bullets_median=6.0] bullets and the longest [stat:scope_bullets_max=68.0].
Where the README links any Aspose page the Enterprise Edition is named in the section in 30/31
(obs:enterprise_in_scope_when_aspose_linked); over all READMEs with the section it is 30/38
(obs:enterprise_in_scope), the difference being the seven JMAP READMEs (no product page to name,
LNK-11) and PDF .NET. The paragraph that names it is the last element of the section in 30/30
(obs:enterprise_closes_scope). Its wording is in §3.4.

**Development and Testing, notices and License.** Development and Testing exists in 39/42
(obs:devtest_present). License exists in 42/42 (obs:license_present), is a prose declaration
("licensed under the ...") in 39/42 (obs:license_prose), adds the sentence on MIT permissions in
38/42 (obs:license_permissions_sentence), and carries a copyright line in 2/42
(obs:license_copyright_line). A Third-Party Notices heading exists in 2/42
(obs:third_party_section); further notices are linked from the License section (Note, Cells Python,
TeX).

**Product-specific sections** are rare and each is justified by a file the repository really
carries: Project Structure 4/42 (obs:project_structure_section) and Feature Showcase 1/42
(obs:feature_showcase_section). They are preserved when live and never added (STR-25).

**Forms observed and the preferred form.** Where several forms compete the preferred form is the
live one; for an element the live README lacks, it is the first form below that the facts support.

<!-- generated:forms -->
| Element | Forms observed | Preferred form |
|---|---|---|
| `identity_h1` | `# Aspose.<Family> FOSS for <Platform>`<br>`package slug, dotted or hyphenated variants (Font, PSD .NET, PSD Python)` | # Aspose.&lt;Family&gt; FOSS for &lt;Platform&gt;, exactly as the registry names it |
| `badge_row` | `shields.io badges, one paragraph, separated by spaces or line breaks without a blank line`<br>`the GitHub Actions workflow badge for a real build status`<br>`the pkg.go.dev badge for Go` | package or release, runtime floor, build status, license, contributors, in that order, each only when its target is verified |
| `banner` | `[![Aspose.<Family> FOSS for <Platform>](https://products.aspose.org/media/<family>/<platform>/banner-readme.png)](https://products.aspose.org/<family>/<platform>/)` | preserved exactly when the live README has it; never added |
| `opening` | `<Product> is a free, open-source, MIT-licensed <language> library for <verbs> ...`<br>`negative-scope second sentence (PSD, Slides): 'It is not a renderer ...'` | the live opening, corrected only where a claim in it is false |
| `navigation` | `H2 Navigation + one bullet per H2`<br>`auto-generated nested table of contents (Cells-Go)` | flat bullet list, every H2, document order, placed after the opening |
| `at_a_glance` | `flowchart TD with subgraphs Starting Points, Core Capabilities (two nested columns), Outputs`<br>`image only (PDF .NET)` | the Mermaid topology of plans/idea.md, topology verified against facts |
| `key_capabilities` | `verb-led bullets with backticked API names, one to four lines each`<br>`bold lead-in phrase, a dash, then the detail`<br>`capability tables (Font) and 'What it can do' lists (Slides .NET, Words .NET)` | the live list; only a false or missing item is corrected or added |
| `installation` | `dotnet add package plus a PackageReference block (.NET)`<br>`Maven dependency block plus Gradle Groovy or Kotlin (Java)`<br>`pip install, quoted when versioned (Python)`<br>`go get with the versioned module path (Go)`<br>`git clone then build, editable install, or ProjectReference (source only)`<br>`CMake add_subdirectory, FetchContent or find_package, plus a NuGet package for Windows (C++)` | the live forms, each command verified against the manifest and the registry |
| `dependencies` | `H3 buckets under H2 Dependencies`<br>`'No required third-party package dependencies.' for a verified-empty bucket`<br>`a 'Requirements' table (Slides .NET)` | H3 buckets from the manifest, verified-empty stated, never omitted silently |
| `quick_start` | `one fenced example after Dependencies`<br>`two examples, create then open` | the live examples; a failing one is fixed or removed with evidence |
| `feature_showcase` | `[![alt](preview.png)](docs/showcase.pdf) between Quick Start and Additional Examples` | preserved when present, never generated |
| `additional_examples` | `<details><summary>View Additional Examples</summary> with one H3 per task` | the live examples, task-named headings, one collapsed block |
| `project_structure` | `an H2 with a language-less fenced tree and a one-line intro` | preserved; paths verified against the tree; fence language text |
| `api_reference` | `<details><summary>View the Supported Public API Surface</summary> (the most common of seven wordings)`<br>`one Class \| Description table per kind or module` | the live block; counts, rows and descriptions corrected against the symbols |
| `docs_resources` | `three bold or plain links to docs.aspose.org, kb.aspose.org, reference.aspose.org`<br>`repository-relative links to PUBLISHING.md, CHANGELOG.md, docs/ guides, workflow files` | the live list; verified Aspose targets added when missing |
| `scope_limitations` | `bullets, from two to dozens, each one limitation`<br>`bold-lead limitation bullets (PSD, Slides)` | the live bullets; a bullet the code contradicts is corrected, never silently dropped |
| `enterprise_paragraph` | `These limitations don't apply to [Aspose.<Family> for <Platform> — Enterprise Edition](url), which adds ...`<br>`These limitations apply only to <FOSS product> — they don't carry over to [..], which adds ...`<br>`For <needs>, see [..], which adds ...` | the live sentence shape; anchor and target verified against product-page facts |
| `development_testing` | `prose with fenced build and test commands, a CI matrix sentence and a release workflow link` | the live section; commands verified against the build files |
| `third_party_notices` | `an H2 Third-Party Notices (PDF Go, PDF C++)`<br>`a link from the License section (Note, Cells Python, TeX)` | link text in normal style, not code style |
| `license` | `This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.` | the live sentence; a bare link or a copyright line is corrected |
<!-- /generated:forms -->


### 3.3 Structure rules

<!-- generated:rules-str -->
| ID | Element | Basis | Severity | Rule | Deterministic detector |
|---|---|---|---|---|---|
| STR-01 | `identity_h1` | OBSERVED_COMMON + OWNER_RULE | blocking | Exactly one H1 holding the complete canonical product name; a second H1 and a package or namespace shorthand are corrected. | existing: text_checks.single_h1, BC-07, BC-12 |
| STR-02 | `badge_row` | OBSERVED_COMMON + OWNER_RULE | blocking | One badge row, one paragraph under the H1; never duplicated, split or fabricated. | existing: text_checks.single_badge_row, BC-07 |
| STR-03 | `badge_row` | OBSERVED_VARIANT | advisory | Badge contents follow the product: a license badge whenever a license file exists, a package badge only when the registry lists the package, a runtime floor from the manifest, a build badge only for a push-triggered workflow, contributors optional. A missing badge with a verified target is added; an unverified one is removed. | existing: BC-07 badge support check, evidence/facts/assets.py link_target:badge.ci |
| STR-04 | `badge_row` | OWNER_RULE | advisory | Badge order is package, runtime, build status, license, contributors. It governs badges the change adds; an existing row is reordered only when the row is already changing for another reason. | existing: BC-07 order check (to be made baseline-relative); NEW: survey_features.badge_order_ok |
| STR-05 | `banner` | OBSERVED_COMMON + OBSERVED_VARIANT | advisory | A live banner stays exactly as written; a banner is never added. Its image comes from products.aspose.org and its link from a verified product page. | existing: evidence/facts/product_pages.py banner fact; text_checks.promotion_after_product (see OD-01) |
| STR-06 | `opening` | OBSERVED_COMMON + OWNER_RULE | blocking | The opening starts with the product name and says what it is and does in two to four sentences; it names an audience or use only when a fact or the live text states it, and it carries no Aspose promotion. | existing: composition/audience.py, BC-04, BC-12; text_checks.promotion_after_product |
| STR-07 | `navigation` | OBSERVED_COMMON + OWNER_RULE | advisory | Navigation is a flat list of in-page links to every H2, in document order, after the opening and before At a Glance; a missing link is added, an existing generated TOC is kept. | NEW: nav completeness (survey_features.navigation_missing_h2) |
| STR-08 | `at_a_glance` | OBSERVED_COMMON + OWNER_RULE | blocking | At a Glance is one Mermaid chain Starting Points, product, Core Capabilities, Outputs with the topology rules of plans/idea.md; an image-only At a Glance gets a verified Mermaid diagram and keeps the image. | existing: BC-07 topology and label geometry; NEW: image_only detector |
| STR-09 | `key_capabilities` | OBSERVED_COMMON + OWNER_RULE | advisory | Key Capabilities is a bulleted list of verb-led capabilities naming the real types; the live count stands (no upper or lower bound), a capability that the code contradicts is corrected, and a verified capability the list lacks may be added. | NEW: capability claim audit against symbols, importers and exporters (DEF-06) |
| STR-10 | `installation` | OBSERVED_COMMON + OWNER_RULE | blocking | Installation shows every idiomatic form of the ecosystem, verified; when the package is not published it says so and shows the source install; a version equals the registry's current release or is marked unreleased. | existing: BC-02, BC-14 (claims.py) |
| STR-11 | `dependencies` | OBSERVED_COMMON + OWNER_RULE | blocking | In the generated skeleton Dependencies is present and built from the manifest in the four buckets, with a verified-empty bucket stated; a README with that skeleton but without the section receives it. | existing: dependency facts and the D-owned Dependencies renderer |
| STR-12 | `quick_start` | OBSERVED_COMMON + OWNER_RULE | blocking | Quick Start follows Dependencies and holds one to three examples that compile or run in isolation at the revision, each with a lead-in sentence. | existing: BC-03 example receipts |
| STR-13 | `additional_examples` | OBSERVED_COMMON + OWNER_RULE | blocking | Additional Examples keeps one visible flagship example and a single collapsed block; every example has a task-named, unique heading and a language-tagged fence. | existing: text_checks.example_headings, fences_and_spacing, BC-03 |
| STR-14 | `api_reference` | OBSERVED_COMMON + OWNER_RULE | blocking | API Reference keeps its visible intro and one collapsed block; the stated type count equals the listed rows, every listed type is public, and no description is a stock sentence. A prose-only API Reference gains the collapsed listing built from the verified public symbols, with its intro kept. | existing: public_symbol facts, validation/claims; NEW: count, internal-type and boilerplate-row detectors (survey_features.api_*) |
| STR-15 | `docs_resources` | OBSERVED_COMMON + OWNER_RULE | advisory | Documentation & Resources lists the docs, knowledge-base and reference sites, repository files that help a reader, and an issues link; every target is verified. | existing: BC-06 link resolution and ceilings (composition/link_budget.py) |
| STR-16 | `scope_limitations` | OBSERVED_COMMON + OWNER_RULE | blocking | Scope and Limitations lists the limitations the code and tests prove, each naming its mechanism; none is dropped without a verified cause and a contradicted one is corrected. | existing: BC-05, BC-08, list_coverage.py; NEW: limitation claim audit |
| STR-17 | `development_testing` | OBSERVED_COMMON + OWNER_RULE | blocking | Development and Testing is visible, never collapsed, and its commands come from the repository's build files and CI. | existing: text_checks.visible_core_sections, BC-07 |
| STR-18 | `license` | OBSERVED_COMMON + OWNER_RULE | blocking | License is a prose declaration with a repository-relative link and, for a permissive license, the permissions sentence; a bare link is corrected and a README-level copyright line is not added. | existing: text_checks.license_prose, evidence license fact |
| STR-19 | `third_party_notices` | OWNER_RULE + OBSERVED_VARIANT | blocking | When a third-party notices file exists the README links it under a visible heading or from the License section, with normal link text. | existing: text_checks.third_party_notices |
| STR-20 | `document` | OBSERVED_COMMON | advisory | The standard headings that are present keep the standard order; a section the change adds goes where the live README's neighbours place it, and an out-of-order live README is not reordered. | NEW: survey_features.standard_order_inversions |
| STR-21 | `document` | OBSERVED_COMMON + OWNER_RULE | blocking | Only secondary material is collapsed: additional examples and long API inventories; every details tag is balanced and no required section renders inside a details block. | existing: BC-07, text_checks.visible_core_sections; NEW: details balance (survey_features.unclosed_details) |
| STR-22 | `document` | OWNER_RULE | advisory | Headings use title case and canonical abbreviations in new text; a live heading is renamed only to repair a defect. Heading levels do not skip, and a bare label heading is not followed by sibling headings. | existing: BC-07 title-case check, terminology.py; NEW: survey_features.heading_level_jumps, empty_headings |
| STR-23 | `document` | OWNER_RULE | blocking | Every code fence carries its language; spacing in examples is normalized. | existing: text_checks.fences_and_spacing, BC-07 |
| STR-24 | `document` | OBSERVED_VARIANT + OWNER_RULE | advisory | Visible length may not grow except to add a required element; a live README over the visible budget is not trimmed to fit it. | existing: composition/renderer.line_counts; NEW: baseline-relative budget |
| STR-25 | `project_structure` | OBSERVED_VARIANT | advisory | Project Structure, Feature Showcase and other product-specific sections are preserved as written, their paths and assets verified against the tree, and never added to a README that lacks them. | existing: repository_files.py path facts; NEW: tree-diff of the fenced tree |
| STR-26 | `document` | OWNER_RULE | blocking | An off-template README keeps its own headings; missing standard elements are inserted next to the live heading that hosts them, under their standard name only when the live README has no equivalent. | NEW: heading-equivalence map (insertion mode) |
<!-- /generated:rules-str -->

### 3.4 Links

**The Aspose link set.** Where a README links any Aspose page, exactly five Aspose links appear in
30/34 (obs:aspose_links_exactly_five_when_aspose_linked); over all READMEs it is 30/42
(obs:aspose_links_exactly_five) because 8/42 (obs:aspose_links_none) carry none: Font and the seven
JMAP READMEs, whose family has no pages yet (LNK-11). At most five appear in 41/42
(obs:aspose_links_at_most_five); the maximum is [stat:aspose_links_max=7.0] (Words .NET). The
five are the banner and the Enterprise Edition on `products.aspose.org` and
`products.aspose.com`, and the documentation, knowledge-base and reference sites in Documentation &
Resources. They sit where they help: the banner above the opening, the three site links in
Documentation & Resources, the Enterprise link closing Scope and Limitations. A link is a ceiling,
not a target (LNK-06); a sixth is added only when a verified article explains the adjacent code.

**Link categories** (live READMEs; the first column is the position the link takes):

| Category | Target | Live |
|---|---|---|
| Banner, above the opening | the product page on `products.aspose.org` | 32/32 (obs:banner_links_to_aspose) |
| Documentation & Resources | `docs.`, `kb.` and `reference.aspose.org` for the family and platform | 31/32 (obs:docs_trio_when_aspose_linked) |
| Enterprise Edition, closing Scope and Limitations | the product page on `products.aspose.com` | 30/31 (obs:enterprise_in_scope_when_aspose_linked) |
| Repository files | PUBLISHING.md, CHANGELOG.md, docs/ guides, workflow files, LICENSE | 23/39 (obs:docs_repo_relative) |
| Issues | the repository's issues page | 41/42 (obs:issues_link) |
| Badges | registry page, workflow, LICENSE, contributors graph | 42/42 (obs:badge_row_present) |
| Forum | `forum.aspose.com` | 1/42 (obs:forum_links), removed |

**The Enterprise paragraph.** It is one to three sentences closing Scope and Limitations. Its
shape in the live portfolio:

| Shape | Opening words | Live |
|---|---|---|
| dont_apply | `These limitations don't apply to [Aspose.X for P — Enterprise Edition](url), which adds ...` | 21/30 (obs:enterprise_dont_apply) |
| apply_only | `These limitations apply only to <FOSS product> — they don't carry over to [..], which adds ...` | 4/30 (obs:enterprise_apply_only) |
| see_for | `For <needs>, see [..], which adds ...` | 4/30 (obs:enterprise_see_for) |
| other | a sentence inside another paragraph | 1/30 (obs:enterprise_other_shape) |

The anchor text is `Aspose.<Family> for <Platform> — Enterprise Edition`; none of the 30 anchors
opens "full-featured" 0/30 (obs:enterprise_full_featured_anchor), although `plans/idea.md` L109
asks for that wording and the renderer prints it (OD-02). Where the README links any Aspose page
"Enterprise Edition" appears exactly once in 29/34 (obs:enterprise_once_when_aspose_linked), and in
29/42 (obs:enterprise_once) of all READMEs; `commercial` stands in for the product or edition name in 10/42
(obs:commercial_substitute) and a banned edition name in 1/42 (obs:banned_edition_names).

**Repository-relative links.** Links to the repository's own files are relative (LNK-07); 5/42
(obs:absolute_self_blob_links) use an absolute `github.com/.../blob/main/...` URL for their own
files, and 3/42 (obs:dead_relative_links) carry a relative link whose target does not exist.
AGENTS.md is linked as a contributor guide in 17/42 (obs:agent_file_links); that is accepted, and
an assistant-specific file such as CLAUDE.md is not a user resource (LNK-10).

**Forbidden.** Forum links appear in 1/42 (obs:forum_links) and are removed (LNK-08).

<!-- generated:rules-lnk -->
| ID | Element | Basis | Severity | Rule | Deterministic detector |
|---|---|---|---|---|---|
| LNK-01 | `docs_resources` | OBSERVED_COMMON | advisory | Where the family has Aspose pages the Aspose link set is five links: the banner and the Enterprise Edition on the product site, and the docs, knowledge-base and reference sites in Documentation & Resources. | existing: composition/link_budget.py ceilings; BC-06 |
| LNK-02 | `docs_resources` | OBSERVED_COMMON + OWNER_RULE | advisory | Aspose links sit where they help: the banner above the opening (live), documentation links in Documentation & Resources or beside the code they explain, the Enterprise link closing Scope and Limitations. A link is added only when a verified target explains the adjacent material. | existing: text_checks.promotion_after_product, BC-06 |
| LNK-03 | `enterprise_paragraph` | OBSERVED_COMMON + OWNER_RULE | blocking | Enterprise Edition is the only edition name and appears once, as the anchor of the closing paragraph; commercial, On-Premise, paid and full-version wordings that refer to the aspose.com product are replaced. | existing: text_checks.edition_name, BC-06; NEW: commercial-substitute heuristic (survey_features.commercial_substitute_mentions) |
| LNK-04 | `enterprise_paragraph` | OBSERVED_COMMON + OBSERVED_VARIANT | advisory | The paragraph closes Scope and Limitations in the live sentence shape; a missing paragraph is added as 'These limitations don't apply to [Aspose.&lt;Family&gt; for &lt;Platform&gt; — Enterprise Edition](url), which adds ...' naming only what verified facts or policy state it adds. | existing: enterprise_relationship section, BC-06; NEW: shape detector (survey_features.enterprise_shape) |
| LNK-05 | `enterprise_paragraph` | OWNER_RULE | blocking | The Enterprise anchor and target name the real family and platform of the repository and resolve; a mislabeled anchor or an unresolved target is corrected from the product-page fact, never guessed. | existing: evidence/facts/product_pages.py, BC-06; NEW: anchor-platform match |
| LNK-06 | `docs_resources` | OWNER_RULE | advisory | Link density is a ceiling, never a target: no unverified, repetitive or promotional link is added to reach the usual five. | existing: composition/link_budget.py |
| LNK-07 | `document` | OBSERVED_COMMON + OWNER_RULE | advisory | Links to the repository's own files are repository-relative; an absolute github.com blob URL to the same repository is rewritten when the target exists in the tree. | NEW: survey_features.absolute_self_blob_links; existing: BC-06 |
| LNK-08 | `document` | OBSERVED_COMMON + OWNER_RULE | blocking | No forum link and no link to a promotional page that adds no reader utility. | existing: BC-06; NEW: survey_features.forum_links |
| LNK-09 | `document` | OWNER_RULE | blocking | Every link resolves; a repository-relative link to a file that does not exist is removed or retargeted with evidence, and an ellipsis in a link position is documentation text, not a link. | existing: validation/links; NEW: survey_features.dead_relative_links |
| LNK-10 | `docs_resources` | OBSERVED_VARIANT | advisory | AGENTS.md may be linked as a contributor guide; an assistant-specific file such as CLAUDE.md or a planning directory is not presented as a user resource. | NEW: survey_features.agent_file_links |
| LNK-11 | `docs_resources` | OBSERVED_VARIANT + OWNER_RULE | advisory | A README whose family has no Aspose product, documentation or reference page carries no Aspose link, banner or Enterprise Edition paragraph; they are added when the product-page fact turns verified, never inferred from the pattern of other families. | existing: evidence/facts/product_pages.py (a verified target, or none); NEW: survey_features.aspose_links_total |
<!-- /generated:rules-lnk -->

### 3.5 Tone

The live voice is declarative, third person, present tense, with the product as the subject and
imperative mood reserved for install, run and test instructions (TON-01). Measured on visible
prose (outside code, tables, headings and collapsed blocks):

- **Sentence length.** The median of the per-README mean is [stat:sentence_mean_median=19.4] words,
  the 90th percentile of sentences has median [stat:sentence_p90_median=35.0]; the means range from
  [stat:sentence_mean_min=9.5] (Cells Python) to [stat:sentence_mean_max=34.3] (PDF Go). A mean of at
  most 25 words holds in 37/42 (obs:sentence_mean_at_most_25) and of at most 30 in 41/42
  (obs:sentence_mean_at_most_30) (TON-02).
- **Register.** "free, open-source" is the standard descriptor, and none uses a word from the
  survey's lexicon of marketing superlatives: 42/42 (obs:no_marketing_superlatives) avoid it. Emoji are absent in
  39/42 (obs:no_emoji) and first-person words in 40/42 (obs:no_first_person); the exceptions are
  Words .NET, Imaging .NET and PDF TypeScript for emoji (the last is documentation of Markdown
  output) and Words .NET and Slides C++ for first person. Second person is used in 21/42
  (obs:second_person_used), in instructions and warnings.
- **Dashes.** The median README holds [stat:em_dashes_median=20.0] em dashes; they are the
  portfolio's separator in capability bullets and are left alone.
- **Candour.** Limitations name the mechanism (an exception type, an unimplemented class), and
  contractions such as "don't" are normal in the Enterprise paragraph (TON-07).
- **Terminology.** Enterprise Edition, FOSS, the product name in full, and the governed
  abbreviations (TON-08).

What is *not* tone and is never "fixed" by the generator: a hand-written voice such as the persona
pitch of Font, the sceptical measured prose of Slides .NET, or the story of Words .NET. They are
recorded as `voice` values (§4.1) and preserved (PRC-01).

<!-- generated:rules-ton -->
| ID | Element | Basis | Severity | Rule | Deterministic detector |
|---|---|---|---|---|---|
| TON-01 | `document` | OBSERVED_COMMON | advisory | Declarative third-person present tense with the product as the subject; imperative only in install, run and test instructions. | NEW: voice lexicon (survey_features.first_person_words, second_person_words) |
| TON-02 | `document` | OBSERVED_COMMON | advisory | Visible prose averages at most 25 words per sentence; new sentences stay under 40 words and a live sentence is not lengthened. | NEW: survey_features.sentence_mean, sentence_p90 |
| TON-03 | `document` | OBSERVED_COMMON | advisory | No emoji or decorative symbols in new text; a live one is left unless it breaks an anchor. | NEW: survey_features.emoji |
| TON-04 | `document` | OBSERVED_COMMON + OWNER_RULE | blocking | No first-person or agent voice, no reference to the generation process, and no assurance narration (source revisions, validators, providers, evidence). | existing: text_checks.assurance_narration, implementation_label |
| TON-05 | `document` | OBSERVED_COMMON | advisory | Factual descriptors (free, open-source, pure-Python, MIT-licensed) are the portfolio's register; marketing superlatives are not added. | NEW: survey_features.marketing_words lexicon |
| TON-06 | `document` | OBSERVED_VARIANT | advisory | Second person is acceptable in instructions and warnings; capability and limitation prose stays third-person. | NEW: survey_features.second_person_words |
| TON-07 | `scope_limitations` | OBSERVED_VARIANT | advisory | Limitations are candid and name the mechanism (an exception type, an unimplemented class); contractions such as don't are normal in the Enterprise paragraph. | existing: list_coverage.py, BC-04 (identifiers in code spans) |
| TON-08 | `document` | OWNER_RULE | advisory | Canonical terminology in new text: Enterprise Edition, FOSS, the product name in full, and governed abbreviations (PDF, XLSX, HTML, glTF, npm). | existing: composition/components/terminology.py, BC-12 |
<!-- /generated:rules-ton -->

### 3.6 Details

**Install forms by ecosystem** (observed; DET-01). .NET: `dotnet add package <Id> --version <v>`
and the matching `PackageReference` (3D, Cells, Email, PDF, Slides, Words; Imaging and PSD are
source-only). Java: a Maven `<dependency>` block and a Gradle Groovy line, with Kotlin in one
(3D, Cells, PDF, Slides). Python: `pip install <name>` where published (3D, Cells, Email, Note,
Page, Slides, Words) and `git clone` with `pip install -e .` or a path step where not (BarCode,
HTML, PDF, PSD, TeX). Go: `go get` with the major-version module path (Cells, PDF). TypeScript:
`git clone`, `npm install`, `npm run build`, because none is published (3D, Cells, PDF). Rust: a
Git dependency. C++: CMake `add_subdirectory`, `FetchContent` or `find_package`, plus a
Windows-only NuGet package (Cells, PDF, Slides; Email is CMake only).

**Dependency buckets** (DET-02). The four buckets of §3.2 come from the manifest; a library is
called "pure" or "dependency-free" only when the manifest lists no runtime dependency of that
class (Cells .NET says "pure managed code" while referencing SkiaSharp, DEF-06).

**Example execution** (DET-03). A shown example compiles or runs at the revision. Of seven live
examples the verifiers marked contradicted across ten measured repositories, four were real
defects (3D .NET, Cells .NET, Cells C++, 3D TypeScript, DEF-20) and three were not: a helper the
snippet cites (Cells Go), an undefined placeholder (Email Python) and an optional dependency (Page
Python). A contradicted example is therefore triaged, never removed by default.

**API completeness** (DET-04). Listings are the public surface of the revision. The stated count
disagrees with the listed rows in 4/21 (obs:api_count_mismatch) of the READMEs that state one, and
9/31 (obs:api_boilerplate_rows_over_20) carry more than twenty stock "Class with N methods"
descriptions (PDF C++: 182 of 244 rows).

<!-- generated:rules-det -->
| ID | Element | Basis | Severity | Rule | Deterministic detector |
|---|---|---|---|---|---|
| DET-01 | `installation` | OBSERVED_VARIANT + OWNER_RULE | blocking | Install commands match the ecosystem's forms and the manifest: quoted version specifiers, a verify line whose import path equals the package's import path, supported runtime from the manifest. | existing: BC-02, BC-14; NEW: survey_features.unquoted_pip_specifier, import-path equality |
| DET-02 | `dependencies` | OWNER_RULE | blocking | Dependency claims equal the manifest: a library is called dependency-free or pure only when the manifest lists no runtime dependency of that class. | existing: dependency snapshot; NEW: dependency claim audit |
| DET-03 | `quick_start` | OWNER_RULE | blocking | A shown example is executed or compiled at the revision. A contradicted example is triaged: an undefined placeholder, an optional dependency or a helper the snippet cites is not a defect; a real compile error is fixed with the verifier or the example is removed with the receipt. | existing: example verifiers and BC-03 receipts; NEW: triage classes |
| DET-04 | `api_reference` | OWNER_RULE | blocking | API rows come from the symbols that are public at the revision; a description is the symbol's own documentation, or the live text, or empty - never a stock sentence or an invented one. | existing: public_symbol facts, type_fallback.py; NEW: row-level audit |
| DET-05 | `document` | OWNER_RULE | blocking | A version, date or count stated in the README equals the verified fact or is marked unreleased; a statement the registry contradicts is corrected. | existing: BC-14 (validation/claims.py); NEW: count and date claims |
| DET-06 | `license` | OWNER_RULE | blocking | The license named equals the manifest and the license file; where no license file exists the README names the declared license without linking a missing file and an upstream issue handoff is raised. | existing: license fact, components/issues |
| DET-07 | `document` | OWNER_RULE | blocking | Documented commands run in a clean clone; a command that cannot (an ignored input, a missing directory) is corrected or flagged upstream. | NEW: clean-clone execution of documented commands (static first) |
<!-- /generated:rules-det -->

## 4. Product-wise differences

Every README is described by one **archetype** and five **axes**. The archetype says how the
standard applies (gap-fill inside the standard skeleton, insertion beside an off-template
structure, or greenfield authoring) and which elements it asks for; the axes record how this
product differs. Both are data, in `data/readme_standard/`.

### 4.1 Axes

<!-- generated:axes -->
| Axis | Value | Meaning |
|---|---|---|
| `install_channel` | `registry` | installed from a package registry: PyPI, NuGet, Maven Central, npm, crates.io, or the Go module proxy |
| `install_channel` | `source_only` | no registry install: clone and build, pip install -e, npm install from a clone, ProjectReference, or a Git dependency; the README says so and says when not published |
| `install_channel` | `native_build` | C++ library integrated through CMake (add_subdirectory, FetchContent, find_package), optionally with a Windows-only prebuilt NuGet package |
| `install_channel` | `none` | the README gives no install path, or no README exists |
| `api_size_class` | `none` | no API listing (no API Reference table or member list) |
| `api_size_class` | `S` | 1 to 49 listed entries; the listing is short enough to read in full |
| `api_size_class` | `M` | 50 to 199 listed entries |
| `api_size_class` | `L` | 200 to 499 listed entries |
| `api_size_class` | `XL` | 500 or more listed entries; the README is a reference document and stays collapsed |
| `voice` | `neutral_reference` | declarative third-person present tense with the product as subject; the portfolio default |
| `voice` | `scope_forward` | states in the opening what the library is not (not a renderer, not a converter) and leads the limits before the capabilities |
| `voice` | `concise_minimal` | terse imperative fragments, mean sentence under 12 words, almost no identifiers |
| `voice` | `candid_handwritten` | hand-written, sceptical and measured; states what is verified and when it was measured; sentence-case headings; steers readers to a sibling edition |
| `voice` | `narrative_marketing` | provenance story, star call to action, conversational we and you, emoji; the least conventional register in the portfolio |
| `voice` | `persona_pitch` | persona and buyer framing, workflow tables, second person, sales vocabulary; a CLI and MCP product pitch rather than a library reference |
| `surfaces` | `library` | a public API consumed from code |
| `surfaces` | `cli` | a command-line interface documented in the README |
| `surfaces` | `mcp` | an MCP server or MCP tool handlers documented in the README |
| `special_structures` | `project_structure` | an H2 Project Structure with a fenced directory tree |
| `special_structures` | `feature_showcase` | an H2 Feature Showcase with a linked preview image |
| `special_structures` | `third_party_notices_section` | an H2 Third-Party Notices |
| `special_structures` | `license_notices_link` | the License section links a notices or font-license file |
| `special_structures` | `format_matrix` | a table of formats against capabilities or load and save support |
| `special_structures` | `choosing_edition` | an H2 or H3 comparing the FOSS editions of one family |
| `special_structures` | `result_images` | screenshots of example output |
| `special_structures` | `image_glance` | At a Glance as an image instead of a Mermaid diagram |
| `special_structures` | `maturity_notice` | a stated pre-release maturity (alpha, pre-alpha, pre-release) |
| `special_structures` | `install_warning` | a bold warning in Installation that the published artifact differs from the source tree or carries a known security fix |
| `special_structures` | `extra_reference_sections` | H2 sections beyond the standard set that hold reference material |
| `special_structures` | `collapsed_capability_reference` | a collapsed block that extends Key Capabilities or Scope |
| `special_structures` | `persona_tables` | persona, workflow or buyer tables in place of capability bullets |
| `special_structures` | `provenance_story` | a section telling where the code came from |
| `special_structures` | `cli_reference` | command-line usage documented as its own section |
| `special_structures` | `mcp_section` | an H2 documenting an MCP server |
| `special_structures` | `no_aspose_product_pages` | the family has no Aspose product, documentation or reference pages yet, so the README carries no Aspose link, banner or Enterprise Edition paragraph (LNK-11) |
<!-- /generated:axes -->

`api_size_class` is derived, not asserted: the validator derives it from the listed API entries in
`survey.json` and fails when `assignments.yaml` disagrees. The other axes are judgments recorded
beside the evidence in each assignment's notes.

### 4.2 Archetypes

<!-- generated:archetypes -->
| Archetype | Mode | Install channels | Repositories | What it is |
|---|---|---|---|---|
| `std-source` | gap_fill | source_only | 17 | The generated ten-section skeleton for a library with no registry install: the reader clones and builds, installs editable, runs npm install from a clone, or adds a ProjectReference or Git dependency. The README says plainly that no package is published and what to do instead. |
| `std-registry` | gap_fill | registry | 16 | The generated ten-section skeleton with Navigation and Additional Examples, for a library the reader installs from PyPI, NuGet, Maven Central or the Go module proxy. The live README has the skeleton; the work is correction, gap-filling and measurable improvement inside it. |
| `std-native` | gap_fill | native_build | 5 | The generated ten-section skeleton for a C++ library the reader integrates through CMake (add_subdirectory, FetchContent, find_package), sometimes with a Windows-only prebuilt NuGet package. Installation is the longest section of the portfolio and its toolchain floors are part of Dependencies. |
| `offtemplate` | insertion | registry, none | 4 | A README that does not use the generated skeleton: a terse short form (Cells Python), a persona and CLI pitch (Font), a candid hand-written reference (Slides .NET) or a provenance narrative (Words .NET). Its structure and voice are the authority; the standard only inserts verified elements the README lacks and corrects what is false, beside the README's own headings. |
| `greenfield` | greenfield | none | 1 | The default branch has no README, so there is no live structure to follow. The standard skeleton is authored from verified facts only, or the transaction records insufficient_evidence when the tree carries no public surface to describe. |
<!-- /generated:archetypes -->

What each archetype asks of each element:

<!-- generated:matrix -->
| Element | `greenfield` | `offtemplate` | `std-native` | `std-registry` | `std-source` |
|---|---|---|---|---|---|
| `identity_h1` | required | required | required | required | required |
| `badge_row` | required | expected | required | required | required |
| `banner` | optional | preserve_only | preserve_only | preserve_only | preserve_only |
| `opening` | required | required | required | required | required |
| `navigation` | required | optional | required | required | required |
| `at_a_glance` | conditional | optional | expected | expected | expected |
| `key_capabilities` | required | required | required | required | required |
| `installation` | required | required | required | required | required |
| `dependencies` | required | expected | required | required | required |
| `quick_start` | conditional | expected | expected | expected | expected |
| `feature_showcase` | not_applicable | preserve_only | preserve_only | preserve_only | preserve_only |
| `additional_examples` | conditional | optional | expected | expected | expected |
| `project_structure` | not_applicable | preserve_only | preserve_only | preserve_only | preserve_only |
| `api_reference` | conditional | expected | required | required | required |
| `docs_resources` | conditional | expected | expected | expected | expected |
| `scope_limitations` | required | required | required | required | required |
| `enterprise_paragraph` | conditional | conditional | conditional | conditional | conditional |
| `development_testing` | conditional | expected | expected | expected | expected |
| `third_party_notices` | conditional | conditional | conditional | conditional | conditional |
| `license` | conditional | required | required | required | required |
<!-- /generated:matrix -->

Install-channel variants:

<!-- generated:channels -->
| Archetype | Install forms | Verification | Required statements |
|---|---|---|---|
| `greenfield` | the verified source build of the tree, with its receipt | every command carries a build receipt (BC-02); every claim maps to an accepted fact (BC-04) | that no package is published, when the registry shows none |
| `offtemplate` | registry: the live install line, verified (pip install aspose-cells-foss; dotnet add package Aspose.Slides.FOSS; dotnet add package Aspose.Words.FOSS); none: no install section is invented for an unpublished package (Font); the MCP extra the README shows stays as written | package name and version against the registry (BC-02, BC-14); the README's own statements agree with each other (Words .NET installs by NuGet and says the package is landing soon) | the publication state when the live README contradicts itself |
| `std-native` | CMake add_subdirectory with target_link_libraries against the exported target; find_package(&lt;Package&gt; CONFIG REQUIRED) against the installed package; FetchContent_Declare with a pinned tag, not a branch; NuGet package or release archive for Windows, stating which toolsets and platforms it covers; cmake configure, build and ctest commands with the preset or generator the repository uses | exported target and package names equal the CMakeLists; the pinned tag or version equals the manifest or the release; the Windows-only claim equals the package contents (BC-02 receipt) | the C++ standard and the minimum CMake version; which install forms work on which platforms |
| `std-registry` | .NET: dotnet add package &lt;Id&gt; --version &lt;registry latest&gt;, then the PackageReference block; Java: Maven dependency block with the registry's latest version, Gradle Groovy or Kotlin line; Python: pip install &lt;name&gt; (quoted when versioned), then a one-line import verification; Go: go get &lt;module path with major-version suffix&gt;, plus the aliased import line; Python, .NET, Java: the supported runtime from the manifest in one sentence | package name equals the package identity fact (BC-02); version equals the registry's current stable release, or the statement says unreleased (BC-14); import path in the verify line equals the verified import path; a source-build fallback is shown only after its receipt succeeds | the package name and the import name or namespace, when they differ; which release the README documents when the source tree is ahead (PRC-08) |
| `std-source` | git clone, then the verified build (pip install -e ., npm install and npm run build, dotnet build, cargo build); ProjectReference or Git dependency block for consumers (Imaging .NET, Cells Rust); sys.path or PYTHONPATH step only when no packaging metadata exists (PSD Python, HTML); one sentence on the supported runtime from the manifest | the registry observation is conclusive that no package of that name is published (BC-02); the source-build receipt names exactly the steps the README prints; working directory, ignored inputs and generated files the build needs are shown | that no package is published yet, in one plain sentence, when the registry shows none; the package or project name consumers will use once published, when the manifest names it |
<!-- /generated:channels -->

### 4.3 Assignments

Every registry repository, once each (the validator proves coverage; family and ecosystem are the
registry's own). The seven JMAP libraries were added on 2026-10-11; the Node.js JMAP library is the
44th registry entry and is added here, with its survey row, in the commit that follows its
admission. Until then the validator reports it as an unassigned registry repository.

<!-- generated:assignments -->
| Repository | Family | Ecosystem | Archetype | Channel | API | Voice | Surfaces | Special structures |
|---|---|---|---|---|---|---|---|---|
| 3D .NET | 3d | net | `std-registry` | registry | L | neutral_reference | library | none |
| 3D Java | 3d | java | `std-registry` | registry | L | neutral_reference | library | none |
| 3D Python | 3d | python | `std-registry` | registry | L | neutral_reference | library | none |
| 3D TypeScript | 3d | typescript | `std-source` | source_only | M | neutral_reference | library | none |
| BarCode Python | barcode | python | `std-source` | source_only | S | neutral_reference | library | none |
| Cells .NET | cells | net | `std-registry` | registry | M | neutral_reference | library | none |
| Cells Cpp | cells | cpp | `std-native` | native_build | M | neutral_reference | library | install_warning |
| Cells Go | cells | go | `std-registry` | registry | S | neutral_reference | library | project_structure, extra_reference_sections |
| Cells Java | cells | java | `std-registry` | registry | M | neutral_reference | library | project_structure |
| Cells Python | cells | python | `offtemplate` | registry | none | concise_minimal | library | format_matrix, license_notices_link |
| Cells Rust | cells | rust | `std-source` | source_only | L | neutral_reference | library | project_structure |
| Cells TypeScript | cells | typescript | `std-source` | source_only | M | neutral_reference | library | none |
| Email .Net | email | net | `std-registry` | registry | S | neutral_reference | library | none |
| Email Cpp | email | cpp | `std-native` | native_build | S | neutral_reference | library | none |
| Email Python | email | python | `std-registry` | registry | S | neutral_reference | library | none |
| JMAP .NET | jmap | net | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| JMAP Cpp | jmap | cpp | `std-native` | native_build | none | neutral_reference | library | no_aspose_product_pages |
| JMAP Go | jmap | go | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| JMAP Java | jmap | java | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| JMAP Python | jmap | python | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| JMAP Rust | jmap | rust | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| JMAP TypeScript | jmap | typescript | `std-source` | source_only | none | neutral_reference | library | no_aspose_product_pages |
| Font Python | font | python | `offtemplate` | none | none | persona_pitch | library, cli, mcp | persona_tables, cli_reference, mcp_section |
| GIS .Net | gis | net | `greenfield` | none | none | neutral_reference | library | none |
| HTML Python | html | python | `std-source` | source_only | L | neutral_reference | library | none |
| Imaging .NET | imaging | net | `std-source` | source_only | S | neutral_reference | library | format_matrix |
| Note Python | note | python | `std-registry` | registry | S | neutral_reference | library | license_notices_link |
| Page Python | page | python | `std-registry` | registry | M | neutral_reference | library, mcp | result_images |
| PDF Go | pdf | go | `std-registry` | registry | L | neutral_reference | library | feature_showcase, third_party_notices_section |
| PDF Python | pdf | python | `std-source` | source_only | L | neutral_reference | library | maturity_notice |
| PDF .NET | pdf | net | `std-registry` | registry | XL | neutral_reference | library | image_glance |
| PDF Cpp | pdf | cpp | `std-native` | native_build | L | neutral_reference | library | project_structure, third_party_notices_section |
| PDF Java | pdf | java | `std-registry` | registry | XL | neutral_reference | library | none |
| PDF TypeScript | pdf | typescript | `std-source` | source_only | XL | neutral_reference | library | collapsed_capability_reference |
| PSD .NET | psd | net | `std-source` | source_only | S | scope_forward | library | none |
| PSD Python | psd | python | `std-source` | source_only | M | scope_forward | library | none |
| Slides .NET | slides | net | `offtemplate` | registry | none | candid_handwritten | library | choosing_edition |
| Slides Cpp | slides | cpp | `std-native` | native_build | M | neutral_reference | library | none |
| Slides Java | slides | java | `std-registry` | registry | L | scope_forward | library | choosing_edition, install_warning |
| Slides Python | slides | python | `std-registry` | registry | L | neutral_reference | library | install_warning |
| TeX Python | tex | python | `std-source` | source_only | S | neutral_reference | library | maturity_notice, license_notices_link |
| Words .NET | words | net | `offtemplate` | registry | XL | narrative_marketing | library | format_matrix, provenance_story |
| Words Python | words | python | `std-registry` | registry | M | neutral_reference | library | none |
<!-- /generated:assignments -->

### 4.4 How the pipeline uses them

1. Snapshot the live README and tree (S1). Look up the repository's assignment; an unassigned
   registry repository is a configuration error, not a default.
2. Map the live headings to the common elements (STR-26). The map is the plan's skeleton.
3. Run the detectors of §5.2 and the fact extractors; the difference between what the facts
   support and what the README says is the work list.
4. Emit typed edits (CORRECT, ADD, IMPROVE) for the work list, constrained by the archetype's
   requirement per element and the repository's axes (for example, no package badge while
   `install_channel` is `source_only` and the registry shows nothing).
5. Apply the edits to the live bytes, validate the result against the live baseline (§5.1), and
   seal. No edit means an empty patch.

A new product (a new family or platform) is added by one assignment entry; a new kind of product
by an archetype file and its element requirements. No stage branches on a repository name.

## 5. Do better than live

### 5.1 Acceptance: a Pareto improvement

A change set is accepted only if, over the measure vector below, no measure is worse than the live
README's and at least one is strictly better (PRC-03). Each measure has a deterministic detector;
the first three also bind absolutely, so text the change adds must itself pass every blocking check
and text predicate.

| Measure | Direction | Detector |
|---|---|---|
| Blocking-check failures (BC-01 to BC-14) | must not rise | validation registry run on live and candidate |
| Text-predicate failures (single H1, edition name, fences, license prose, narration) | must not rise | `review/acceptance/text_checks.py` on both |
| Failing examples and dead or contradicted links | must not rise | BC-03 receipts, BC-06 |
| Verified claims preserved (units, links, badges, limitations, capabilities) | must not fall | live-floor check (PRC-05) |
| Required elements of the archetype that are present | must not fall | element map (STR-26) |
| Defect-class count of §5.2 | must fall for at least one class | survey measures as detectors |
| Visible lines | must not rise except to add a required element | STR-24 |
| Mean sentence length | must not rise | TON-02 |

A candidate that fails the rule is not repaired by weakening a check; it is rejected, and the
edit that caused the regression is dropped (`AGENTS.md`: route defects to their earliest causal
stage).

**Every iteration.** The baseline is always the live README at the exact head the candidate is built
against (PRC-09). When a correction merges it becomes the baseline; the next iteration, run
because upstream moved or a detector improved, must beat that baseline again or produce an empty
patch, and may not undo an accepted edit without a new verified cause. The ratchet therefore only
turns one way: the README a visitor sees never gets worse than the one before the change, and
improves whenever a verified defect or gap remains.

### 5.2 Defect classes found in the live READMEs

Every class below was found by the survey, has a deterministic detector or, for DEF-06, an audit
whose findings are accepted only with a quoted line as evidence, and has a correction that
changes the least text. The detector column says whether it exists in `src/` today or is new
(§6); the Live READMEs column lists the repositories the survey found it in.

<!-- generated:defects -->
| ID | Defect class | Live READMEs | Detector | Correction | Preserves |
|---|---|---|---|---|---|
| DEF-01 | second H1 | 1: Cells Go | existing: text_checks.single_h1; BC-07 | Demote the stray H1 to a bold note or fold its sentence into Installation prose; keep the sentence. | the sentence text and its place in Installation |
| DEF-02 | unbalanced details tags | 1: Cells Go | new: details balance over non-code lines | Insert the missing closing tag at the end of the block that precedes the next required heading. | every line inside the block |
| DEF-03 | dead repository-relative link | 3: Cells Python, Font Python, Words .NET | existing: validation/links; BC-06 | Retarget to the file that exists, or to the absolute URL when the link relies on GitHub path resolution (../../issues); remove only when no target exists. | the link text |
| DEF-04 | stale version or release statement | 3: PDF Java, 3D .NET, Cells Go | existing: BC-14 validation/claims.py | Replace the version with the registry's current release or the manifest version, or mark the statement unreleased; keep the surrounding sentence. | the install block and its explanation |
| DEF-05 | install statement contradicts registry or repository state | 3: Words .NET, TeX Python, Imaging .NET | existing: BC-02 registry observation; NEW: contradiction between two README statements | Rewrite the false statement to the observed registry state; keep both install forms when both are true. | every verified install command |
| DEF-06 | capability or limitation claim contradicted by the code | 4: 3D .NET, Cells .NET, Imaging .NET, PDF .NET | claim_audit: LLM audit with read-only repository tools; accepted only when the evidence is a quoted line that exists at the cited path | Correct the sentence to what the cited code does, keeping its place and wording otherwise; an unverifiable claim becomes an issue or an advisory, not an edit. | the rest of the bullet or paragraph |
| DEF-07 | no license file in the tree | 4: 3D TypeScript, PSD .NET, PSD Python, GIS .Net | existing: license fact; components/issues upstream-defect handoff | Do not link a missing file; state the manifest-declared license where one exists; raise an upstream issue handoff. The README cannot fix a missing LICENSE. | the license sentence |
| DEF-08 | unquoted version specifier in a shell command | 1: Words Python | new: pip install with an unquoted comparison operator | Quote the requirement ("aspose-words-foss&gt;=26.5.0"). | the command |
| DEF-09 | documented command cannot run in a clean clone | 5: Page Python, Words Python, Cells Go, PSD Python, Font Python | new: clean-clone execution of documented commands, static first (scripts, targets, paths, ignored inputs) | Correct the command (path, import name, missing step) with the receipt, or raise an upstream issue when the fix belongs in the repository. | the surrounding instructions |
| DEF-10 | stock API descriptions | 9: 3D Java, Cells Java, Cells Rust, Cells TypeScript, Page Python, PDF Python, PDF Cpp, PDF TypeScript, Words Python | new: description matches a stock '&lt;Kind&gt; with N methods' pattern | Replace with the symbol's own documentation summary when it exists; otherwise leave the live row (no regression) and record an advisory. | every row and its name |
| DEF-11 | internal or non-public type listed as public | 4: Cells Cpp, HTML Python, Page Python, Cells TypeScript | existing: public_symbol facts: row name not in the verified public surface | Remove the row, or move it under an honest heading; recompute the stated count. | all verified rows |
| DEF-12 | stated type count differs from the listed rows | 4: PDF Python, PDF .NET, PDF TypeScript, Words .NET | new: stated count against listed rows against symbol facts | Replace the number with the verified count; keep the sentence. | the sentence |
| DEF-13 | code fence without a language | 7: Cells Go, Cells Java, Cells Rust, Font Python, PDF Cpp, Slides .NET, Slides Java | existing: text_checks.fences_and_spacing; BC-07 | Add the language (text for a directory tree or console output, bash for commands). | the fenced content |
| DEF-14 | edition named other than Enterprise Edition | 10: 3D Java, Cells .NET, Cells Cpp, Email Cpp, Note Python, PDF Cpp, Slides .NET, Slides Java, Words .NET, Words Python | existing: text_checks.edition_name; BC-06 (banned list); NEW: commercial-substitute heuristic | Where the phrase refers to the aspose.com product, say Enterprise Edition (see OD-07); where it describes the FOSS code's own origin, leave it. | the sentence meaning |
| DEF-15 | Enterprise Edition paragraph missing or repeated in a README that links Aspose pages | 5: Cells Python, PDF .NET, PDF Java, Slides .NET, Words .NET | new: Aspose pages are linked and Enterprise Edition is not named exactly once | Add the standard closing paragraph when a verified target exists and the README has a Scope section or an equivalent; collapse a duplicate into the closing paragraph. A family with no Aspose pages (LNK-11) is not a case. | the live commercial pointers' facts |
| DEF-16 | mislabeled Enterprise link | 1: Cells TypeScript | new: anchor platform differs from the repository's platform; target against product-page fact | Take anchor and target from the verified product-page fact; if none exists, drop the platform from the anchor and link the family page. | the sentence around the link |
| DEF-17 | truncated sentence | 1: Cells .NET | new: paragraph ends in a comma or without terminal punctuation | Complete the sentence from the verified facts or end it at the last complete clause. | the link |
| DEF-18 | At a Glance as an image only | 1: PDF .NET | new: glance form is image | Add the verified Mermaid diagram and keep the image beneath it with alt text that states what it shows. | the image asset |
| DEF-19 | Dependencies section missing | 3: Cells .NET, Cells Cpp, Cells Python | existing: dependency facts present, section absent; D-owned renderer | Insert the manifest-derived Dependencies section after Installation and add its Navigation link. | all other sections |
| DEF-20 | capability example does not compile | 4: 3D .NET, Cells .NET, Cells Cpp, 3D TypeScript | existing: example verifiers and BC-03 receipts | Apply the minimal fix the compiler proves (a missing include, a read-only property, a wrong overload); remove the example only when no fix is proven. | the example's task and heading |
| DEF-21 | internal process or roadmap text in a public README | 7: PDF TypeScript, Cells Rust, PSD .NET, Email .Net, Slides Cpp, Font Python, Imaging .NET | existing: text_checks.assurance_narration (phrase list); NEW: LLM-proposed, reviewer-confirmed | Move maintainer-process text to Development and Testing or CONTRIBUTING; delete only meta-commentary a reader cannot use. | contributor instructions |
| DEF-22 | stale pre-publication text | 2: Cells Rust, Words .NET | new: phrase list (once the repository is live, landing soon, coming soon) against registry and repository state | Rewrite to the observed state with the evidence. | the install block |
| DEF-23 | absolute link to the repository's own file | 5: Cells .NET, Cells Cpp, Slides .NET, Slides Java, Slides Python | new: github.com blob URL to the same repository | Rewrite to a repository-relative path when the target exists in the tree. | the link text |
| DEF-24 | heading hierarchy smell | 4: PDF TypeScript, Imaging .NET, Cells .NET, BarCode Python | new: level jump, bare label heading, repeated heading text | Advisory only; repair a level jump when the section is edited anyway. Never a stand-alone change. | anchors that other sections link to |
| DEF-25 | non-prose or non-canonical license and name | 5: Font Python, Slides .NET, Words .NET, PSD .NET, PSD Python | existing: text_checks.license_prose; BC-12 canonical product name | Write the License section as the standard prose declaration and set the H1 to the canonical product name. | any extra license facts (font licenses, notices) |
| DEF-26 | README missing | 1: GIS .Net | existing: snapshot: default branch has no README; processability gate | Author the standard skeleton from verified facts only if the tree carries a real public surface; otherwise insufficient_evidence. |  |
| DEF-27 | Dependencies section points at the manifest instead of listing it | 1: JMAP Java | new: a dependency bucket that defers to the manifest file and names no dependency | List the manifest's dependencies with their versions in the bucket and keep the pointer as one sentence. | the pointer sentence |
| DEF-28 | API Reference without a listing | 7: JMAP .NET, JMAP Cpp, JMAP Go, JMAP Java, JMAP Python, JMAP Rust, JMAP TypeScript | new: API Reference holds prose only: no table rows and no member bullets | Keep the intro paragraph and add the collapsed Class \| Description listing built from the verified public symbols, with the verified count; leave an undocumented type undescribed. | the intro paragraph and its error-handling description |
<!-- /generated:defects -->

Prevalence of the markup defects among the READMEs: second H1 1/42 (obs:second_h1), unbalanced
details tags 1/42 (obs:unclosed_details), fences without a language 7/42
(obs:fences_without_language), an unquoted pip specifier 1/42 (obs:unquoted_pip_specifier), heading
level jumps 2/42 (obs:heading_level_jumps), a bare label heading followed by a sibling or shallower
heading 19/42 (obs:empty_label_headings), a repeated heading text 6/42 (obs:duplicate_headings).
The last two are structural smells the older contract itself prescribed (`#### Detailed Member
Reference` followed by `###` groups); they are advisory and never a stand-alone change (DEF-24).

### 5.3 Never remove valuable maintainer content

A correction may replace or delete text only when a verified cause names it (PRC-04, PRC-05). The
protected classes are:

- every command, example and code block that verifies (BC-03, BC-08);
- every verified link, badge and image, including relative links to repository files;
- every limitation the code or tests prove, every capability the code proves, and every warning
  about a published artifact (Slides Java, Slides Python, Cells Go);
- terminology, spelling and voice (a hand-written register is not "fixed");
- uncertainty the evidence cannot resolve, which is preserved as written and flagged.

The permitted operations on a protected unit are: keep; move to the destination the live
structure implies, with the move shown; replace the smallest false span with the verified value.
Deleting a unit requires a typed cause: a failed example receipt, a 404, a contradicted fact, or a
duplicate that survives elsewhere in the same README. A "stale" verdict without a registry or tree
observation is not a cause. Cosmetic normalization (badge order, heading case, dash style) is
never a cause and is never a change by itself (PRC-06).

### 5.4 The edit record

Each edit in the ledger carries: the operation (CORRECT, ADD, IMPROVE); the exact span in the live
bytes; the replacement; the defect class or element it serves; the evidence (receipt, registry
answer, tree path, grep line or predicate) and its revision; and the measure it moves. The ledger,
not the diff, is what the independent reviewer reads (§6 item 9).

### 5.5 What "better than live" means per archetype

<!-- generated:better -->
| Archetype | ID | Better than live means | Measured by | Defects |
|---|---|---|---|---|
| `greenfield` | BTL-GRN-01 | Nothing is claimed that a fact does not support; with no public surface the outcome is insufficient_evidence, not a thin README. | BC-04 unit-to-fact binding; processability gate | DEF-26 |
| `greenfield` | BTL-GRN-02 | The owner's standing rules hold from the first version - canonical H1, one badge row, Enterprise Edition naming, no assurance narration. | text_checks predicates and BC-06, BC-07, BC-12 all pass |  |
| `greenfield` | BTL-GRN-03 | A missing LICENSE or README is raised upstream through an issue handoff and never papered over in the README. | handoff present for each missing community file | DEF-07, DEF-26 |
| `offtemplate` | BTL-OFF-01 | Verified elements the README lacks are inserted beside its own headings without renaming or reordering them. | heading diff shows additions only; the live heading list is a subsequence of the candidate's | DEF-15, DEF-19 |
| `offtemplate` | BTL-OFF-02 | Statements that contradict the code, the registry or each other are corrected with evidence. | claim audit and BC-02 / BC-14; contradiction count falls | DEF-05, DEF-06 |
| `offtemplate` | BTL-OFF-03 | Dead links and commands that cannot run are repaired or flagged upstream. | dead_relative_links zero; clean-clone receipts | DEF-03, DEF-09 |
| `offtemplate` | BTL-OFF-04 | The H1 is the canonical product name and License is the prose declaration, keeping any extra license facts. | h1_canonical; license_prose | DEF-25 |
| `offtemplate` | BTL-OFF-05 | References to the aspose.com product use Enterprise Edition, once, in the live heading that already points there. | enterprise_mentions equals one; commercial_substitute_mentions falls | DEF-14, DEF-15 |
| `offtemplate` | BTL-OFF-06 | The README's voice is kept; no marketing wording, emoji or first person is added and none is rewritten into the portfolio default. | marketing_words, emoji, first_person_words not higher than live |  |
| `std-native` | BTL-NAT-01 | Each install form is verified against the CMake files and the NuGet package contents, and platform limits are stated. | target, package and tag equality against the repository; package listing against the Windows-only claim | DEF-05 |
| `std-native` | BTL-NAT-02 | Dependencies carries the C++ standard, CMake floor, test framework version and bundled third-party code from the build files. | bucket contents equal CMakeLists and FetchContent declarations | DEF-19 |
| `std-native` | BTL-NAT-03 | Every example compiles with exactly the includes it shows. | g++ or MSVC compile receipt (BC-03); a missing include is added | DEF-20 |
| `std-native` | BTL-NAT-04 | API rows name public header symbols only, with real descriptions where header documentation exists; a prose-only API Reference gains the collapsed listing. | row set equals the public_symbol facts; api_boilerplate_rows falls | DEF-10, DEF-11, DEF-28 |
| `std-native` | BTL-NAT-05 | Directory trees and CMake blocks carry a fence language. | fences_without_language is zero | DEF-13 |
| `std-registry` | BTL-REG-01 | Every version, install command and publication statement equals the registry answer or is marked unreleased. | BC-14 on live and candidate; stale-version count must not rise and must fall where the live README is stale | DEF-04, DEF-05 |
| `std-registry` | BTL-REG-02 | Dependencies exists with manifest-derived buckets, verified-empty stated, and is linked from Navigation. | section presence; bucket contents equal the dependency snapshot | DEF-19 |
| `std-registry` | BTL-REG-03 | Every shown example compiles or runs at the revision; a proven fix replaces a failing one, and removal needs a receipt. | BC-03 receipts; failing-example count must not rise | DEF-20 |
| `std-registry` | BTL-REG-04 | API Reference lists only public types, states the verified count, and replaces stock descriptions with the symbols' own documentation where it exists. | survey_features api_count_mismatch, api_boilerplate_rows; row set equals the public_symbol facts | DEF-10, DEF-11, DEF-12 |
| `std-registry` | BTL-REG-05 | Exactly one Enterprise Edition paragraph closes Scope and Limitations with a verified, correctly labeled target, and no other wording names the aspose.com product's edition. | enterprise_mentions equals one; anchor platform equals the repository platform; commercial_substitute_mentions falls | DEF-14, DEF-15, DEF-16 |
| `std-registry` | BTL-REG-06 | Documented commands, including the verify step, run in a clean clone. | clean-clone execution receipt per documented command | DEF-08, DEF-09 |
| `std-registry` | BTL-REG-07 | Markup hygiene is repaired where it is broken: one H1, balanced details tags, fence languages, working relative links. | second_h1, unclosed_details, fences_without_language, dead_relative_links all zero or not higher than live | DEF-01, DEF-02, DEF-03, DEF-13, DEF-23 |
| `std-source` | BTL-SRC-01 | The README states the publication state the registry shows, in one sentence, with no contradicting install command. | BC-02 conclusive registry observation against the README's own statements | DEF-05, DEF-22 |
| `std-source` | BTL-SRC-02 | Every source-install and build command runs in a clean clone, including the working directory and ignored inputs it needs. | clean-clone execution receipt | DEF-09 |
| `std-source` | BTL-SRC-03 | Dependencies lists runtime, optional, native and development requirements, including toolchain floors, from the manifest. | bucket contents equal the dependency snapshot; Python, Node, Rust or .NET floors equal the manifest | DEF-19, DEF-06, DEF-27 |
| `std-source` | BTL-SRC-04 | The license sentence matches a license file in the tree; where none exists the README links nothing missing and an upstream issue handoff exists. | license fact against the tree; handoff present | DEF-07 |
| `std-source` | BTL-SRC-05 | Maturity statements (alpha, pre-release) agree with the manifest's classifiers and version. | statement against pyproject classifiers or package version | DEF-04 |
| `std-source` | BTL-SRC-06 | Examples import from the path the source tree really provides and compile or run there. | BC-03 receipts against the built output | DEF-20 |
| `std-source` | BTL-SRC-07 | API Reference holds only public types with the verified count and no stock descriptions where documentation exists; a prose-only API Reference gains the collapsed listing. | survey_features api_count_mismatch, api_boilerplate_rows; row set equals the public_symbol facts | DEF-10, DEF-11, DEF-12, DEF-28 |
<!-- /generated:better -->

## 6. Migration plan

### 6.1 What of the legacy contract survives

| `README_CONTRACT.md` | Status under this standard |
|---|---|
| §1 Outcome | Kept; the visible-length sentence becomes the no-grow rule (STR-24, OD-06). |
| §2 Semantic shell, rows 1 to 20 | **Superseded** by §3 and §4 here. Kept only as the legacy encoding of `SEMANTIC_SHELL` until item 1 below lands. |
| §2.1 At a Glance topology | Kept as written; it is an OWNER_RULE (STR-08). |
| §2 prose after the table (headings, canonical abbreviations, never present) | Kept for text the change adds (STR-22, TON-04, LNK-03). |
| §3 Assembly pipeline (S1 to S12) | Amended: S4 defaults to keep-in-place, S5 plans edits not sections, S7 applies edits to the live bytes (items 2 to 4). Fact kinds, content-unit and placement rules stay. |
| §4 Agentic decisions | Amended: the planning decision becomes "which edits"; the guards are unchanged. |
| §5 Blocking checks | Kept, made baseline-relative where marked (items 5 to 7). |
| §6 Repair scope, §7 Bundle layout | Kept; the bundle gains `edits.json` (the ledger) in item 4. |
| §8 Prose rules | Kept for added text; live prose is never rewritten to meet them (PRC-01). |

Where the legacy contract and the live portfolio disagree, the live portfolio decides, and the
decision is recorded here once:

| Legacy rule | Live portfolio | Resolution |
|---|---|---|
| Row 7: three to eight capabilities | 16/31 inside the range (obs:capabilities_3_to_8) | no cap (OD-03) |
| BC-06 and row 18: anchor opens "full-featured" | 0/30 (obs:enterprise_full_featured_anchor) | keep live anchor (OD-02) |
| Row 14: summary "View the Complete Public API Surface" | 1/39 (obs:api_summary_view_complete) | keep live wording |
| Visible budget 300 (code) or 320 (contract) lines | 12/35 over 300 (obs:visible_lines_over_300) | no-grow (OD-06) |
| Row 3 banner and `promotion_after_product` | banner present in 32/42 (obs:banner_present) | preserve, never add (OD-01) |
| Row 2 and BC-07: badge order blocks | 16/33 in order (obs:badge_order_ok) | order governs added badges (OD-05) |
| Row 5: Navigation required | 39/42 (obs:navigation_present) | required in the standard skeleton, optional in an off-template README |

### 6.2 Code gates and governed constants that encode the old contract

Efforts are focused engineer-days for one lane including focused tests (`AGENTS.md`), estimated
from the size of the file and the 2026-10-11 correction analysis; every item is a work item that
needs the cursor's usual admission. Schema changes under `schemas/` need an owner-admitted §31
proposal.

| # | Gate or constant | File | Encodes today | Change | Days | Governed version |
|---|---|---|---|---|---|---|
| 1 | `SEMANTIC_SHELL` (17 sections, Navigation and API Reference required, D-owned sections supersede inherited units) | `composition/components/shell.py` | the contract's §2 table as the fixed template | the shell becomes the element catalogue of `common.yaml`: candidates for insertion beside the live skeleton, not a template; D renderers produce inserted blocks only | 2 | `SHELL_VERSION` 6 |
| 2 | Presentation planning (section inclusion by shell condition) | `composition/planning.py` (1517 lines), `prompts/presentation_planning.yaml` (carries the plan's output schema) | plan = which shell sections to render | input = live skeleton map and the archetype; output = typed edits (CORRECT, ADD, IMPROVE) with evidence | 5 | `NORMALISATION_VERSION` 34; the planning prompt manifest hash |
| 3 | Renderer (whole-document rendering, `render_patch` diff of live to candidate) | `composition/renderer.py` (1296 lines) | section order, Navigation, Installation, Dependencies, License rendered wholesale | apply the edit ledger to the live bytes by exact-match span replacement; keep the deterministic renderers for inserted blocks; `README.patch` stays a unified diff | 5 | `RENDERER_VERSION` 32 |
| 4 | Reconciliation default and placement | `reconciliation/dispositions.py` (1951 lines), `composition/placement.py`, `prompts/source_reconciliation.yaml` | `SUPERSEDE_REDUNDANT` is the dominant disposition; one shared fact id drops a whole preserved unit | default keep-in-place; `CORRECT_WITH_EVIDENCE` gains a replacement-text field; overlap drops only the covered items; bundle gains `edits.json` | 4 | `NORMALISATION_VERSION`; the reconciliation prompt manifest hash; `schemas/candidate-bundle.schema.json` for `edits.json` (owner admission) |
| 5 | BC-07 structure check (stable badge order, title-case headings, topology, length) | `validation/registry.py` (2426 lines), check BC-07 | the old structure for every candidate, absolutely | judge the delta against live: no new failure, absolute only for added text (PRC-03) | 3 | `VALIDATOR_VERSION` 21; Check BC-07 version 10 |
| 6 | BC-05 and BC-08 (dispositions, protected content) | `validation/registry.py`, `validation/deferrals.py` | commands and ecosystem code blocks protected; prose, links, badges and limitations not | item-level floor over prose, links, badges, limitations; typed-cause exceptions only | 3 | Check BC-05 6, BC-08 2 |
| 7 | BC-06 Aspose links and edition name | `validation/links/rules.py`, `composition/link_budget.py` | the "full-featured" anchor prefix; ceilings for generated links | prefix check off in live-first mode until OD-02; ceilings apply to links the change adds | 1 | Check BC-06 7; `LINK_BUDGET_VERSION` 1 |
| 8 | Acceptance profile and template checker | `review/acceptance/profile.py`, `scorer.py`, `template_check.py` | the 30-point template conformance | rebase on the §5.1 vector; template conformance becomes the archetype element map | 2 | `PROFILE_VERSION` 2 |
| 9 | Independent review | `prompts/independent_review.yaml`, `review/independent/review.py` | the original is "evidence, not the standard"; renderer-owned text out of scope | the reviewer reads the ledger and the diff against live; scope is the edits | 3 | `REVIEWER_LOGIC_VERSION` 19 |
| 10 | Planning policy | `composition/policy.py` | `capabilities_min` 3, `capabilities_max` 8, `visible_lines_budget` 300 | no caps in live-first mode; no-grow rule | 0.5 | `POLICY_VERSION` 1 |
| 11 | Contract version recorded in every bundle | `bundle/seal.py` | `CONTRACT_VERSION = "readme-contract-v1"` | record the standard the candidate was built against | 0.5 | `CONTRACT_VERSION` |
| 12 | Documents that name the contract as the structure authority | `docs/README_CONTRACT.md`, `docs/EXECUTION_STATE_MACHINE.md` (lines 77, 235, 239), `AGENTS.md` (Authority by subject), `project/state.yaml` (authority block) | `README_CONTRACT.md` owns "shape" | name `README_STANDARD.md` as owner of shape; delete §2 of the contract and fold its §8 into §3.5 here when item 1 lands | 1 | none |
| 13 | The live-first lane | new package `src/repository_presenter/components/readme/live_first/` (edit ledger, apply engine, detectors, archetype loader reading `data/readme_standard/`) | does not exist | Phase 1 (ledger, apply, baseline-relative validation, deterministic detectors, PR body): about 11 days; Phase 2 (staleness, example repair, diff-scoped review, clean-clone execution): about 12.5; Phase 3 (claim audit): 6 to 8 | 30 | none (new component; it records its own version from the first seal) |

**Sequencing.** Item 13 Phase 1 can start now and needs no governed constant, because it lives
beside the existing pipeline and consumes only the data files. Items 1 to 11 change meaning of
governed components, so their bumps (`RENDERER_VERSION`, `NORMALISATION_VERSION`,
`REVIEWER_LOGIC_VERSION`, `VALIDATOR_VERSION` and the per-check versions of BC-05, BC-06, BC-07 and
BC-08, plus `SHELL_VERSION`, `POLICY_VERSION`, `PROFILE_VERSION` and `CONTRACT_VERSION`) land
together in one cut after the cut now on `integration/cut3`, with one bump per constant and the
version-bump discipline test green, so a sealed bundle reads as `VALID_UPDATE_AVAILABLE` rather than
being invalidated wholesale (`AGENTS.md`: never add a global control-plane hash). Item 12 lands in
the same commit as item 1, because the document must stop naming the contract as the owner of shape
at the moment the code stops encoding it.

**Interim.** Until items 1 to 11 land, the sealed regeneration pipeline keeps producing candidates
under `readme-contract-v1`. Those candidates are not authorizable under this standard unless the
baseline-relative validation of item 5 passes; the progress unit stays as `AGENTS.md` defines it
until the owner replaces it.

## 7. Open owner decisions

Each default below is what the standard does until the owner rules; none is silent.

<!-- generated:decisions -->
| ID | Question | Default until the owner rules | Rules |
|---|---|---|---|
| OD-01 | The banner links to products.aspose.org above the opening, which plans/idea.md L79 reads as promotion before the product is explained, while the live portfolio does it in 32/42 READMEs. | Preserve the live banner unchanged and never add one; the promotion_after_product predicate judges only links the change adds. | STR-05, LNK-02 |
| OD-02 | plans/idea.md L109 asks for a 'full-featured ... Enterprise Edition' anchor and BC-06 enforces the prefix; no live anchor uses it (0/30). | Keep the live anchor; new anchors read 'Aspose.&lt;Family&gt; for &lt;Platform&gt; — Enterprise Edition'. The prefix check stays off in live-first mode until the owner rules. | LNK-04 |
| OD-03 | README_CONTRACT row 7 caps Key Capabilities at three to eight items; only 16/38 live READMEs stay inside that range. | The live count stands; no cap in live-first mode. | STR-09 |
| OD-04 | plans/idea.md L110 says source tone and prose structure are not preservation obligations; the 2026-10-11 directive says the opposite. The owner may wish to amend idea.md. | The directive governs; idea.md is not edited by agents. | PRC-01 |
| OD-05 | The owner's badge order (package, runtime, build, license, contributors) is followed by 21/40 of the live rows that have two or more badges. | Apply the order to added badges; never reorder an existing row alone. | STR-04 |
| OD-06 | The visible-length budget is 300 lines in code and 320 in the contract; 12/42 live READMEs exceed 300. | Visible length may not grow except to add a required element; no trimming to a budget. | STR-24 |
| OD-07 | 10/42 live READMEs use 'commercial' for the aspose.com product; the owner rule allows Enterprise Edition only. | Rewrite when the phrase refers to the aspose.com product, with the diff shown to the reviewer; leave phrases about the code's own origin. | LNK-03 |
| OD-08 | Cells Go documents the v26.7.1 release while main is ahead of that release; no policy says whether a README documents the release, main, or both. | Document the release and mark main-only features unreleased (PRC-08). | PRC-08 |
<!-- /generated:decisions -->

## 8. Maintaining this standard

- **Change a rule** by editing `data/readme_standard/common.yaml`, then
  `python -X utf8 -m tools.readme_standard.check_profiles --write-doc`. The tables of this document
  are rendered from the data; the prose around them is edited by hand and its tagged numbers are
  checked.
- **Change a frequency** only by re-measuring (§2). Never edit a count; a count that crosses 80
  percent changes the rule's basis in the same commit.
- **Add a repository** by one entry in `assignments.yaml` and one survey row (shallow, read-only
  clone, then `build_survey --root <old clones> --root <new clones>`, which keeps every old row
  byte for byte when its clone is unchanged); the validator fails until the registry, the
  assignments and the survey agree and `api_size_class` matches the survey. The Node.js JMAP
  library is the next one due.
- **Add an archetype** as `archetypes/<id>.yaml` defining every element of `common.yaml`; the
  validator fails on a missing or unknown element and on an archetype with no member.
- **Version.** The standard has no version constant until item 11 of §6 lands; until then a
  change that alters a rule's meaning is recorded in `docs/DECISION_LOG.md` by the owner of that
  file, and this document's date line is the only marker.
- **Run** `python -X utf8 -m tools.readme_standard.check_profiles` (exit 1 on any problem) and
  `pytest tests/test_readme_standard.py`; both run in CI with the rest of `tests/`.

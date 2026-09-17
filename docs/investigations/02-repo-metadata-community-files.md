# Investigation 02: Repo Metadata, Social Appearance, and Community Files

Status: research only, no implementation. Written 2026-09-17 against
`docs/PRODUCTION_ROADMAP.md` workstream 2 (`Repo metadata / social appearance / community-files
component`, anchored to `plans/idea.md`'s "Visual Assets and Social Preview" section and the
"Central Agent" responsibilities bullet "maintaining the website, topics, visuals, and
social-preview image" / "checking community, contribution, licensing, and security files").
`plans/idea.md` is the human product authority this report reconciles against; nothing here
overrides it, and nothing here authorizes a taskcard — per `docs/PRODUCTION_ROADMAP.md`'s
standing rule, that still needs an owner decision after this report is read.

## 1. Current codebase state

### 1.1 What the README pipeline already does

`src/repository_presenter/components/readme/` is the only populated directory under
`components/`; there is no sibling `components/repo_metadata/`, `components/community/`, or
similar. Its subpackages (`extractors/`, `investigation/`, `reconciliation/`, `composition/`,
`validation/`, `review/`, `repair/`, `bundle/`, `evidence/`) implement one pipeline: read a
repository's default-branch README plus its source/manifests/tests/examples, extract verified
facts, reconcile the existing README against those facts, compose a new candidate README locally,
validate and independently review it, and seal it as evidence. Per `plans/idea.md`'s Gate A/B/C
staging, none of this writes back to GitHub yet — the whole pipeline stops at a local sealed
candidate bundle (`candidates/<owner>__<name>/<revision>/`); PR creation (Gate C) is itself still
future work, gated behind full-registry Gate A/B completion.

### 1.2 What touches community files today — detection only, not maintenance

`src/repository_presenter/core/snapshot/inventory.py` case-insensitively scans a repository clone
root for `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, and `SUPPORT` files (plus README, LICENSE,
and NOTICES variants) and records their `Path` if present, in a `FileInventory` dataclass. This is
read-only presence detection over a handful of hardcoded filename variants — it does not read
their content for reconciliation, does not validate their content against repository facts, and
does not create, edit, or propose changes to them. It exists to let other stages know a file
exists at all (e.g. so a README can safely link `[Code of Conduct](CODE_OF_CONDUCT.md)` without
guessing at the filename), not to maintain those files' substance.

No other module references `community_paths`, `CODE_OF_CONDUCT`, `CONTRIBUTING`, `SECURITY`, or
`.github/ISSUE_TEMPLATE` outside this scan and one README-composition line that emits the fixed
verbatim relative link shown above when the file is present. Confirmed by grep across
`src/repository_presenter/` for community-file names, GitHub topics/description/social-preview
terminology, and any GitHub API client: none of repo description, topics, homepage, or
social-preview-image is read, computed, or written anywhere in the current source tree.

### 1.3 No GitHub write client exists yet — but the layout already reserves a place for one

There is no `core/github/` directory yet (only `core/git_safety/`, `core/llm/`, `core/registry/`,
`core/snapshot/` exist under `core/`), and `pyproject.toml` depends on `httpx` only — no GitHub
SDK (`PyGithub`, `ghapi`, `gidgethub`, etc.). However, `docs/REPOSITORY_LAYOUT.md` §2 already
reserves `core/github/` with the annotation "read and write GitHub API clients", and
`core/config.py`'s docstring/layout note anticipates "a subpackage once G4 adds GitHub App
configuration" plus a GitHub check joining `core/preflight.py` "at G4". `.github/workflows/` is
likewise annotated as growing `monitor.yml, present.yml, propose.yml from G4`. In other words: the
project's own architecture already earmarks one shared read/write GitHub API client boundary for
whichever gate first needs to write to GitHub (Gate C's PR creation, per `plans/idea.md`) — a
future repo-metadata/social/community-files component should plug into that same boundary rather
than building a second bespoke GitHub client. Today, `core/config.py` reads only
`GPT_OSS_ENDPOINT`/`GPT_OSS_API_KEY`/`GPT_OSS_MODEL` (the LLM gateway); there is no GitHub App
authentication code anywhere yet, consistent with `plans/idea.md` treating GitHub App auth as
still-future production machinery.

**Conclusion for Q1:** the boundary is exactly where `plans/idea.md` and the roadmap say it is.
Nothing beyond README content currently reads or writes repo metadata, social-preview assets, or
community-file content; community-file *detection* (presence/path only) is the one adjacent piece
of machinery that exists, and it is deliberately shallow.

## 2. What the GitHub API actually supports (researched 2026-09-17)

Verified two ways: `gh api` calls against this project's own live repository
(`babar-raza/repository-presenter`, authenticated via the session's `GH_TOKEN`), and current
GitHub REST API documentation / community discussions.

### 2.1 Repository description, homepage, and topics — writable

- `PATCH /repos/{owner}/{repo}` accepts `description` (string) and `homepage` (string) directly,
  among many other repo-settings fields (`name`, `private`, `visibility`, `has_issues`,
  `default_branch`, merge-button settings, `archived`, `allow_forking`, etc.). It does **not**
  accept `topics` — the docs explicitly redirect topic changes to a separate endpoint.
- `PUT /repos/{owner}/{repo}/topics` is the dedicated endpoint: body is `{"names": [...]}`, an
  array of strings; GitHub lowercases and validates them server-side; sending `[]` clears all
  topics.
- Live check confirms both are populated, readable fields on a normal `GET /repos/{owner}/{repo}`
  response (`description`, `homepage`, `topics` were `null`/`null`/`[]` respectively on this
  project's own repo, i.e. unset, but present and typed as expected).
- Both operations need a token/App installation with **repository administration write** access
  (GitHub's "Administration" permission set) — a materially higher privilege than the read-only
  scopes Gate A/B need today. This is a concrete new production-credential requirement, not just
  new code.

### 2.2 Social-preview image — still manual-UI-only, confirmed unchanged

- There is **no** REST or GraphQL endpoint to upload or replace a repository's social-preview
  (Open Graph) image. `GET /repos/{owner}/{repo}` does return a read-only
  `social_preview_image_url` field (confirmed live: present, `null` when unset), so an agent
  *can* observe whether a custom preview is currently set and what URL GitHub is serving, but
  cannot set it.
- The most recent GitHub-staff-adjacent confirmation found (`github/orgs/community` discussion
  #172072, last activity 2025-09-04, i.e. within the last year, not from years ago) states plainly
  that no public API endpoint exists for this and directs requesters to file a feature request.
  Feature-request threads propose either a dedicated `PUT /repos/{owner}/{repo}/social-preview`
  upload endpoint or an `og_image` field on the existing `PATCH`, but neither is implemented.
  An unofficial, undocumented upload endpoint
  (`https://github.com/upload/policies/repository-images`) is used by at least one third-party
  tool (`AnswerDotAI/gh-social-preview`) via browser-session reverse engineering — not a supported
  API, not something this project should depend on, and inconsistent with `plans/idea.md`'s
  explicit ban on undocumented/unsupported mechanisms for this exact surface ("a social-preview
  image is a manual-UI surface unless and until GitHub provides a documented, supported automation
  mechanism").
- **`plans/idea.md`'s claim is still accurate as of this writing.** No update needed to that
  section; the interim-fallback design it already specifies remains the only compliant path.

### 2.3 Community-file health — a read-only observation signal, not a write surface

- `GET /repos/{owner}/{repo}/community/profile` ("Get community profile metrics") is GET-only —
  confirmed live, and confirmed by docs. It returns `health_percentage` (an integer, not simply
  one of {0,25,50,75,100} in practice — real repositories show values like 28, 37, 87, so the
  underlying weighting is more granular than the public docs' simplified description implies),
  `description`, `documentation`, `updated_at`, and a `files` object.
- **Live-verified exact key set of `files` on this project's own repo:** `code_of_conduct`,
  `code_of_conduct_file`, `contributing`, `issue_template`, `license`, `pull_request_template`,
  `readme`. Notably **`security` is not one of the keys** — GitHub's community-profile health
  score does not score `SECURITY.md` presence at all, even though `SECURITY.md` is one of the
  file types `core/snapshot/inventory.py` already detects locally and `plans/idea.md` explicitly
  names as something the central agent should check. A future implementation must not assume
  `community/profile` is a complete community-file signal; `SECURITY.md` (and `SUPPORT.md`, also
  not scored) need their own presence/content checks regardless of what this endpoint reports.
- This endpoint cannot be a fork's repository, and needs only baseline read access — it is a good
  cheap "current observed state" input (e.g. "does GitHub itself think CONTRIBUTING.md is
  missing") to cross-check against the local clone scan, but it computes a score GitHub owns; nothing
  about the score itself is settable by API. The only way to move `health_percentage` is to change
  the underlying files, which is a `core/github` **Contents API** write (or a PR), not a call to
  this endpoint.

### 2.4 Community-file content — ordinary repository files, no special API

CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, and `.github/ISSUE_TEMPLATE/*` /
`.github/PULL_REQUEST_TEMPLATE.md` are not a distinct GitHub API surface at all — they are plain
repository file content, written the same way any file is written: the Contents API
(`PUT /repos/{owner}/{repo}/contents/{path}`) for a direct commit, or a branch + pull request for
a reviewed change. This is exactly the same write mechanism `plans/idea.md`'s Gate C already needs
for proposing README changes. **This means the net-new GitHub API surface this workstream actually
needs is small**: repo-settings write (`PATCH`/topics `PUT`) for §2.1, and nothing at all beyond
the existing (future) Gate C file/PR mechanism for community-file content. The hard, novel part of
this workstream is content generation and reconciliation discipline, not API integration.

## 3. What "maintaining community files" would concretely mean

Sketch only — this is not a design document and authorizes no implementation.

The shape is a direct extension of the discipline the README pipeline already applies, generalized
from one document type (README) to a handful of others, each still governed by the same rule
`plans/idea.md` states for README content: **every claim must trace to verified repository
evidence; unresolved gaps are omitted or flagged, never invented.**

- **SECURITY.md** — a reporting process and contact needs a verified source: an existing
  organization-wide security policy, a verified security-contact address/form the repository
  evidence (or an authoritative owner input, analogous to how `plans/idea.md` already treats
  `ProductFactsV2`/ecosystem facts) actually names. If no such verified contact exists, the correct
  behavior is the same "fail closed rather than fabricate" rule README composition already
  follows for unsupported claims (`plans/idea.md` §"Trust and Repository-Grounded
  Reconciliation") — never invent a plausible-sounding security email or process.
- **CONTRIBUTING.md** — derivable largely from facts the README pipeline already extracts per
  ecosystem: build/test commands (`extractors/platforms/<ecosystem>*.py` already verify these for
  README examples), license (`evidence/facts/license.py` already extracts this), and repository
  structure. The reconciliation discipline is the same: prefer an existing maintainer-authored
  CONTRIBUTING.md as valuable curated input (per `plans/idea.md`'s "existing README is a
  high-value... source" principle, generalized to this file type) over regenerating from scratch,
  and only correct/fill gaps against verified facts.
- **CODE_OF_CONDUCT.md** — the lowest-risk of the set: this is close to boilerplate (e.g. the
  Contributor Covenant) with a verified contact substituted in; still needs the same "don't
  fabricate a contact" discipline as SECURITY.md.
- **`.github/ISSUE_TEMPLATE/*`, `PULL_REQUEST_TEMPLATE.md`** — structurally generated from
  ecosystem facts (e.g. asking for language/runtime version, reproduction steps) rather than prose
  reconciliation; closer to the README's structural-component discipline
  (`composition/components/`) than its evidence-reconciliation discipline.
- Each of these would need its own fact sources feeding the same kind of typed, versioned
  evidence records the README pipeline already uses (`core/facts.py`, `evidence/facts/`), its own
  validation/review gate proportional to its risk (SECURITY.md's fabricated-contact risk is much
  higher than a template's structural risk), and would be sealed and PR'd through the same Gate-C
  mechanism as README changes rather than a separate write path.
- This is **not** a request to design the full pipeline now — only to record that it is
  reconciliation-shaped work, not integration-shaped work, and that it can reuse the README
  pipeline's typed evidence/validation/review pattern rather than inventing a new one.

## 4. Editable vs. observation-only — the concrete GitHub-surface map

Directly answering `plans/idea.md`'s "auditing GitHub-generated information without treating it as
directly editable metadata" and the "Lessons From Existing Repositories" principle that
GitHub-computed signals (contributors, languages, activity, stars, forks) are observations only:

| Surface | Editable via API? | Mechanism | Notes |
|---|---|---|---|
| Repo description | Yes | `PATCH /repos/{o}/{r}` (`description`) | plain text field |
| Repo homepage URL | Yes | `PATCH /repos/{o}/{r}` (`homepage`) | plain text field |
| Repo topics | Yes | `PUT /repos/{o}/{r}/topics` | separate endpoint, not part of `PATCH` |
| Social-preview image | **No** | manual UI only (Settings → Social preview) | `social_preview_image_url` is readable, not writable; no documented/supported upload API exists as of 2026-09 |
| Community-file content (CONTRIBUTING/SECURITY/CODE_OF_CONDUCT/templates) | Yes | Contents API / PR — ordinary file write, same as README | not a distinct GitHub feature |
| Community-profile `health_percentage` and its `files` flags | **No** | fully computed by GitHub from the files actually present | move it only by changing underlying files; the score itself has no write endpoint |
| Contributors, languages, activity, stars, forks | **No** | fully GitHub-computed | already correctly named "observations only" in `plans/idea.md`; nothing above changes that — confirms it, does not need re-verification, since none of these surfaces has ever had a write endpoint at any point in GitHub's API history |

The one nuance worth flagging to the owner: community-profile `health_percentage` sits in between
the two categories in a way `plans/idea.md`'s current two-bucket framing ("editable" vs.
"observation-only, GitHub-generated") doesn't quite name. It is GitHub-generated and never
directly writable, exactly like stars/forks — but unlike stars/forks, this project *can* move it
indirectly, on purpose, by doing the (editable) community-file work in §3. It should be treated as
an **observation** for direct-editing purposes (never attempt to "set" it) but is a legitimate,
useful *target metric* for the community-files workstream's own before/after evidence.

## 5. Minimum viable slice if the owner wants to start now

`plans/idea.md` is explicit that this whole workstream is **not required for the initial pilot**.
If the owner nonetheless wants a first slice, the natural ordering by risk and infrastructure
dependency is:

**Phase 0 — read-only observation, zero product effect.** Extend the existing evidence capture
(alongside `core/snapshot/inventory.py`'s local file scan) to also record, per repository:
`description`, `homepage`, `topics`, `social_preview_image_url`, and the full
`community/profile` response. This needs only the read-level GitHub access Gate A/B already use
(no new credential scope), produces no write, and gives the owner a first honest before/after
baseline across the registry before any change is proposed. This is the safest possible starting
point and arguably should happen regardless of when the rest of the workstream lands, since it
costs almost nothing and directly informs how large the eventual community-files gap actually is
across the portfolio.

**Phase 1 — description/topics/homepage proposal.** The lowest-content-risk editable surface:
short, deterministically checkable text (does the proposed description match a verified
one-sentence product summary already reconciled for the README's opening/H1? do proposed topics
trace to verified language/format/ecosystem facts rather than being guessed?). Still needs the new
"Administration: write" credential scope this project does not have configured anywhere today —
that is itself a real, non-trivial dependency (a GitHub App permission grant, most naturally
alongside whatever Gate C's App setup already needs, per `core/github/`'s reserved layout slot),
not just new application code.

**Phase 2 — community-file generation.** Higher-risk content-generation work per §3, needing its
own validation/review proportional to each file's fabrication risk (SECURITY.md's contact info
highest, templates lowest). This should not start before Phase 1 proves the write path
(credentials, PR mechanism reuse) works safely on the simpler surface.

**Interim fallback for social-preview specifically**, matching `plans/idea.md`'s own prescription
almost exactly: since no supported write API exists and none is expected soon (§2.2), the
minimum-viable version of this piece is (a) derive a validated image asset from verified repository
facts (product name, canonical branding, format/language badges — whatever the README's own
verified identity facts already establish, so the asset never asserts something the README
doesn't), (b) track desired-vs-observed state by reading `social_preview_image_url` and a content
hash/fingerprint of the last asset prepared, so an unchanged asset is never regenerated or
re-flagged, (c) when the desired asset differs from what evidence suggests is currently applied,
emit a precise manual-application handoff (exact file, exact upload location — Settings → Social
preview — and exact expected visual result) for a human to apply, and (d) never record or imply
that the preview was actually applied until a human confirms it (there is no API to verify
application either, so this confirmation is necessarily manual too, and the record must say so
plainly rather than inferring success from the handoff having been issued).

## 6. Open questions for the owner

1. Should description/topics changes flow through the same Gate A→B→C review/authorization
   ladder as README content, or does their much smaller blast radius (a few words vs. a whole
   document) justify a lighter-weight path? `plans/idea.md` doesn't say explicitly for this
   surface.
2. Is there an existing, verified, canonical Aspose security-contact address/process this project
   can cite as evidence for SECURITY.md generation, or does that itself need to come from the
   owner as an authoritative input (the same role `ProductFactsV2`/ecosystem facts play for
   README, per `plans/idea.md`'s "Product Agents" section)? Without one, SECURITY.md generation
   cannot start at all under the "never fabricate" rule.
3. Should community-file candidates be sealed as their own bundle type alongside the README
   candidate, or as an extension of the existing README bundle for a repository? This affects
   `core/registry`/`bundle/seal.py` reuse vs. a new sealed-artifact shape.
4. Given `core/github/` is already reserved in the layout for Gate C's PR mechanism, should this
   workstream's write client be built as part of that same effort (shared credential/App setup,
   shared rate-limit/retry policy) rather than separately timed — i.e., does workstream 2's Phase 1
   effectively need to wait for (or merge into) whatever unblocks Gate C, rather than running fully
   independently as the roadmap's five-workstream table currently implies?
5. GitHub also exposes organization-level "custom repository properties" (a newer, separate
   mechanism from topics, aimed at governance tagging). Out of scope for this report, but worth a
   deliberate "not now" or "not applicable" decision if the owner later asks why topics rather than
   custom properties were used for any governance-relevant tagging.

## Sources consulted

- `plans/idea.md` (`Visual Assets and Social Preview`, `Central Agent`, `Lessons From Existing
  Repositories`, `Upstream Defect Reporting`, `Execution Environments and GitHub Access`)
- `docs/PRODUCTION_ROADMAP.md` (workstream 2 row and its "known constraints already on record")
- `docs/REPOSITORY_LAYOUT.md` §2 (`core/github/`, `core/config.py`, `.github/workflows/` future
  entries)
- `src/repository_presenter/core/snapshot/inventory.py`,
  `src/repository_presenter/core/config.py`, `pyproject.toml`
- Live `gh api` calls against `babar-raza/repository-presenter`:
  `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/community/profile`
- GitHub REST API docs: `rest/repos/repos` (update a repository; replace all repository topics),
  `rest/metrics/community`
- `github/orgs/community` discussion #172072 ("API Endpoint to update a project social preview?"),
  last activity 2025-09-04

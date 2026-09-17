# Investigation 04 — Portfolio Discovery Module

Written 2026-09-17, research-only, isolated worktree. Commissioned by
`docs/PRODUCTION_ROADMAP.md` workstream 4 ("Portfolio discovery module — find new
repos/products, reuse an existing aspose.org discovery mechanism if one exists"), itself
anchored on `plans/idea.md`'s **Common Gate C0** ("complete authorized-portfolio discovery
and intake"). No code changes accompany this report; it is research to inform a future
taskcard, per the roadmap's own standing rule ("do not start implementing any of the five
workstreams from this document alone").

`docs/PRODUCTION_ROADMAP.md` exists only on the local `main` branch (commit `ec33096`,
authored 2026-09-17T10:48:48+05:00) as of this writing — it has not yet reached
`origin/main`. This worktree's own branch tip was one commit behind `origin/main` at the
same commit `origin/main` was at, so this report reads that roadmap from local `main` via
`git show main:docs/PRODUCTION_ROADMAP.md` rather than from this worktree's own checkout.

## Top findings

1. **"aspose.org" is a real, currently active GitHub repository — but not at the address
   this project already recorded.** `migration/reuse-manifest.yaml` names the reuse source
   as `babar-raza/aspose.org`; that address does not resolve (`gh repo view` returns 404).
   The actual repository is **`Aspose/aspose.org`** — private, owned by the `Aspose`
   GitHub org, not a personal account — last pushed 2026-09-17T02:30:45Z (today, still
   under active development by someone).
2. **It does contain a genuine repository-discovery module**, not just the ecosystem-truth
   extraction engine this project already pulled from it on 2026-09-06
   (`docs/RESEARCH_AND_GUIDELINES.md` §29, `migration/reuse-manifest.yaml` `aspose-org`
   file records). `scripts/pipeline/lib/org_scanner.py` and
   `scripts/pipeline/commands/ops/update_product_registry.py` implement authenticated,
   paginated, rate-limit-aware GitHub org scanning with fail-closed semantics that closely
   match `plans/idea.md`'s Gate C0 language. This was not previously pulled or evaluated by
   this project.
3. **Its registry schema is weaker than this project's own.** `data/products.json` in
   `Aspose/aspose.org` carries no stable provider identity (`repository_id`/`node_id`) at
   all — it identifies repositories by name/URL, exactly the anti-pattern
   `plans/idea.md` warns against. `data/registry.json` here already improved on that.
   Reusing the scanning *mechanism* is promising; reusing its registry *shape* would be a
   regression.
4. **The GitHub numeric `repository_id` is confirmed stable across rename/transfer;
   `node_id` is not unconditionally so** — GitHub ran a platform-wide GraphQL ID
   re-encoding (2021–2022) that changed `node_id` values for existing repositories
   independent of any rename or transfer. This project's schema currently treats both
   fields as equally load-bearing identity (`validate_stable_identities` enforces
   uniqueness on both). See §3.4.
5. **`Aspose/aspose.org`'s own discovery orchestrator already knows about 13 additional
   Aspose FOSS product families** (`aspose-cad-foss`, `aspose-diagram-foss`,
   `aspose-drawing-foss`, `aspose-finance-foss`, `aspose-gis-foss`, `aspose-imaging-foss`,
   `aspose-medical-foss`, `aspose-ocr-foss`, `aspose-omr-foss`, `aspose-pub-foss`,
   `aspose-svg-foss`, `aspose-tasks-foss`, `aspose-zip-foss`) beyond the 13 families
   currently in this project's 34-entry registry. This is concrete, sourced evidence for
   what "more products/repos" likely means.

## 1. Current registry shape

Source files read: `data/registry.json`, `schemas/registry.schema.json`,
`src/repository_presenter/core/registry/models.py`,
`src/repository_presenter/core/registry/loader.py`.

`data/registry.json` (`schema_version: 1`) currently holds **34 entries** across **13
families**: `3d`, `barcode`, `cells`, `email`, `font`, `html`, `note`, `page`, `pdf`,
`psd`, `slides`, `tex`, `words`. `data/products.json` does not exist anywhere in this
repository — `plans/idea.md`'s own text still names `data/products.json` as "the hard
execution allow-list" (carried over verbatim from the legacy project per the authority
note at the top of `plans/idea.md`), but the executable successor is `data/registry.json`;
this naming drift between the plan text and the implemented schema is worth a formal note
somewhere the next reader of `plans/idea.md` will see it, since a naive read would go
looking for a file that isn't there.

Each entry (`schemas/registry.schema.json`, `additionalProperties: false`):

| Field | Type | Notes |
|---|---|---|
| `repository` | `"owner/name"` string | pattern-validated |
| `family` | string | e.g. `"pdf"` |
| `platform` | string | e.g. `"python"` |
| `ecosystem` | string | lowercase identifier, e.g. `"python"`, `"net"` |
| `mode` | `"full" \| "dry_run" \| "disabled"` | **governs publication readiness, never read eligibility** (`models.py` docstring) |
| `policy_profile` | string | per-repository/family policy overlay name |
| `active` | bool | declared in the schema; **a repo-wide grep found zero consumers of this field anywhere in `src/`** — it is currently vestigial |
| `provider_identity` | object | `{provider: "github", repository_id: int>0, node_id: string}` |

Two gates in `loader.py`:

- `require_listed` — the **read gate**: presence in the registry is the only
  authorization needed to analyze a repository, regardless of `mode`.
- `is_permitted` — the stricter **write gate**: returns `None` (refuses) when
  `mode == "disabled"`. A disabled entry is analyzed but never proposed to.

This means the schema **already implements** `plans/idea.md`'s "new eligible repositories
enter disabled and read-only" requirement, with no change needed: two production entries
(`aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`, `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`)
already sit at `mode: "disabled"`, `active: true` today, demonstrating the exact target
state for a newly discovered repository once admitted.

`Registry.validate_stable_identities` (`models.py`) fails closed on any two entries
sharing a `repository` (casefolded), a `repository_id`, **or** a `node_id`. Any discovery
or intake process must not collide with an existing entry on any of the three.

## 2. What "aspose.org" actually is

### 2.1 What this machine's `GitHub` folder actually contains

`D:\Users\prora\OneDrive\Documents\GitHub\` holds, among others: `products.aspose.app`,
`products.aspose.app-workflows`, `products.aspose.cloud`,
`products.aspose.cloud-workflows-shallow`, `products.aspose.com`,
`products.aspose.com-configs`, `products.aspose.com-shallow`,
`products.aspose.com-workflows-shallow`. **No directory named `aspose.org` or anything
resembling it exists on this machine.** These `products.aspose.*` directories are storefront
website checkouts (per their `-workflows`/`-configs`/`-shallow` siblings, they look like
partial/shallow mirrors kept for reference); a spot check was not performed on their
contents for discovery code because the stronger lead below made it unnecessary, but their
names alone do not match "aspose.org" and they were not the source `migration/reuse-
manifest.yaml` already names.

### 2.2 What this repository already recorded about aspose.org

`docs/RESEARCH_AND_GUIDELINES.md` §29 and `plans/idea.md`'s "Ecosystem truth" bullet
already document a **prior, different** reuse decision (owner, 2026-09-04): the sibling
`aspose.org` pipeline's *extraction* modules are a second reuse source under the same pull
discipline as the retired legacy project (pinned revision, one file record per file,
ported tests, cut import closure, typed façade — never a runtime dependency).
`migration/reuse-manifest.yaml` records this as source id `aspose-org`:

```yaml
- id: aspose-org
  repository: babar-raza/aspose.org
  url: https://github.com/babar-raza/aspose.org
  frozen_revision: 16d75e95d4e8205d8106896bf11c8167d00e7e1f
  revision_verified: true
  revision_metadata:
    verified_at: "2026-09-06"
    ...
  working_tree_at_freeze:
    status: DIRTY
    modified_tracked_files: 424
    untracked_files: 60
    ...
```

Eight files were pulled under work item G4-W09 (`PORT_NEARLY_INTACT` disposition) and now
live at
`src/repository_presenter/components/readme/extractors/surface/_vendor/aspose_extraction/`:
`publication_probe.py`, `package_registries/{__init__,cargo,go,npm,nuget,pypi}.py`,
`package_manifest.py`, `package_root.py`, `api_surface.py`, `tree_helpers.py`,
`lang/{__init__,cpp,csharp,go,java,python,rust,typescript}.py`. **All of these are
ecosystem-surface extraction (public API surface, package-registry publication checks,
manifest parsing) — none of them are repository discovery.** This is the reuse `plans/
idea.md`'s "Ecosystem truth" bullet already authorized; it is a different workstream from
the one this investigation was commissioned to examine.

### 2.3 The recorded address does not resolve

This session is authenticated as GitHub user `babar-raza` (`gh auth status`, confirmed
live). `gh repo view babar-raza/aspose.org` returns:

```
GraphQL: Could not resolve to a Repository with the name 'babar-raza/aspose.org'. (repository)
```

`gh repo list babar-raza --limit 200` (43 repositories) contains no `aspose.org` entry,
under that or any variant name. Either the repository was transferred away from the
personal account after the 2026-09-06 pull (plausible — its own `working_tree_at_freeze`
note already records "The checkout's HEAD has since moved to `0a4d627c`", i.e. it kept
being actively developed after the pull), the manifest recorded the wrong owner from the
start, or it was renamed. This project's own registry schema exists precisely to survive
this kind of drift via `repository_id`/`node_id` — but the reuse manifest for aspose.org
predates that discipline being applied to *itself* and only records a URL/owner string.

### 2.4 The actual repository

`gh api user/orgs` lists the organizations this account belongs to, including one named
simply `Aspose` (distinct from the many `aspose-<family>-foss` per-product orgs).
`gh repo list Aspose --limit 300` finds:

```
aspose.org
aspose.org-workflows
```

`gh repo view Aspose/aspose.org`:

```json
{
  "defaultBranchRef": {"name": "main"},
  "description": "Theme, frontmatter and skill set for content generation across aspose.org site sections",
  "isPrivate": true,
  "name": "aspose.org",
  "pushedAt": "2026-09-17T02:30:45Z",
  "url": "https://github.com/Aspose/aspose.org"
}
```

This is almost certainly the same codebase `migration/reuse-manifest.yaml` pinned at
`16d75e95d4` — the file layout matches exactly (`scripts/pipeline/lib/`,
`scripts/pipeline/extraction/`, the same file names) — just under its current, correct
owner. **Recommendation: correct the `aspose-org` source's `repository`/`url` fields in
`migration/reuse-manifest.yaml` to `Aspose/aspose.org` /
`https://github.com/Aspose/aspose.org`** once the owner confirms this is the same
repository (see open question 1).

Everything below was read via the read-only GitHub Contents API
(`gh api repos/Aspose/aspose.org/contents/...`) — no clone was made, no code was pulled or
copied into this project, and nothing here changes the pull-discipline status of any file.

### 2.5 What is actually inside it, relevant to discovery

Top-level layout includes `AGENTS.md`, `CLAUDE.md`, `CODEX.md`, `AUTONOMOUS_EXECUTION_
CONTRACT.yaml`, `MISSION_AUTHORITY.yaml` — this is a sibling project run under the same
kind of autonomous-agent operating discipline as this one, not a simple static site repo.
Its `scripts/pipeline/` directory (own `INVENTORY.md`/`PIPELINE.md`) is large: `audit/`,
`commands/` (11 subdirectories: `content`, `diagnostics`, `enrichment`, `foss`,
`governance`, `healing`, `kilocode`, `knowledge`, `launch`, `migration`, `ops`,
`websites`), `content_eval/`, `core/`, `evidence/`, `extraction/`, `knowledge/`, `lib/`
(~100 files), `scout_enrichers/`, `tools/`, `verification/`.

**The discovery-relevant files:**

- **`scripts/pipeline/lib/org_scanner.py`** — "GitHub organisation scanner. Scans a
  GitHub organisation for repositories and returns structured metadata." Public API:
  `resolve_token(explicit=None) -> (token, auth_mode)`,
  `preflight(org, *, token=None) -> None` (raises `TokenRejected`),
  `scan_org(org, *, token=None, per_page=100, max_rate_wait=300) -> list[dict]`,
  `scan_orgs(orgs, *, token=None, max_rate_wait=300) -> (list[dict], list[dict])`.
  Each repo dict currently returns: `name`, `full_name`, `html_url`, `clone_url`,
  `pushed_at`, `archived`, `description` — **no `id`, no `node_id`** (see gap analysis,
  §3.4). `scan_orgs` additionally returns one typed **outcome** dict per org:
  `{"org", "status": "ok"|"auth_denied"|"rate_limited"|"not_found"|"http_error"|
  "network_error", "repo_count", "detail"}` — its own docstring states the design intent
  in almost `plans/idea.md`'s own words: *"a failed scan is NEVER reported as an empty
  success... so callers can distinguish 'this org has no matching repos' from 'this org
  was never reached'."* GitHub overloads HTTP 403 for both rate-limiting and
  authorization/policy denial; the module disambiguates via `Retry-After` and
  `X-RateLimit-Remaining` headers rather than status code alone — its own comment records
  a fixed historical bug where the conflation caused "a ~54-minute sleep per org against a
  token the org will never accept."

- **`scripts/pipeline/commands/ops/update_product_registry.py`** — the write-side
  orchestrator. Docstring:

  ```
  Modes:
      Default:      Scan GitHub org for FOSS repos, merge with local knowledge dirs.
      --local-only: Skip GitHub — build registry from knowledge/ dirs only.
      --force:      Overwrite active/inactive status even for repos already in registry.
      --reconcile:  Read-only check: verify all 8 content/knowledge/package-registry
                    signals for each registered product...

  Exit codes:
      0  registry written (or dry-run/reconcile OK)
      1  --reconcile found a MISSING/STALE signal, or a read error
      2  no credential, or the GitHub scan reached no org — the tracked registry is
         left UNCHANGED rather than rewritten from unverified data (ST-058)
  ```

  Exit code 2 is exactly the fail-closed behavior `plans/idea.md` demands: an incomplete
  or failed scan must never silently produce a truncated registry. It scans a fixed
  default list of **26** `aspose-{family}-foss` organizations (`_DEFAULT_ORGS`,
  overridable via the `ASPOSE_ORG` env var — see §3.5 for the family gap this reveals),
  and classifies each repository name with three regexes: the canonical
  `Aspose.{Family}-FOSS-for-{Platform}` form (case-insensitive — a live 2026-09-11 fix,
  see below), a lowercase `aspose-{family}-foss-for-{platform}` form, and a legacy
  `aspose-{family}-{platform}` form. A code comment records a real classification miss:
  the case-sensitive pattern silently failed to classify `Aspose.Imaging-Foss-for-.NET`
  (mixed-case "Foss") with no error, fixed by making the match case-insensitive.

- **`data/registry_exclusions.json`** — a small, hand-curated, evidence-backed exclusion
  ledger (2 entries at the sampled snapshot):

  ```json
  {
    "match": "repo_name",
    "value": "Aspose-PDF-FOSS-for-Go-MCP",
    "repo_url": "https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP",
    "reason": "MCP (Model Context Protocol) server exposing the pdf/go library, not a
      language-SDK port. Has no class/method API surface for repo-scout to extract...",
    "excluded_at": "2026-07-28",
    "resolved_via": "gap-escalation-pending"
  }
  ```

  and one excluding every org's generic `.github` community-health profile repository
  ("case-insensitive and org-agnostic, so any org's `.github` profile repo is covered by
  this one entry"). This is precisely the "every exclusion is explicit and evidence-
  backed" discipline `plans/idea.md`'s Gate C0 requires — repository-presenter has no
  equivalent file today.

- **`data/products.json`** — 33 entries at the sampled snapshot. Schema:

  ```json
  {
    "family": "3d",
    "platform": "java",
    "repo_name": "Aspose.3D-FOSS-for-Java",
    "repo_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java",
    "clone_url": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java.git",
    "active": true,
    "discovered_via": "github"
  }
  ```

  No `repository_id`, no `node_id` — identity is `repo_name`/`repo_url` only. See §3.4.

- **`scripts/pipeline/lib/product_registry.py`** — a read-side loader whose own docstring
  explains a real, previously-live bug this project should learn from without repeating
  it: install-command text was historically generated from three independently-maintained,
  disagreeing sources (`data/package_registry.json`, a hardcoded branch in one command,
  and a hand-maintained dict in another); this module is the shared loader that replaced
  duplicated identity logic with one read path. It also documents a **second, sharper**
  problem directly relevant to Gate C0: a product can be excluded in
  `registry_exclusions.json` (e.g. `cells/typescript`, `BLOCKED_REPO_NOT_LAUNCHABLE` for
  missing LICENSE, boilerplate README, and a non-Aspose `package.json` name) **while its
  `data/products.json` record still says `active: true`**, because nothing re-runs the
  merge/enforcement step on every read — this loader exists specifically to reproduce the
  exclusion check read-side so consumers don't trust the stale `active` flag directly.

- **`scripts/pipeline/commands/diagnostics/repo_patrol.py`** — referenced by name inside
  the `.github`-exclusion reason ("without this entry it re-surfaces as 'unclassifiable'
  noise on every `/repo-patrol` scan") as the pass that surfaces ambiguous/unmatched
  repository names for triage — the closest analogue in that codebase to the
  "ambiguous"/"unmatched" observation categories `plans/idea.md` names for Gate C0. Not
  read in full for this investigation; named here as a concrete pointer for later reuse
  evaluation.

Note also `scripts/pipeline/lib/registry_observation_ledger.py`, which despite the
similar name is **not** the discovery ledger — its own docstring is explicit that it
records per-tick *package-registry publication* observations (family/platform/registry_
type, `published`/`ambiguous`/`method`/`live_version`), i.e. the same kind of thing this
project's already-vendored `publication_probe.py` does, not repository/org discovery.
Anyone skimming file names in that `lib/` directory should not conflate the two.

## 3. What authenticated all-visibility pagination actually requires

### 3.1 API shape

`org_scanner.py`'s proven implementation uses the **REST** API,
`GET /orgs/{org}/repos?per_page=100&page=N` (not GraphQL), paginating by page number with a
fixed inter-page sleep. This is a reasonable, already-battle-tested choice: REST repo
listing is simple, well-documented, and this module already has real production mileage
(the case-sensitivity and 403-disambiguation fixes above are evidence of that, not
theoretical design). A GraphQL implementation could combine repository + relationship
data in fewer round trips, but nothing in this investigation found a concrete need for that
here.

### 3.2 All-visibility and scope

`/orgs/{org}/repos` returns public, private, and internal repositories visible to the
authenticated identity's org membership and token scope — never anonymously. This
session's own live `gh auth status` output is a direct demonstration of the exact failure
mode `plans/idea.md` is implicitly guarding against:

```
✓ Logged in to github.com account babar-raza (GH_TOKEN)
  ...
  ! Missing required token scopes: 'read:org'
```

Even this session's own credential could not necessarily complete a full all-visibility
org scan today until that scope is granted — a live, concrete instance of the "source
failures" and "pending intake" states Gate C0 requires the system to detect and record
rather than silently under-count.

### 3.3 Rate limits and credential policy

`gh api rate_limit` during this investigation showed the standard `5,000/hour` REST quota
with `5000` remaining (fresh window). `org_scanner.py`'s own `_RATE_SLEEP = 1.0` between
paginated requests and its `_is_rate_limited`/`_rate_wait_seconds` helpers (distinguishing
HTTP 429, `Retry-After`, and `X-RateLimit-Remaining == 0` from a plain authorization-denial
403) are a solid, already-proven reference design.

Separately, and load-bearing for `plans/idea.md`'s own credential rules: `org_scanner.py`'s
`resolve_token` prefers `GH_TOKEN` over `GITHUB_TOKEN` specifically because *"the
aspose-\*-foss orgs reject fine-grained PATs whose lifetime exceeds 366 days; the classic
PAT in `GH_TOKEN` is accepted. Confirmed live 2026-08-05."* `GITHUB_TOKEN` is exactly what
GitHub Actions injects by default, and is a fine-grained token. `plans/idea.md`'s own
production model calls for a GitHub App's short-lived installation tokens instead of either
of these — a different credential type again, whose acceptance against these same orgs'
policy has **not** been verified anywhere this investigation found. This is worth an
explicit, isolated check before relying on it in production (see §6).

### 3.4 Provider identity stability — confirmed, with a caveat

`plans/idea.md` wants "stable provider identity" specifically to survive renames and
transfers, and this project's registry already carries `provider_identity.repository_id`
(numeric) and `.node_id` (GraphQL global ID) toward that end. Checked externally during
this investigation (see Sources):

- The numeric **`repository_id`** (database ID) is documented/confirmed by GitHub
  community discussion (and consistent with GitHub's own stated design — repositories are
  tracked internally by `id`, not `full_name`, precisely because `full_name` changes on
  rename or transfer) to **not change** across either operation. This is the correct
  anchor for anti-rename/anti-transfer detection.
- The **`node_id`** (GraphQL global ID) is **not** unconditionally stable. GitHub
  announced a platform-wide GraphQL global-ID re-encoding in November 2021 ("GraphQL
  global ID migration"), and a documented case (GitHub community discussion #35719) shows
  an organization's and its repositories' `node_id` values changing between October 5–10,
  2022 as accounts were migrated to "the new `next ID`" format — same repository, same
  numeric `id`, different `node_id` string before and after, with no rename or transfer
  involved at all.

This project's `Registry.validate_stable_identities`
(`src/repository_presenter/core/registry/models.py`) currently enforces uniqueness on
`repository_id` **and** `node_id` equally, which is fine for catching an accidental
duplicate entry. But if a future drift-detection design were to treat a `node_id` mismatch
against a previously-recorded value as evidence "this is now a different repository" (the
literal anti-transfer signal Gate C0 wants), it would produce a false positive the next
time GitHub performs a similar platform-wide re-encoding — which has already happened once
and is not a one-off promise never to recur. **Recommendation: treat `repository_id` as
the authoritative, load-bearing anti-rename/anti-transfer signal; treat `node_id` as
corroborating/informational, refreshed from a live lookup rather than compared strictly
against a frozen historical value.**

### 3.5 The family gap

`update_product_registry.py`'s `_DEFAULT_ORGS` names exactly the 13 families already in
this project's registry (`3d`, `barcode`, `cells`, `email`, `font`, `html`, `note`, `page`,
`pdf`, `psd`, `slides`, `tex`, `words` → `aspose-<family>-foss`) **plus 13 more**: `cad`,
`diagram`, `drawing`, `finance`, `gis`, `imaging`, `medical`, `ocr`, `omr`, `pub`, `svg`,
`tasks`, `zip` — 26 organizations in total. This is concrete, sourced evidence for what the
owner most likely means by "more products/repos to add": a sibling system already
enumerates twice as many Aspose FOSS product families as this project's registry currently
covers.

## 4. Minimal discovery-pass output and safe intake shape

The registry schema (§1) already has a place for an admitted-but-unreviewed repository:
`mode: "disabled"`, `active: true`. **No schema change is needed for that state alone** —
this project's own PSD entries already demonstrate it in production.

What is missing is not a place to put an admitted entry, but somewhere to put everything
Gate C0 also requires that is *not* an admitted entry: excluded-as-noise, ambiguous,
inaccessible, unmatched-name, renamed, transferred, source-failed observations. None of
these fit `data/registry.json` (`additionalProperties: false`, modeling only admitted
repositories) and none should be force-fit into it.

A minimal, safe design (sketch only — no implementation follows from this report):

- A **staging/observation artifact**, never merged into `data/registry.json`
  automatically (e.g. under `data/discovery/` or `evidence/`), holding one record per
  repository actually observed during a scan: `provider_identity` (`repository_id`,
  `node_id`), current `full_name`, org, visibility, `archived`, `pushed_at`, and a
  disposition drawn from `plans/idea.md`'s own Gate C0 vocabulary (e.g.
  `candidate_admit`, `excluded_noise`, `excluded_fork`, `ambiguous_name`, `renamed`,
  `transferred`, `inaccessible`, `source_failed`).
- A separate, hand/agent-reconciled step turns each `candidate_admit` observation into a
  new `data/registry.json` entry at `mode: "disabled"`, and every excluded/ambiguous/
  failed observation into an explicit, evidence-backed exclusion record — `Aspose/
  aspose.org`'s `data/registry_exclusions.json` shape (`match`, `value`, `reason`,
  `excluded_at`/`observed_at`, `resolved_via`) is a reasonable template for that half.
- Nothing writes to `data/registry.json` directly from an automated scan. This preserves
  this project's existing design intent stated in `loader.py`'s own docstring — "presence
  in the registry is the only authorization needed" — by keeping that presence a
  deliberate, reviewable act, never a scan side effect.
- `active`'s intended meaning for intake is currently undefined (§1) — before it is used
  to distinguish "admitted, not yet vetted" from `mode: disabled` alone, that needs an
  explicit decision, since right now it is `true` on all 34 entries and drives no logic
  anywhere in `src/`.

## 5. In-scope vs. noise criteria

- `update_product_registry.py`'s three-regex classifier (canonical `Aspose.{Family}-FOSS-
  for-{Platform}`, lowercase `-foss-for-` variant, and a legacy `aspose-{family}-
  {platform}` form, all case-insensitive after the 2026-09-11 fix) is a working, tested
  precedent for "does this repository's name match the product convention," including a
  documented real miss (case-sensitivity) worth learning from rather than rediscovering.
- Its exclusions file demonstrates two concrete, already-adjudicated noise classes: (a)
  non-SDK companion repositories with no class/method API surface to extract (its MCP-
  server example), and (b) GitHub's own generic `.github` org-profile repository, present
  in every organization and never a product.
- `_ACTIVE_PUSH_DAYS = 180` — `Aspose/aspose.org` treats "no push in 180 days" as a
  recency-based activity signal feeding its own `active` flag, independent of the
  `archived` flag GitHub itself reports. This project's `mode`/`active` fields today are
  set by human/agent decision, not push recency; whether staleness should ever *auto*-
  demote an admitted repository, or only ever surface as an observation for a human/agent
  to reconcile, is an open design choice — `plans/idea.md`'s "zero unexplained
  observations... required for portfolio completeness" language reads as favoring the
  latter (surface, never silently auto-act).
- GitHub's repo API returns explicit `fork` and `archived` booleans per repository.
  `plans/idea.md` explicitly wants archived repositories recorded as their own
  disposition, not silently admitted or silently dropped. Neither of `Aspose/aspose.org`'s
  two current exclusion entries is fork- or archived-based, so that codebase does not yet
  supply a tested precedent for how to handle a fork of an admitted product (e.g., a
  contributor's fork under a different owner) — this remains an open question (see §7.5)
  rather than something this investigation can report as already solved elsewhere.

## 6. Concrete next steps

1. Ask the owner to confirm `Aspose/aspose.org` (private, org-owned) is the intended reuse
   source (§2.4), and on confirmation, correct `migration/reuse-manifest.yaml`'s
   `aspose-org` source `repository`/`url` fields, which currently point at a
   `babar-raza/aspose.org` address that does not resolve.
2. Decide, under the existing pull discipline (`docs/RESEARCH_AND_GUIDELINES.md` §29),
   whether `org_scanner.py` and `update_product_registry.py` become a **new class** of
   pull target alongside the six extraction files already vendored — this is functionally
   different territory (org enumeration vs. ecosystem-surface extraction) and should not
   be silently folded into the existing G4-W09 pull's scope.
3. Any ported/adapted scanner needs to be extended, not used as-is, to capture `id` and
   `node_id` per repository from the GitHub API response — the upstream module's returned
   dict has neither field today, because its own registry schema never needed them.
4. Design the staging/observation artifact and its reconciliation step (§4) in a
   follow-up, implementation-track document before any discovery code is written.
5. Verify, in isolation, whether the GitHub App installation token `plans/idea.md`'s
   production model calls for is actually accepted by the `aspose-*-foss` orgs' policy
   that is already known to reject long-lived fine-grained PATs — untested as of this
   report.
6. Log or fix the live finding that this session's own `GH_TOKEN` account is missing the
   `read:org` scope a full all-visibility scan would need.

## 7. Open questions for the owner

1. Is `Aspose/aspose.org` (org-owned, private, pushed 2026-09-17) definitely the system
   you meant by "aspose.org," or is there a different, more literal target this
   investigation should also check — a live site admin panel, a different internal
   database, something not reachable as a GitHub repository at all?
2. Should the org-scanning mechanism (`org_scanner.py` / `update_product_registry.py`) be
   pulled under the existing pull discipline (pinned revision, file records, ported
   tests), reimplemented from scratch given it needs a materially different output shape
   (stable provider identity) than its source ever needed, or something in between (pull
   the scanning primitives, write new orchestration)?
3. Should discovery ever run against all 26 `aspose-*-foss` organizations `Aspose/
   aspose.org` already scans, or only a subset — and who decides which of the 13
   currently-unrepresented families (`cad`, `diagram`, `drawing`, `finance`, `gis`,
   `imaging`, `medical`, `ocr`, `omr`, `pub`, `svg`, `tasks`, `zip`) are actually in scope
   for this project versus intentionally out of scope?
4. What should `active: false` mean once discovery exists? It does no work in `src/`
   today — is it meant to be the "admitted but not yet vetted" state distinct from `mode:
   disabled`, or should it be repurposed or retired?
5. Should archived repositories and forks ever be silently excluded, or must every one
   always produce an explicit, dated, evidence-backed exclusion record, matching
   `plans/idea.md`'s "every exclusion is explicit and evidence-backed" line? `Aspose/
   aspose.org`'s own exclusions file doesn't answer this yet — neither of its two entries
   is fork- or archived-based.

## Sources consulted (external, read-only)

- GitHub community discussion — repositories are tracked by `id`, not `full_name`, which
  can change on rename/transfer: <https://github.com/orgs/community/discussions/29784>
- GitHub community discussion — organization and repository `node_id` values changed
  2022-10-05–10 as part of a global-ID re-encoding, referencing GitHub's November 2021
  "GraphQL global ID migration update" post:
  <https://github.com/orgs/community/discussions/35719>
- Greptile — "Every GitHub Object Has Two IDs" (technical structure of the numeric
  database ID vs. the GraphQL node ID): <https://www.greptile.com/blog/github-ids>
- GitHub Docs — Transferring a repository:
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>

All other findings in this report are drawn directly from this repository's own files
(`data/registry.json`, `schemas/registry.schema.json`,
`src/repository_presenter/core/registry/{models,loader}.py`,
`migration/reuse-manifest.yaml`, `docs/RESEARCH_AND_GUIDELINES.md`, `plans/idea.md`,
local `main`'s `docs/PRODUCTION_ROADMAP.md`) and from live, read-only `gh`/GitHub-API
calls made during this session (`gh repo view`, `gh repo list`, `gh api user/orgs`,
`gh api repos/Aspose/aspose.org/contents/...`, `gh api rate_limit`).

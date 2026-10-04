# Upstream-issue approvals (owner-only)

An upstream-defect handoff under `evidence/upstream-defects/` is filed as a GitHub issue in the
target repository only if a file in this directory approves **that exact handoff**. The repository
variable `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` is only a kill switch: it can stop all
filing, and it can never authorize one. An empty directory (apart from this file) means nothing is
approved.

## Approving one handoff (owner act)

1. Read the handoff's `suggested_issue_title` / `suggested_issue_body` and its evidence. It will be
   posted verbatim, under the target repository's name, to that repository's issue tracker.
2. Run `repository-presenter file-upstream-defects --repo <owner>/<name>`. For an unapproved
   handoff it prints the file name to create and the `evidence_digest` to use.
3. Commit `ops/issue_approvals/<handoff-id>.json` (a human-authored commit, through a reviewed PR):

   ```json
   {
     "handoff_id": "<owner>__<name>__<64 hex fingerprint>",
     "repository": "<owner>/<name>",
     "evidence_digest": "sha256:<64 hex>",
     "approver": "<your GitHub login>",
     "approved_at": "2026-10-05T12:00:00Z",
     "expires_at": "2026-10-12T12:00:00Z"
   }
   ```

   `expires_at` must be after `approved_at` and at most 30 days later. Timestamps are UTC strings.

4. Re-run the dry run; the handoff must now read `WOULD-FILE`.

## What invalidates an approval

- Any change to the handoff's target, revision, fingerprint, triggering check, evidence, claim,
  title or body changes its digest: the old record is refused (`approval digest mismatch`) and a
  new one is needed.
- Expiry (`expires_at`), a record naming another repository, a bot-authored or bot-committed
  record, or a record that is not committed in the run's own checkout commit.
- Deleting or reverting the file withdraws the approval.

## Why a run cannot approve itself

Records are read from the git commit a workflow run was triggered on, never from its working tree.
The scheduled workflow holds `contents: read` only and persists no checkout credential, so no step
can push one. Protect this directory with branch protection or CODEOWNERS so only the owner's
review can add a file here.

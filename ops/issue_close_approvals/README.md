# Upstream-issue close approvals (owner-only)

Closing an issue this system filed is a write to a product repository. A scheduled run closes one
only if a file in this directory approves **that exact issue** for **that exact reason**. The
repository variable `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` is only a kill switch, and an
approval to *file* a handoff (`ops/issue_approvals/`) never authorizes a close. An empty directory
(apart from this file) means nothing may be closed.

## Approving one close (owner act)

1. Read the dry-run report (`repository-presenter redetect-upstream-defects --repo <owner>/<name>`).
   For a `FILED` handoff whose check no longer fires it prints either `would close #N (reason)` or
   `would not close: ...`, and, when only the approval is missing, the file name and fields to use.
2. Decide that the check's verdict is right: `completed` means the maintainers fixed it at a revision
   that moved; `not_planned` means the check changed or the original finding was a false positive.
3. Commit `ops/issue_close_approvals/<handoff-id>.json` (a human-authored commit, through a reviewed PR):

   ```json
   {
     "handoff_id": "<owner>__<name>__<64 hex fingerprint>",
     "repository": "<owner>/<name>",
     "issue_number": 42,
     "close_reason": "completed",
     "evidence_digest": "sha256:<64 hex>",
     "approver": "<your GitHub login>",
     "approved_at": "2026-10-05T12:00:00Z",
     "expires_at": "2026-10-12T12:00:00Z"
   }
   ```

   `expires_at` must be after `approved_at` and at most 30 days later. `close_reason` is GitHub's own
   `completed` or `not_planned`.

## What stops a close even with a valid record

- The registry entry for the target is not mode `full`, or is inactive or unlisted.
- `issue_number` differs from the issue the handoff recorded as filed, or `close_reason` differs
  from the reason the check proves at close time, or the handoff's evidence digest changed.
- The record is expired, dated in the future, bot-authored, not committed in the run's own checkout
  commit, or names another repository.
- The write token is not an installation token scoped to exactly the target.
- The live issue is not open, is a pull request, or does not carry this handoff's fingerprint marker
  (a comment `<!-- repository-presenter-defect: sha256:... -->` in its body): the system closes only
  issues it filed.

Deleting or reverting the file withdraws the approval. Protect this directory with branch protection
or CODEOWNERS so only the owner's review can add a file here.

#!/usr/bin/env bash
# Warns (never fails) when this checkout is far behind origin/main. ci_check.sh runs it in its
# preflight so staleness is reported where every commit and push passes, not only when the import
# root happens to be wrong (scripts/check_import_root.py).
#
# Measure: the commits on origin/main that HEAD does not contain, i.e. how far HEAD's merge-base
# with origin/main is behind. A warning (exit 0) when that exceeds the threshold. Warn-only on
# purpose: under churn a branch is legitimately a few commits behind, and a gate here would block
# merges for a condition a rebase fixes in seconds.
#
# Threshold: 20 commits (override: RP_STALE_COMMITS=<n>). Measured 2026-10-05: main took 59
# commits in the previous day (about 2.5 an hour; 105 in a week). 20 is roughly one working
# session's worth of other people's merges: below it a rebase is routine noise, above it the base
# is old enough that tests and imports can disagree with what main now says. A threshold under ~10
# would warn on nearly every long-lived branch, and a warning that is always on is ignored.
#
# Freshness: the count is only as fresh as origin/main, so unless RP_STALE_FETCH=0 the script first
# runs `git fetch origin main` (bounded to 20 seconds, no credential prompt, failure tolerated). It
# is skipped on GitHub Actions, where the checkout is the merge ref and has no origin/main to trust.
#
# Usage: scripts/check_staleness.sh        (always exits 0)
set -u

unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_NAMESPACE GIT_PREFIX

THRESHOLD="${RP_STALE_COMMITS:-20}"
case "$THRESHOLD" in ""|*[!0-9]*) THRESHOLD=20 ;; esac

[ -z "${GITHUB_ACTIONS:-}" ] || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

if [ "${RP_STALE_FETCH:-1}" != "0" ] && git remote get-url origin >/dev/null 2>&1; then
  if command -v timeout >/dev/null 2>&1; then
    GIT_TERMINAL_PROMPT=0 timeout 20 git fetch origin main --quiet >/dev/null 2>&1 || true
  else
    GIT_TERMINAL_PROMPT=0 git fetch origin main --quiet >/dev/null 2>&1 || true
  fi
fi

git rev-parse --verify --quiet refs/remotes/origin/main >/dev/null || exit 0
behind="$(git rev-list --count HEAD..refs/remotes/origin/main 2>/dev/null)" || exit 0
if [ "$behind" -gt "$THRESHOLD" ]; then
  base="$(git merge-base HEAD refs/remotes/origin/main 2>/dev/null | cut -c1-8)"
  echo "ci_check.sh: WARNING this checkout is $behind commits behind origin/main (merge-base ${base:-unknown}; threshold $THRESHOLD)."
  echo "  Its code, and what a shared venv imports, may be stale. Start new work with scripts/new_worktree.sh <name> <branch>,"
  echo "  refresh the main checkout with scripts/sync_main.sh, or bring this branch up to date with origin/main (docs/REPOSITORY_LAYOUT.md, Branching and worktrees)."
  echo
fi
exit 0

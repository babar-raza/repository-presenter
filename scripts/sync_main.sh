#!/usr/bin/env bash
# Fast-forwards the LOCAL main branch to origin/main, and only when that is provably safe.
#
# Why: pushes and PR merges update origin/main on GitHub only. The local `main` ref (and, in the
# main checkout, its working tree and the editable install the shared .venv points at) stays where
# the last explicit fetch left it. Agents work in git worktrees; anything that branches from local
# `main` or imports code from the main checkout then runs stale code (2026-10-05: false version
# mismatches in tests; scripts/check_import_root.py detects the import side, this removes the cause).
# Branch NEW work from origin/main with scripts/new_worktree.sh; use this to keep the main checkout
# itself current. Workflow: docs/REPOSITORY_LAYOUT.md "Branching and worktrees".
#
# Usage: scripts/sync_main.sh [--check]       (any checkout or worktree of this repository)
#   --check   fetch and report only; change nothing.
# Windows: run it with Git for Windows bash (not the WSL bash.exe in System32):
#   & "C:\Program Files\Git\bin\bash.exe" scripts/sync_main.sh
#
# Steps: `git fetch origin --prune`; compare local main with origin/main; then
#   - main checked out in some worktree (normally the main checkout): `git merge --ff-only
#     origin/main` run there, after the safety checks below;
#   - main checked out nowhere (or absent): `git fetch origin main:main`, which git itself limits to
#     a fast-forward.
# Nothing else is ever run: no reset, clean, stash, checkout, rebase, force, or branch deletion.
#
# Output: exactly one line, "sync_main: <STATUS> ...". Exit 0: OK (fast-forwarded), UP_TO_DATE, or
# --check's report. Exit 1: REFUSED <code> (nothing was changed; the line says what to do). Exit 2:
# ERROR (cannot decide: no origin, fetch failed). Refusal codes:
#   DIRTY            the main checkout has uncommitted tracked changes (staged or unstaged)
#   DIVERGED         local main has commits that are not on origin/main
#   OP_IN_PROGRESS   a merge, rebase, cherry-pick, revert or bisect is in progress there
#   UNTRACKED_CLASH  the fast-forward would overwrite untracked files; git aborted, files intact
#   FF_FAILED        git refused the fast-forward for another reason (its message is included)
# Idempotent: when main already equals origin/main it only reports UP_TO_DATE, even if the main
# checkout is dirty. It cannot see other processes: do not run it while tests or a build run from
# the main checkout, because a fast-forward rewrites the files they import.
set -u

# A hook or an outer git exports these and they outrank -C (see .githooks/pre-push).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_NAMESPACE GIT_PREFIX

CHECK_ONLY=0
case "${1:-}" in
  "") ;;
  --check) CHECK_ONLY=1 ;;
  *) echo "usage: sync_main.sh [--check]" >&2; exit 2 ;;
esac

say() { printf 'sync_main: %s\n' "$*"; }
refuse() { local code="$1"; shift; say "REFUSED $code - $*"; exit 1; }
error() { local code="$1"; shift; say "ERROR $code - $*"; exit 2; }
short() { git rev-parse --short=8 "$1" 2>/dev/null; }

git rev-parse --git-dir >/dev/null 2>&1 || error NOT_A_REPOSITORY "run it inside a checkout of repository-presenter"
git remote get-url origin >/dev/null 2>&1 || error NO_ORIGIN "this repository has no remote named origin"
git fetch origin --prune --quiet 2>/dev/null || error FETCH_FAILED "git fetch origin --prune failed (network or credentials); main was not touched"
git rev-parse --verify --quiet refs/remotes/origin/main >/dev/null || error NO_ORIGIN_MAIN "origin has no main branch"

REMOTE="refs/remotes/origin/main"
LOCAL="refs/heads/main"
remote_sha="$(short "$REMOTE")"

# The worktree that has main checked out, if any (the path is on the first line of its porcelain block).
main_wt="$(git worktree list --porcelain | awk -v b="branch $LOCAL" '
  /^worktree / { path = substr($0, 10) }
  $0 == b { print path; exit }')"

if ! git rev-parse --verify --quiet "$LOCAL" >/dev/null; then
  if [ "$CHECK_ONLY" -eq 1 ]; then say "CHECK local main does not exist; origin/main=$remote_sha"; exit 0; fi
  git fetch origin main:main --quiet 2>/dev/null || error FF_FAILED "could not create local main from origin/main"
  say "OK created main at $remote_sha"
  exit 0
fi

local_sha="$(short "$LOCAL")"
read -r ahead behind < <(git rev-list --left-right --count "$LOCAL...$REMOTE")
counts="behind $behind, ahead $ahead"
state="main=$local_sha origin/main=$remote_sha ($counts)"

# would <reason>: with --check, report what a real run would refuse and stop; otherwise return.
would() {
  if [ "$CHECK_ONLY" -eq 1 ]; then say "CHECK $state; would $*"; exit 0; fi
}

if [ "$ahead" -gt 0 ]; then
  would "refuse DIVERGED"
  refuse DIVERGED "local main has $ahead commit(s) not on origin/main ($state); move them to a branch and open a PR - this script never rewrites or merges them"
fi
if [ "$behind" -eq 0 ]; then
  say "UP_TO_DATE $state"
  exit 0
fi

# A merge/rebase/cherry-pick/revert/bisect in progress in the main checkout (the primary worktree)
# or in the worktree that has main checked out blocks the fast-forward: during a rebase of main
# itself HEAD is detached, so main then appears checked out nowhere.
primary_wt="$(git worktree list --porcelain | awk '/^worktree / { print substr($0, 10); exit }')"
for wt in "$primary_wt" "$main_wt"; do
  [ -n "$wt" ] || continue
  gd="$(git -C "$wt" rev-parse --absolute-git-dir 2>/dev/null)" || continue
  for op in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG rebase-merge rebase-apply; do
    if [ -e "$gd/$op" ]; then
      would "refuse OP_IN_PROGRESS ($op)"
      refuse OP_IN_PROGRESS "$wt has a merge/rebase/cherry-pick/revert/bisect in progress ($op); finish or abort it yourself, then rerun"
    fi
  done
done

if [ -n "$main_wt" ]; then
  if [ -n "$(git -C "$main_wt" status --porcelain --untracked-files=no)" ]; then
    would "refuse DIRTY"
    refuse DIRTY "$main_wt has uncommitted tracked changes; commit them on a branch (work does not belong in the main checkout) or set them aside yourself, then rerun"
  fi
  would "fast-forward in $main_wt"
  if ! out="$(git -C "$main_wt" merge --ff-only "$REMOTE" 2>&1)"; then
    case "$out" in
      *"untracked working tree files would be overwritten"*)
        files="$(printf '%s\n' "$out" | awk '/^\t/ { gsub(/\t/, ""); printf "%s ", $0 }')"
        refuse UNTRACKED_CLASH "fast-forward would overwrite untracked file(s): ${files}- git aborted, nothing changed; move or commit them yourself, then rerun" ;;
      *) refuse FF_FAILED "git merge --ff-only origin/main failed in $main_wt: $(printf '%s' "$out" | tr '\n' ' ')" ;;
    esac
  fi
else
  would "fast-forward (main is checked out nowhere)"
  if ! out="$(git fetch origin main:main 2>&1)"; then
    refuse FF_FAILED "git fetch origin main:main failed: $(printf '%s' "$out" | tr '\n' ' ')"
  fi
fi

[ "$(git rev-parse "$LOCAL")" = "$(git rev-parse "$REMOTE")" ] || error FF_FAILED "main did not reach origin/main after the fast-forward"
say "OK fast-forwarded main $local_sha -> $remote_sha (was $counts${main_wt:+; checkout $main_wt})"

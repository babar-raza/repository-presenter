#!/usr/bin/env bash
# Creates a git worktree for a NEW branch from a freshly fetched origin/main, wired so tests run the
# worktree's own code. The one sanctioned way to start work (docs/REPOSITORY_LAYOUT.md "Branching
# and worktrees"): agents use it instead of re-deciding each step by hand.
#
# Why: anything branched from the local `main` ref, or importing from the main checkout's editable
# install in the shared .venv, runs stale code (see scripts/sync_main.sh). This script always
# starts from origin/main as it is now, and prints what the shell needs so the venv imports THIS
# worktree's src.
#
# Usage: scripts/new_worktree.sh <name> [<branch>]     (run inside any checkout or worktree)
#   <name>    directory name, placed at <main checkout>/runs/wt/<name> (letters, digits, . _ -)
#   <branch>  new branch to create (default wt/<name>); must not exist locally or on origin
# Windows: run it with Git for Windows bash (not the WSL bash.exe in System32):
#   & "C:\Program Files\Git\bin\bash.exe" scripts/new_worktree.sh <name> <branch>
#
# Steps: `git fetch origin`; refuse an invalid name, an existing branch or an existing path;
# `git worktree add -b <branch> <path> origin/main`; link <main checkout>/.venv into the worktree
# (directory junction via mklink /J on Windows, symlink elsewhere; a missing shared .venv is
# reported, not fatal); print the environment to export.
# It never touches any other worktree, branch, stash or file, and runs no destructive command.
#
# Refusals (exit 1, nothing created): BAD_NAME, BAD_BRANCH, BRANCH_EXISTS, REMOTE_BRANCH_EXISTS,
# PATH_TAKEN, FORBIDDEN_DRIVE. Exit 2: ERROR (no origin, fetch failed, git worktree add failed).
#   NEW_WORKTREE_FORBIDDEN_DRIVES  space-separated Windows drive letters worktrees may not live on
#                                  (default "C": the system drive; never put work under C:\).
#                                  Set to "" only where the checkout must live there (the tests).
#   CI_TOOLS_VENV                  tools venv to export; default C:\dev-tools\rp-ci-tools when it exists.
# The worktree always lands under <main checkout>/runs/wt, so it is never at a drive root.
# Removing a worktree later: delete its .venv junction first with `rmdir .venv` (never a recursive
# delete through it), then `git worktree remove <path>`.
set -u

unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_NAMESPACE GIT_PREFIX

say() { printf 'new_worktree: %s\n' "$*"; }
refuse() { local code="$1"; shift; say "REFUSED $code - $*"; exit 1; }
error() { local code="$1"; shift; say "ERROR $code - $*"; exit 2; }

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then echo "usage: new_worktree.sh <name> [<branch>]" >&2; exit 2; fi
NAME="$1"
BRANCH="${2:-wt/$NAME}"

case "$NAME" in
  ""|.*|*[!A-Za-z0-9._-]*) refuse BAD_NAME "'$NAME' is not a plain directory name (letters, digits, '.', '_', '-'; no slash, no leading dot)" ;;
esac
git check-ref-format --branch "$BRANCH" >/dev/null 2>&1 || refuse BAD_BRANCH "'$BRANCH' is not a valid branch name"
case "$BRANCH" in
  main|master|origin/*) refuse BAD_BRANCH "'$BRANCH' is not a name for a new work branch" ;;
esac

common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || error NOT_A_REPOSITORY "run it inside a checkout of repository-presenter"
[ "$(basename "$common")" = ".git" ] || error NOT_A_REPOSITORY "cannot find the main checkout from $common"
MAIN_ROOT="$(dirname "$common")"
WINDOWS=0
if command -v cygpath >/dev/null 2>&1; then
  WINDOWS=1
  MAIN_ROOT="$(cygpath -m "$MAIN_ROOT")"
  drive="$(printf '%s' "$MAIN_ROOT" | sed -n 's#^\([A-Za-z]\):/.*#\1#p' | tr 'a-z' 'A-Z')"
  for d in ${NEW_WORKTREE_FORBIDDEN_DRIVES-C}; do
    if [ -n "$drive" ] && [ "$drive" = "$(printf '%s' "$d" | tr 'a-z' 'A-Z')" ]; then
      refuse FORBIDDEN_DRIVE "the main checkout is on $drive:, so runs/wt would be too; keep work off that drive"
    fi
  done
fi
WT="$MAIN_ROOT/runs/wt/$NAME"

git remote get-url origin >/dev/null 2>&1 || error NO_ORIGIN "this repository has no remote named origin"
git fetch origin --quiet 2>/dev/null || error FETCH_FAILED "git fetch origin failed (network or credentials); nothing created"
git rev-parse --verify --quiet refs/remotes/origin/main >/dev/null || error NO_ORIGIN_MAIN "origin has no main branch"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  refuse BRANCH_EXISTS "branch '$BRANCH' already exists locally; pick a new branch name (an existing branch is never reset or reused)"
fi
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  refuse REMOTE_BRANCH_EXISTS "branch '$BRANCH' already exists on origin; pick a new branch name"
fi
if [ -e "$WT" ] || [ -L "$WT" ]; then
  refuse PATH_TAKEN "$WT already exists; pick another <name> (nothing is overwritten)"
fi

base_sha="$(git rev-parse refs/remotes/origin/main)"
if ! out="$(git worktree add -b "$BRANCH" "$WT" refs/remotes/origin/main 2>&1)"; then
  error WORKTREE_ADD_FAILED "$(printf '%s' "$out" | tr '\n' ' ')"
fi

# Shared venv: link, never copy. Not fatal when absent (a CI-style checkout has none).
if [ ! -d "$MAIN_ROOT/.venv" ]; then
  venv_note="WARNING no shared venv at $MAIN_ROOT/.venv; provision one (scripts/ci_check.sh header) before running checks"
elif [ "$WINDOWS" -eq 1 ] && command -v cmd >/dev/null 2>&1; then
  if MSYS2_ARG_CONV_EXCL='*' cmd /c mklink /J "$(cygpath -w "$WT/.venv")" "$(cygpath -w "$MAIN_ROOT/.venv")" >/dev/null 2>&1 && [ -d "$WT/.venv" ]; then
    venv_note="junction .venv -> $MAIN_ROOT/.venv"
  else
    venv_note="WARNING could not create the .venv junction; run: cmd /c mklink /J \"$(cygpath -w "$WT/.venv")\" \"$(cygpath -w "$MAIN_ROOT/.venv")\""
  fi
elif ln -s "$MAIN_ROOT/.venv" "$WT/.venv" 2>/dev/null; then
  venv_note="symlink .venv -> $MAIN_ROOT/.venv"
else
  venv_note="WARNING could not link .venv; run: ln -s '$MAIN_ROOT/.venv' '$WT/.venv'"
fi

# Prints a shell-safe single-quoted copy of $1.
sq() { local q="'" bs='\'; printf "'%s'" "${1//$q/$q$bs$q$q}"; }

say "OK $WT (branch $BRANCH from origin/main ${base_sha:0:8})"
say "venv: $venv_note"
say "export these in the shell that works in the worktree; without PYTHONPATH the shared venv imports the main checkout's src:"
tools="${CI_TOOLS_VENV:-}"
if [ "$WINDOWS" -eq 1 ]; then
  if [ -z "$tools" ] && [ -d "/c/dev-tools/rp-ci-tools" ]; then tools='C:\dev-tools\rp-ci-tools'; fi
  gitroot="$(cygpath -m /)"; gitroot="${gitroot%/}"
  echo "  export PYTHONPATH=$(sq "$WT/src")"
  if [ -n "$tools" ]; then echo "  export CI_TOOLS_VENV=$(sq "$tools")"; fi
  echo "  export PATH=$(sq "$(cygpath -u "$gitroot/bin")"):\"\$PATH\"   # Git for Windows bash first (the WSL bash in System32 fails here)"
  printf "  PowerShell: \$env:PYTHONPATH=%s; " "$(sq "$(cygpath -w "$WT/src")")"
  if [ -n "$tools" ]; then printf "\$env:CI_TOOLS_VENV=%s; " "$(sq "$tools")"; fi
  printf "\$env:PATH=%s + \$env:PATH\n" "$(sq "$(cygpath -w "$gitroot/bin");")"
else
  echo "  export PYTHONPATH=$(sq "$WT/src")"
  if [ -n "$tools" ]; then echo "  export CI_TOOLS_VENV=$(sq "$tools")"; fi
fi
say "then work in '$WT' (never in the main checkout), run scripts/ci_check.sh before each commit, push the branch and open a PR"

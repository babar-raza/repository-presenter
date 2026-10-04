#!/usr/bin/env bash
# Sourced by scripts/ci_check.sh (and by tests/test_ci_check_output_dir.py): gives one ci_check.sh
# invocation a private output directory for its SBOM and pip-audit files.
#
# Why: the outputs used to live at a fixed path under the shared tools venv ($CI_TOOLS_VENV/sbom).
# Every session and agent that pushes runs the pre-push hook against the same venv at the same time,
# so concurrent runs overwrote and truncated each other's pip-audit-osv.json, and the sbom step
# failed intermittently on an empty JSON file (2026-10-05, reported independently by two agents).
# A shared fixed path cannot be made safe by retrying; each invocation gets its own directory.
#
# Contract:
#   ci_output_dir_init   creates a fresh directory with mktemp -d under the OS temp dir (never the
#                        repository or the tools venv), exports it as SBOM_DIR, and installs an EXIT
#                        trap (plus INT/TERM, which exit so the EXIT trap fires) that removes it,
#                        on success or failure. CI_CHECK_KEEP_OUTPUT=1 keeps it and prints its path.
#   ci_output_dir_cleanup  the trap body; callable directly.
# The trap is installed in the shell that calls ci_output_dir_init, so call it from the top level,
# not from a command substitution or subshell.

ci_output_dir_init() {
  local base="${TMPDIR:-${TEMP:-${TMP:-/tmp}}}"
  [ -d "$base" ] || base="/tmp"
  SBOM_DIR="$(mktemp -d "${base%/}/ci_check.XXXXXX")" || {
    echo "ci_check.sh: cannot create a private output directory under $base" >&2
    return 1
  }
  # Git Bash's "/tmp/..." means nothing to the native Windows Python that pip-audit runs under (it
  # would resolve to <drive>:	mp); the mixed form (C:/Users/...) is valid to both. No-op elsewhere.
  if command -v cygpath >/dev/null 2>&1; then
    SBOM_DIR="$(cygpath -m "$SBOM_DIR")"
  fi
  export SBOM_DIR
  trap ci_output_dir_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
}

ci_output_dir_cleanup() {
  local dir="${SBOM_DIR:-}"
  [ -n "$dir" ] || return 0
  if [ "${CI_CHECK_KEEP_OUTPUT:-}" = "1" ]; then
    echo "ci_check.sh: CI_CHECK_KEEP_OUTPUT=1 - kept SBOM/audit output in $dir"
    return 0
  fi
  rm -rf -- "$dir"
}

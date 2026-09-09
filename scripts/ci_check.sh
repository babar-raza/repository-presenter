#!/usr/bin/env bash
# The full local CI-equivalent: mirrors .github/workflows/ci.yml's five steps exactly, in the
# same order, so "green locally" and "green on CI" mean the same thing. Run this before every
# push (AGENTS.md's own "Git and Commits" rule) - only `pytest` was ever run by habit during the
# 2026-09-09 healing pass, letting lint/format/mypy drift silently for an entire pass undetected
# (CS-06, plans/healing/ci-staleness-followup.md; docs/CI_AND_STALENESS_ASSESSMENT.md).
#
# Usage: scripts/ci_check.sh
#
# Each check runs independently (never short-circuits on an earlier failure), the same reasoning
# .github/workflows/ci.yml's own Summary step uses (a fail-fast pipeline hides whether the test
# suite passes behind whichever gate breaks first) - so a single run always reports every gate's
# real outcome, never just the first one to fail.
#
# NOT auto-generated from .github/workflows/ci.yml: the two must be kept in sync by hand when
# either changes. A config-generation layer producing both from one source would be new machinery
# beyond this script's own scope (plans/healing/ci-staleness-followup.md's CS-06, Hard rules).
#
# "Install from the lock" needs network access the same way CI's own step does; every other step
# here is offline.
set -u

# python -m repository_presenter.cli runs nothing usable - the console script is the only real
# entry point (this project's own established Windows/venv trap); locate it the same way, next
# to the interpreter, on both platforms.
if [ -x "./.venv/Scripts/python.exe" ]; then
  PYTHON="./.venv/Scripts/python.exe"
  ENTRYPOINT="./.venv/Scripts/repository-presenter.exe"
elif [ -x "./.venv/bin/python" ]; then
  PYTHON="./.venv/bin/python"
  ENTRYPOINT="./.venv/bin/repository-presenter"
else
  PYTHON="python"
  ENTRYPOINT="repository-presenter"
fi

declare -A OUTCOMES

run_step() {
  local name="$1"
  shift
  echo "== $name =="
  if "$@"; then
    OUTCOMES["$name"]="success"
  else
    OUTCOMES["$name"]="failure"
  fi
  echo
}

run_step "lint" "$PYTHON" -m ruff check .
run_step "format" "$PYTHON" -m ruff format --check .
run_step "typecheck" "$PYTHON" -m mypy src
run_step "pytest" "$PYTHON" -m pytest
run_step "entrypoint" bash -c "'$ENTRYPOINT' --version && '$ENTRYPOINT' status"

echo "===== Summary ====="
overall=0
for name in lint format typecheck pytest entrypoint; do
  echo "$name: ${OUTCOMES[$name]}"
  if [ "${OUTCOMES[$name]}" != "success" ]; then
    overall=1
  fi
done

if [ "$overall" -ne 0 ]; then
  echo "One or more checks failed - see the outcomes above for exactly which."
fi
exit "$overall"

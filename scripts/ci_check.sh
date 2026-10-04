#!/usr/bin/env bash
# The full local CI-equivalent: runs the same checks as .github/workflows/ci.yml, in the same
# order, with the same commands and flags, so "green locally" and "green on CI" mean the same
# thing. Run this once per commit, immediately before the commit (AGENTS.md "Git and Commits";
# docs/RESEARCH_AND_GUIDELINES.md section 30.9). Originally written 2026-09-09 after lint, format
# and mypy drifted silently for an entire healing pass (CS-06, plans/healing/ci-staleness-followup.md).
#
# Usage: scripts/ci_check.sh        (from the repository root; Git Bash on Windows, bash on Linux)
#   RP_VENV=<dir>        repo venv (default ./.venv). Its Scripts/ or bin/ goes first on PATH for
#                        this process only, so "repository-presenter" resolves as it does in CI.
#   CI_TOOLS_VENV=<dir>  isolated tools venv (default ./.venv-ci-tools).
#
# Local tools. Preflight checks every one before any check runs and exits 2, naming what is
# missing, if one is absent or off its pin. Nothing here is installed system-wide.
#   Repo venv (RP_VENV): provisioned from the lock, as ci.yml's "Install from the lock" step does:
#       python -m venv .venv
#       .venv/Scripts/python -m pip install -r requirements-lock.txt
#       .venv/Scripts/python -m pip install --no-deps -e .
#     This script never runs that install: it would rewrite a venv shared by other checkouts and
#     repoint its editable install at this one. Preflight only verifies, with a pip dry run, that
#     the venv already satisfies requirements-lock.txt.
#   Tools venv (CI_TOOLS_VENV): holds only the two tools ci.yml installs, pinned as it pins them:
#       python -m venv .venv-ci-tools
#       .venv-ci-tools/Scripts/python -m pip install "uv==0.12.21" "pip-audit==2.10.1"
#     It is separate so pip-audit's own dependencies (requests, rich, ...) never change the repo
#     venv's runtime packages. On CI there is no such venv: ci.yml installs both on the
#     setup-python interpreter, and the script falls back to PATH.
#
# Differences from ci.yml, each deliberate; none removes a check:
#   - Python matrix 3.11/3.12/3.13: only the repo venv's interpreter runs here.
#   - Checkout, pip cache, the uv/pip-audit install steps, "Install from the lock" and the SBOM
#     artifact upload are CI plumbing. Preflight verifies their outcome instead of repeating them.
#   - SBOM and audit outputs go to $CI_TOOLS_VENV/sbom, not evidence/sbom, so a local run never
#     rewrites the committed SBOM snapshot. ci.yml's /tmp paths were also replaced: a Python
#     heredoc's "/tmp/..." resolves to E:\tmp on Windows, so the JSON path is passed as an argument.
#   - ruff, mypy and pytest run as "python -m <tool>", the same entry points as the console
#     scripts. The venv's mypy.exe launcher exits 1 silently on this machine.
#   - PYTHONPATH is set to this checkout's src. Otherwise an editable install of another checkout
#     is what gets tested. scripts/check_import_root.py verifies it held and exits 2 before any
#     check runs if repository_presenter still resolves outside src/ (a worktree sharing a venv).
#   - Shell: ci.yml's "run" steps use bash -e; the SBOM step runs under set -e to match.
#
# NOT auto-generated from .github/workflows/ci.yml: the two must be kept in sync by hand when
# either changes (plans/healing/ci-staleness-followup.md's CS-06, Hard rules).
#
# Each check runs independently (never short-circuits on an earlier failure), the same reasoning
# ci.yml's Summary step uses, so a single run reports every gate's real outcome.
set -u

RP_VENV="${RP_VENV:-.venv}"
CI_TOOLS_VENV="${CI_TOOLS_VENV:-.venv-ci-tools}"
SBOM_DIR="$CI_TOOLS_VENV/sbom"
PINNED_UV="0.12.21"
PINNED_PIP_AUDIT="2.10.1"

# Scripts/ on Windows, bin/ elsewhere; prints nothing when the venv is absent (CI).
venv_bin() {
  if [ -d "$1/Scripts" ]; then
    (cd "$1/Scripts" && pwd)
  elif [ -d "$1/bin" ]; then
    (cd "$1/bin" && pwd)
  fi
}

REPO_BIN="$(venv_bin "$RP_VENV")"
TOOLS_BIN="$(venv_bin "$CI_TOOLS_VENV")"
if [ -n "$REPO_BIN" ]; then
  PATH="$REPO_BIN:$PATH"
fi
export PATH

if [ -d src ]; then
  # pwd -W gives the Windows form, which Python on Windows needs in PYTHONPATH.
  export PYTHONPATH="$(cd src && (pwd -W 2>/dev/null || pwd))"
fi

PY="python"

# Runs the given command with the tools venv's interpreter first on PATH, for uv and pip-audit
# (both invoked as "python -m ..."). With no tools venv (CI) it runs unchanged.
with_tools() {
  if [ -n "$TOOLS_BIN" ]; then
    env PATH="$TOOLS_BIN:$PATH" "$@"
  else
    "$@"
  fi
}

echo "interpreter: $(command -v "$PY") ($("$PY" --version 2>&1))"
echo "src: ${PYTHONPATH:-<unset>}"
echo

MISSING=()

need() {
  local what="$1"
  shift
  if ! "$@" >/dev/null 2>&1; then
    MISSING+=("$what")
  fi
}

need "ruff: pip install -r requirements-lock.txt into the repo venv" "$PY" -m ruff --version
need "mypy: pip install -r requirements-lock.txt into the repo venv" "$PY" -m mypy --version
need "pytest: pip install -r requirements-lock.txt into the repo venv" "$PY" -m pytest --version
need "repository-presenter entry point: pip install --no-deps -e . into the repo venv" command -v repository-presenter

uv_version="$(with_tools "$PY" -m uv --version 2>/dev/null)"
case "$uv_version" in
  *" $PINNED_UV"*) ;;
  *) MISSING+=("uv==$PINNED_UV in the tools venv (found: ${uv_version:-none}); python -m pip install \"uv==$PINNED_UV\"") ;;
esac

pip_audit_version="$(with_tools "$PY" -m pip_audit --version 2>/dev/null)"
case "$pip_audit_version" in
  *" $PINNED_PIP_AUDIT"*) ;;
  *) MISSING+=("pip-audit==$PINNED_PIP_AUDIT in the tools venv (found: ${pip_audit_version:-none}); python -m pip install \"pip-audit==$PINNED_PIP_AUDIT\"") ;;
esac

lock_check="$("$PY" -m pip install --dry-run --disable-pip-version-check -r requirements-lock.txt 2>&1)"
lock_rc=$?
if [ "$lock_rc" -ne 0 ] || printf '%s\n' "$lock_check" | grep -q "Would install"; then
  MISSING+=("repo venv does not satisfy requirements-lock.txt (pip dry run would change it); re-provision it as the header describes")
fi

# Verifies the PYTHONPATH exported above actually took effect for every check below: an editable
# install of another checkout (a shared .venv junction, a stale pip install -e) would otherwise be
# what the checks import. Run with the same environment the checks get, so it tests what they test.
if ! import_root="$("$PY" scripts/check_import_root.py . 2>&1)"; then
  MISSING+=("repository_presenter does not resolve inside this checkout: $import_root (re-point the repo venv's editable install at this checkout, or set PYTHONPATH to its src)")
fi

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "ci_check.sh: required local tool(s) missing or off-pin - NO CHECKS WERE RUN:"
  for item in "${MISSING[@]}"; do
    echo "  - $item"
  done
  echo "Install sources are documented in this script's header comment."
  exit 2
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

# ci.yml's SBOM step, byte-for-byte in its commands; run under set -e as a bash "run" block is.
sbom_step() {
  (
    set -e
    mkdir -p "$SBOM_DIR"
    with_tools "$PY" -m pip_audit -r requirements-lock.txt -f cyclonedx-json -o "$SBOM_DIR/requirements-lock.cdx.json" --timeout 60
    with_tools "$PY" -m pip_audit -r requirements-lock.txt -s osv -f json --timeout 60 | tee "$SBOM_DIR/pip-audit-osv.json"
    with_tools "$PY" -m pip_audit -r requirements-lock.txt -s osv -f markdown --timeout 60 > "$SBOM_DIR/pip-audit-osv.md"
    with_tools "$PY" - "$SBOM_DIR/pip-audit-osv.json" <<'PY'
import json, sys

with open(sys.argv[1]) as f:
    report = json.load(f)

# pip-audit's own JSON has no severity field (OSV's severity data is inconsistent across
# advisories); every finding it reports is therefore treated as high-severity for this
# gate's own purpose - "fails on a new high-severity finding" - rather than silently
# under-reacting to a finding this tool chose not to score. A future, better-scored
# source should replace this blanket rule, not be assumed to exist today.
vulnerable = [dep for dep in report["dependencies"] if dep["vulns"]]
if vulnerable:
    print("VULNERABILITIES FOUND - failing the gate (G7-W02 acceptance: fail on a new "
          "high-severity finding; pip-audit's own JSON carries no severity field, so "
          "every genuine finding is treated as high-severity rather than assumed benign):")
    for dep in vulnerable:
        for vuln in dep["vulns"]:
            print(f"  {dep['name']}=={dep['version']}: {vuln['id']} - {vuln.get('fix_versions')}")
    sys.exit(1)
print(f"No known vulnerabilities across {len(report['dependencies'])} resolved packages (OSV).")
PY
  )
}

# Step names match ci.yml's Summary step exactly.
run_step "lockdrift" with_tools bash scripts/check_lock_drift.sh
run_step "sbom" sbom_step
run_step "lint" "$PY" -m ruff check .
run_step "format" "$PY" -m ruff format --check .
run_step "typecheck" "$PY" -m mypy src
run_step "pytest" "$PY" -m pytest
run_step "entrypoint" bash -c 'repository-presenter --version && repository-presenter status'

echo "===== Summary ====="
overall=0
for name in lockdrift sbom lint format typecheck pytest entrypoint; do
  echo "$name: ${OUTCOMES[$name]}"
  if [ "${OUTCOMES[$name]}" != "success" ]; then
    overall=1
  fi
done

if [ "$overall" -ne 0 ]; then
  echo "One or more checks failed - see the outcomes above for exactly which."
fi
exit "$overall"

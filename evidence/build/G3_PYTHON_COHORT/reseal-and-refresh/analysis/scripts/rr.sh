#!/bin/bash
# usage: rr.sh <log-id> <owner/name> <command...>   (runs the command inside the shallow clone, writes raw-logs/<log-id>.txt)
ANA=/e/Users/prora/OneDrive/Documents/GitHub/repository-presenter/runs/wt/liss1/evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis
BASE=/e/Users/prora/OneDrive/Documents/GitHub/repository-presenter/runs/wt/liss1/runs/iss01
id="$1"; repo="$2"; shift 2
d="$BASE/clones/${repo//\//__}"
tmp=$(mktemp)
headsha=$(git -C "$d" rev-parse HEAD)
( cd "$d" && bash -c "$*" ) > "$tmp" 2>&1
ec=$?
{
 echo "# log: $id"
 echo "# repository: $repo"
 echo "# head: $headsha"
 echo "# utc: $(date -u +%FT%TZ)"
 echo "# cwd: shallow clone of the default branch"
 echo "# command: $*"
 echo "# ---- output (capped at 60000 bytes) ----"
 head -c 60000 "$tmp"
 echo
 echo "# exit: $ec"
} > "$ANA/raw-logs/$id.txt"
rm -f "$tmp"
echo "$id exit=$ec"

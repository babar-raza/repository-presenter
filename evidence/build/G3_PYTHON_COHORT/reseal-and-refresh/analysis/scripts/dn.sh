#!/bin/bash
# usage: dn.sh <image> <owner/name> <command...>  -> runs the command in /w (copy of the clone, so the clone stays untouched) inside a container
export MSYS_NO_PATHCONV=1
BASE=$(cd "$(dirname "$0")" && pwd -W)
image="$1"; repo="$2"; shift 2
d="$BASE/clones/${repo//\//__}"
docker run --rm -v "$d:/src:ro" -v "$BASE/probes:/p:ro" $image bash -c "cp -r /src /w && cd /w && $*"

#!/bin/bash
# usage: clone.sh owner/name [sparse]
r="$1"; d="clones/${r//\//__}"
if [ -d "$d/.git" ]; then exit 0; fi
if [ "$2" = sparse ]; then
  git -c core.autocrlf=false -c core.longpaths=true clone -q --depth 1 --filter=blob:none --sparse "https://github.com/$r.git" "$d" 2>&1 | tail -2
else
  git -c core.autocrlf=false -c core.longpaths=true clone -q --depth 1 "https://github.com/$r.git" "$d" 2>&1 | tail -2
fi
echo "$r $(git -C $d rev-parse HEAD) $(git -C $d rev-parse --abbrev-ref HEAD)"

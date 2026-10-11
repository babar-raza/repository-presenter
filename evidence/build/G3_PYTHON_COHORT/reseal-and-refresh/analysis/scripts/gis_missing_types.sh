#!/bin/bash
# usage: gis_missing_types.sh <build-output.txt>  (run inside the GIS clone)
# Lists the type names the compiler could not find (CS0246) that are declared nowhere in the tracked sources.
grep -o -E "type or namespace name '[A-Za-z0-9_]+' could not" "$1" | sed -E "s/.*name '([A-Za-z0-9_]+)'.*/\1/" | sort -u > /dev/null
names=$(grep -o -E "type or namespace name '[A-Za-z0-9_]+' could not" "$1" | sed -E "s/.*name '([A-Za-z0-9_]+)'.*/\1/" | sort -u)
missing=()
for n in $names; do
  if ! git grep -q -E "\b(class|interface|enum|struct|record|delegate)\b[^;{]*\b$n\b" -- '*.cs'; then missing+=("$n"); fi
done
echo "unresolved names: $(echo "$names" | wc -w); declared nowhere in the repository: ${#missing[@]}"
printf '%s ' "${missing[@]}"; echo

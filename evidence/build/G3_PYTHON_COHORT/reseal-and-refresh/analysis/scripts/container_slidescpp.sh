apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq libpugixml-dev >/dev/null 2>&1
g++ --version | head -1
echo "pugixml: $(dpkg -s libpugixml-dev | grep -m1 Version)"
echo "--- README Quick Start (block at README.md:242) verbatim, g++ -std=c++20 -fsyntax-only -Iinclude:"
g++ -std=c++20 -fsyntax-only -Iinclude /p/slidescpp/snippet_01_line242.cpp > o.txt 2>&1; echo "exit=$?"; grep -E 'error' o.txt | head -2 | cut -c1-220
echo "--- same with #include <Aspose/Slides/Foss/slide.h> added:"
g++ -std=c++20 -fsyntax-only -Iinclude /p/fix/slides01_fixed.cpp > o.txt 2>&1; echo "exit=$?"; grep -m1 error o.txt
echo "--- per-block table (blocks 02 and 10 are fragments that rely on earlier blocks):"
for f in /p/slidescpp/*.cpp; do g++ -std=c++20 -fsyntax-only -Iinclude $f > o.txt 2>&1; rc=$?; echo "$(basename $f): exit=$rc $(grep -m1 -oE "incomplete type '[^']+'" o.txt)"; done

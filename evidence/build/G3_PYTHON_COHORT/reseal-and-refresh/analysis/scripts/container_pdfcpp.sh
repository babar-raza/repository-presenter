g++ --version | head -1
echo "--- README code blocks wrapped in main(), g++ -std=c++20 -fsyntax-only -Iinclude (only blocks that are self-contained; the verdict lines below are per block):"
for f in /p/pdfcpp/snippet_03_line253.cpp /p/pdfcpp/snippet_06_line360.cpp; do
  g++ -std=c++20 -fsyntax-only -Iinclude $f > o.txt 2>&1; rc=$?
  echo "$(basename $f): exit=$rc $(grep -m1 -E 'error' o.txt | sed -E 's#^[^ ]+ ##' | cut -c1-170)"
done
echo "--- TIFF block with #include <aspose/pdf/page_collection.hpp> added:"
g++ -std=c++20 -fsyntax-only -Iinclude /p/fix/pdf06_fixed.cpp > o.txt 2>&1; echo "exit=$?"; grep -m1 error o.txt
echo "--- full per-block table:"
for f in /p/pdfcpp/*.cpp; do g++ -std=c++20 -fsyntax-only -Iinclude $f > o.txt 2>&1; rc=$?; echo "$(basename $f): exit=$rc"; done
echo "--- create-from-scratch block (README.md:253) with #include <aspose.pdf.foss.hpp> added:"
g++ -std=c++20 -fsyntax-only -Iinclude /p/fix/pdf03_fixed.cpp > o.txt 2>&1; echo "exit=$?"; grep -m1 error o.txt | cut -c1-200
echo "--- snippet_03 error lines:"
g++ -std=c++20 -fsyntax-only -Iinclude /p/pdfcpp/snippet_03_line253.cpp 2>&1 | grep -E "error" | head -4 | cut -c1-220

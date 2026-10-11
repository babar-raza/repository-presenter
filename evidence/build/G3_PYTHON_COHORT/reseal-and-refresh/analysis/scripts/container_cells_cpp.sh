g++ --version | head -1
echo "--- README snippet verbatim (includes Workbook.h, Worksheet.h, Cell.h):"
g++ -std=c++17 -fsyntax-only -IAspose.Cells.Foss.Cpp/include /p/cells_cpp/load.cpp > o.txt 2>&1
echo "g++ -std=c++17 -fsyntax-only exit: $?"
grep -E 'error' o.txt | head -4
echo "--- same snippet plus #include \"aspose/cells_foss/WorksheetCollection.h\":"
g++ -std=c++17 -fsyntax-only -IAspose.Cells.Foss.Cpp/include /p/cells_cpp/load_fixed.cpp > o2.txt 2>&1
echo "g++ -std=c++17 -fsyntax-only exit: $?"
grep -E 'error' o2.txt | head -4
echo "--- declarations:"
grep -n 'WorksheetCollection' Aspose.Cells.Foss.Cpp/include/aspose/cells_foss/Workbook.h | head -4
grep -n 'operator\[\]' Aspose.Cells.Foss.Cpp/include/aspose/cells_foss/WorksheetCollection.h

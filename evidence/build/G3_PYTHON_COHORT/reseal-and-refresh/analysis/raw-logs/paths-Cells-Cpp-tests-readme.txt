# log: paths-Cells-Cpp-tests-readme
# repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp
# head: 9f852d0ff1cfdad2d661556d6b87a8eff8c063a2
# utc: 2026-10-10T15:25:06Z
# cwd: shallow clone of the default branch
# command: grep -n 'workspace' Aspose.Cells.Foss.Cpp.Tests/README.md | head -6; echo '--- does workspace/ exist?'; ls -d workspace 2>&1 | head -1; echo '--- top-level dirs:'; git ls-tree --name-only HEAD
# ---- output (capped at 60000 bytes) ----
8:cmake -S .\workspace\Aspose.Cells.Foss.Cpp.Tests -B .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc
9:cmake --build .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc --config Debug -- /p:VcpkgApplocalDeps=false
15:ctest --test-dir .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc -C Debug --output-on-failure
19:`workspace/Aspose.Cells.Foss.Cpp` as a CMake subdirectory. It uses CMake
--- does workspace/ exist?
ls: cannot access 'workspace': No such file or directory
--- top-level dirs:
.gitignore
AGENTS.md
Aspose.Cells.Foss.Cpp.Tests
Aspose.Cells.Foss.Cpp
License
README.md
samples

# exit: 0

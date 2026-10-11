# key: paths-Cells-Cpp-tests-readme
# repository clone: Aspose.Cells-FOSS-for-Cpp
# head: 9f852d0ff1cfdad2d661556d6b87a8eff8c063a2
# utc: 2026-10-11T17:49:22Z

$ grep -n workspace Aspose.Cells.Foss.Cpp.Tests/README.md
[exit 0]
8:cmake -S .\workspace\Aspose.Cells.Foss.Cpp.Tests -B .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc
9:cmake --build .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc --config Debug -- /p:VcpkgApplocalDeps=false
15:ctest --test-dir .\workspace\Aspose.Cells.Foss.Cpp.Tests\build\debug-fc -C Debug --output-on-failure
19:`workspace/Aspose.Cells.Foss.Cpp` as a CMake subdirectory. It uses CMake

$ ls -d workspace 2>&1
[exit 2]
ls: cannot access 'workspace': No such file or directory

$ git ls-tree --name-only HEAD
[exit 0]
.gitignore
AGENTS.md
Aspose.Cells.Foss.Cpp.Tests
Aspose.Cells.Foss.Cpp
License
README.md
samples

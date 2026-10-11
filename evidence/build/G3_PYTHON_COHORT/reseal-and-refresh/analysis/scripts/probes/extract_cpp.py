import pathlib
import re
import sys

readme = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
n = 0
for m in re.finditer(r"```(?:cpp|c\+\+)\n(.*?)```", readme, re.S):
    n += 1
    start_line = readme[: m.start()].count("\n") + 2
    body = m.group(1)
    if "main(" not in body:
        incs = [ln for ln in body.splitlines() if ln.startswith("#include")]
        rest = [ln for ln in body.splitlines() if not ln.startswith("#include")]
        body = "\n".join(incs) + "\nint main() {\n" + "\n".join(rest) + "\nreturn 0;\n}\n"
    (out / f"snippet_{n:02d}_line{start_line}.cpp").write_text(body, encoding="utf-8")
print(n, "snippets")

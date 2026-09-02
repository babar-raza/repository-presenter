"""Only fenced blocks in the ecosystem's language are examples; shells and others are not."""

from __future__ import annotations

from repository_presenter.components.readme.extractors.examples.selection import select_examples

README = b"""# Title

```bash
pip install aspose-3d-foss
```

```python
from aspose.threed import Scene
scene = Scene()
```

```py
print("alias")
```

~~~Python3 title="x"
print("tilde fence")
~~~

```
no language
```

```python
```

    indented block

```javascript
console.log(1)
```
"""


def test_python_fences_become_candidates_in_order() -> None:
    candidates = select_examples("README.md", README, "python")
    assert [(c.ordinal, c.language) for c in candidates] == [
        (1, "python"),
        (2, "py"),
        (3, "python3"),
    ]
    first = candidates[0]
    assert first.code == "from aspose.threed import Scene\nscene = Scene()\n"
    assert (first.start_line, first.end_line) == (7, 10)
    assert first.unit_id == "inherited_unit:003.code_block"
    assert candidates[2].code == 'print("tilde fence")\n'


def test_other_ecosystems_select_their_own_language() -> None:
    assert select_examples("README.md", README, "javascript")[0].code == "console.log(1)\n"
    assert select_examples("README.md", README, "go") == []
    assert select_examples("README.md", b"", "python") == []

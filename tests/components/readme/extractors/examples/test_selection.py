"""Only fenced blocks in the ecosystem's language are examples; shells and others are not."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.extractors.examples.selection import select_examples
from repository_presenter.core.errors import ConfigError

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

```csharp
using Aspose.ThreeD;
var scene = new Scene();
```

```cs
scene.Save("out.obj");
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


def test_another_ecosystem_selects_its_own_fences_and_not_pythons() -> None:
    """The spec owns the fence vocabulary, so a C# block is an example of the .NET ecosystem.

    Measured 2026-09-06: an alias table here knew only Python, so every ```csharp block in the
    .NET cohort's six READMEs was not an example at all and every repository reached planning
    with zero candidates (section 29.2 F6).
    """
    candidates = select_examples("README.md", README, "net")
    assert [(c.ordinal, c.language) for c in candidates] == [(1, "csharp"), (2, "cs")]
    assert candidates[0].code == "using Aspose.ThreeD;\nvar scene = new Scene();\n"
    # Neither ecosystem sees the other's blocks, and no ecosystem sees bash or an unfenced block.
    assert [c.language for c in select_examples("README.md", README, "python")] == [
        "python",
        "py",
        "python3",
    ]
    assert select_examples("README.md", b"", "net") == []


def test_an_ecosystem_with_no_spec_fails_closed() -> None:
    """Selection reads the spec, and a spec is registered or it is a configuration failure.

    `cli.present` resolves `plugin_for` before it ever selects, so this is the same refusal one
    stage earlier: guessing a fence vocabulary would silently produce a candidate-free document.
    """
    with pytest.raises(ConfigError, match="javascript"):
        select_examples("README.md", README, "javascript")

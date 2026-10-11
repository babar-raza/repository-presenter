"""The At a Glance diagram: one builder, one linter, one real-render check.

``components/readme/composition/renderer.py`` (regeneration) and the live-first correction path
(``components/readme_correction``) both need the same diagram, drawn the same way, so it lives
here once: ``build_body`` writes it, ``lint_source`` finds what is wrong with a drawing that
exists, ``rebuild_readme`` repairs a README's diagram without touching a byte elsewhere, and
``render_check`` proves the result in a real browser. See ``build.py`` for why it is drawn this way.
"""

from repository_presenter.components.readme_diagram.build import (
    balanced_columns,
    build_block,
    build_body,
    init_directive,
)
from repository_presenter.components.readme_diagram.lint import lint_source
from repository_presenter.components.readme_diagram.model import (
    Defect,
    Glance,
    LintReport,
    NotAGlanceError,
)
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.components.readme_diagram.rebuild import (
    Rebuilt,
    rebuild_body,
    rebuild_readme,
)

__all__ = [
    "Defect",
    "Glance",
    "LintReport",
    "NotAGlanceError",
    "Rebuilt",
    "balanced_columns",
    "build_block",
    "build_body",
    "init_directive",
    "lint_source",
    "parse",
    "rebuild_body",
    "rebuild_readme",
]

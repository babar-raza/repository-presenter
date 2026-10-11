"""The corrected README may not fail a check the live one did not already fail."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import correct

README = """# Aspose.3D FOSS for Java

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

## License

This project is licensed under the [MIT License](LICENSE).
"""


def test_a_correction_that_fixes_a_blocking_claim_introduces_nothing_and_resolves_it(
    make_context: Any,
) -> None:
    ctx = make_context(README)
    result = correct(ctx)
    delta = validation_delta(ctx, result.corrected, README.encode())
    assert delta["introduced"] == []
    assert {"check": "BC-14", "fewer": 1} in delta["resolved"]
    assert "BC-14" not in delta["corrected_failures"]


def test_a_text_that_adds_a_failure_is_reported_as_introduced(make_context: Any) -> None:
    ctx = make_context(README)
    worse = (
        README.replace("26.5.0", "26.6.0")
        + "\nStill 26.9.9 elsewhere: org.aspose:aspose-3d-foss:26.9.9\n"
    )
    delta = validation_delta(ctx, worse, README.encode())
    assert delta["introduced"] and delta["introduced"][0]["check"] == "BC-14"


def test_failures_the_live_readme_already_had_do_not_block_a_correction(make_context: Any) -> None:
    ctx = make_context(README + "\nSee the commercial-edition page.\n")
    delta = validation_delta(ctx, ctx.readme, ctx.readme.encode())
    assert delta["introduced"] == [] and delta["corrected_failures"] == delta["live_failures"]

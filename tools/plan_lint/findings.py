"""The one result type every rule reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A lint result: ``rule`` is a stable code, ``where`` a card/line locator, ``error`` fails."""

    rule: str
    where: str
    message: str
    severity: str = "error"  # "error" fails the lint; "warn" is reported only

    def render(self) -> str:
        return f"[{self.severity.upper()}] {self.rule} {self.where}: {self.message}"


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "error"]

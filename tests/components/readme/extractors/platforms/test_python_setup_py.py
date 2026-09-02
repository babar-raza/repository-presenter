"""setup.py is read, never executed: only literal keywords of a proven setuptools call count."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.platforms.python_setup_py import (
    parse_setup_py,
)


def _setup_py(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "setup.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_real_shape_setup_py_yields_literal_metadata(tmp_path: Path) -> None:
    path = _setup_py(
        tmp_path,
        """from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as stream:
    long_description = stream.read()

setup(
    name="aspose-3d-foss",
    version="26.1.0",
    packages=find_packages(),
    python_requires=">=3.7",
    long_description=long_description,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: 3.7",
    ],
)
""",
    )
    assert parse_setup_py(path) == {
        "name": "aspose-3d-foss",
        "version": "26.1.0",
        "requires_python": ">=3.7",
        "python_classifier_versions": "3.7,3.10,3.12",
    }


def test_dynamic_and_decoy_metadata_stays_absent_and_nothing_runs(tmp_path: Path) -> None:
    side_effect = tmp_path / "must-not-exist"
    path = _setup_py(
        tmp_path,
        f"""from setuptools import setup

def discover():
    open({str(side_effect)!r}, "w").write("executed")
    return ">=3.13"

decoy(name="wrong-name", version="99.0", python_requires=">=99")
setup(
    name="literal-name",
    version=discover(),
    python_requires=discover(),
    classifiers=[f"Programming Language :: Python :: {{discover()}}"],
)
""",
    )
    assert parse_setup_py(path) == {"name": "literal-name"}
    assert not side_effect.exists()


def test_multiple_setup_calls_fail_closed(tmp_path: Path) -> None:
    path = _setup_py(
        tmp_path,
        "from setuptools import setup\n"
        'setup(name="first", python_requires=">=3.7")\n'
        'setup(name="second", python_requires=">=3.12")\n',
    )
    assert parse_setup_py(path) == {}


@pytest.mark.parametrize(
    "source",
    [
        'def setup(**kwargs):\n    return kwargs\nsetup(name="forged")\n',
        'from attacker import setup\nsetup(name="forged")\n',
        'import attacker as setuptools\nsetuptools.setup(name="forged")\n',
        'from setuptools import setup\nmetadata = {"python_requires": ">=99"}\n'
        'setup(name="real", **metadata)\n',
        'from setuptools import setup\nsetup = lambda **kwargs: kwargs\nsetup(name="forged")\n',
        "import setuptools\nsetuptools.setup = lambda **kwargs: kwargs\n"
        'setuptools.setup(name="forged", python_requires=">=99")\n',
    ],
    ids=[
        "local-function",
        "foreign-function",
        "foreign-module",
        "keyword-spread",
        "rebound",
        "rebound-attribute",
    ],
)
def test_unproven_setup_call_owners_are_rejected(tmp_path: Path, source: str) -> None:
    assert parse_setup_py(_setup_py(tmp_path, source)) == {}


@pytest.mark.parametrize(
    ("import_statement", "call_name"),
    [
        ("from setuptools import setup", "setup"),
        ("from setuptools import setup as package_setup", "package_setup"),
        ("import setuptools", "setuptools.setup"),
        ("import setuptools as packaging", "packaging.setup"),
    ],
    ids=["direct-function", "aliased-function", "direct-module", "aliased-module"],
)
def test_proven_setuptools_import_forms_are_accepted(
    tmp_path: Path, import_statement: str, call_name: str
) -> None:
    path = _setup_py(
        tmp_path, f'{import_statement}\n{call_name}(name="real", python_requires=">=3.11")\n'
    )
    assert parse_setup_py(path) == {"name": "real", "requires_python": ">=3.11"}


def test_unreadable_or_invalid_source_yields_nothing(tmp_path: Path) -> None:
    assert parse_setup_py(tmp_path / "missing.py") == {}
    assert parse_setup_py(_setup_py(tmp_path, "def broken(:\n")) == {}

"""README, license, and community files are found regardless of casing, in a fixed order."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.core.snapshot.inventory import scan


class TestReadme:
    def test_finds_standard_readme_md(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
        assert scan(tmp_path).readme_path == tmp_path / "README.md"

    def test_finds_lowercase_readme(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("# hi", encoding="utf-8")
        assert scan(tmp_path).readme_path == tmp_path / "readme.md"

    def test_missing_readme_is_none(self, tmp_path: Path) -> None:
        assert scan(tmp_path).readme_path is None

    def test_a_readme_directory_does_not_count(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").mkdir()
        assert scan(tmp_path).readme_path is None


class TestLicense:
    def test_finds_root_level_license_uppercase(self, tmp_path: Path) -> None:
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path == tmp_path / "LICENSE"

    def test_finds_root_level_license_titlecase_txt(self, tmp_path: Path) -> None:
        (tmp_path / "License.txt").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path == tmp_path / "License.txt"

    def test_finds_license_in_nested_license_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "License"
        nested.mkdir()
        (nested / "LICENSE.txt").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path == nested / "LICENSE.txt"

    def test_missing_license_is_none(self, tmp_path: Path) -> None:
        assert scan(tmp_path).license_path is None


class TestCommunityFiles:
    def test_finds_contributing_uppercase_extension(self, tmp_path: Path) -> None:
        (tmp_path / "CONTRIBUTING.md").write_text("please contribute", encoding="utf-8")
        assert scan(tmp_path).community_paths["CONTRIBUTING"] == tmp_path / "CONTRIBUTING.md"

    def test_finds_code_of_conduct_lowercase(self, tmp_path: Path) -> None:
        (tmp_path / "code_of_conduct.md").write_text("be nice", encoding="utf-8")
        found = scan(tmp_path).community_paths["CODE_OF_CONDUCT"]
        assert found == tmp_path / "code_of_conduct.md"

    def test_finds_security_and_support(self, tmp_path: Path) -> None:
        (tmp_path / "SECURITY.md").write_text("report issues here", encoding="utf-8")
        (tmp_path / "SUPPORT.md").write_text("get help here", encoding="utf-8")
        paths = scan(tmp_path).community_paths
        assert paths["SECURITY"] == tmp_path / "SECURITY.md"
        assert paths["SUPPORT"] == tmp_path / "SUPPORT.md"

    def test_missing_community_files_produce_an_empty_dict(self, tmp_path: Path) -> None:
        assert scan(tmp_path).community_paths == {}


def test_third_party_notices_are_found_regardless_of_casing(tmp_path: Path) -> None:
    assert scan(tmp_path).notices_path is None
    (tmp_path / "Third-Party-Notices.txt").write_text("zlib\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "Third-Party-Notices.txt"


def test_a_missing_root_yields_an_empty_inventory(tmp_path: Path) -> None:
    inventory = scan(tmp_path / "nope")
    assert (inventory.readme_path, inventory.license_path, inventory.community_paths) == (
        None,
        None,
        {},
    )

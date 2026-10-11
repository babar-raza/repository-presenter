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


def test_a_license_file_named_for_the_bundled_material_it_covers_is_the_notices_file(
    tmp_path: Path,
) -> None:
    """TeX-Python 181015d2 keeps LICENSE-FONTS beside LICENSE; the README documents it as the
    bundled fonts' attribution, so it is the third_party_notices record."""
    (tmp_path / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (tmp_path / "LICENSE-FONTS").write_text("Knuth\n", encoding="utf-8")
    inventory = scan(tmp_path)
    assert inventory.notices_path == tmp_path / "LICENSE-FONTS"
    assert inventory.license_path == tmp_path / "LICENSE"


def test_a_dual_license_file_is_not_a_notices_file(tmp_path: Path) -> None:
    """Negative control: LICENSE-MIT and LICENSE-APACHE are the project's own, never attribution."""
    (tmp_path / "LICENSE-MIT").write_text("MIT License\n", encoding="utf-8")
    (tmp_path / "LICENSE-APACHE").write_text("Apache License\n", encoding="utf-8")
    assert scan(tmp_path).notices_path is None


def test_a_license_inside_a_bundled_material_directory_is_the_notices_file(tmp_path: Path) -> None:
    """PDF-Go cdf43df1: fonts/LICENSE.txt holds the bundled fonts' licence; third_party/ is
    preferred to fonts/ and a notices-named root file to both."""
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "Arimo.ttf").write_text("x", encoding="utf-8")
    (tmp_path / "fonts" / "LICENSE.txt").write_text("OFL\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "fonts" / "LICENSE.txt"
    (tmp_path / "third_party").mkdir()
    (tmp_path / "third_party" / "APACHE-2.0.txt").write_text("a", encoding="utf-8")
    (tmp_path / "third_party" / "PDF417-TABLE-NOTICE.txt").write_text("n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "third_party" / "PDF417-TABLE-NOTICE.txt"
    (tmp_path / "NOTICE").write_text("root\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "NOTICE"


def test_a_directory_without_a_license_file_yields_no_notices(tmp_path: Path) -> None:
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "Arimo.ttf").write_text("x", encoding="utf-8")
    assert scan(tmp_path).notices_path is None


def test_a_missing_root_yields_an_empty_inventory(tmp_path: Path) -> None:
    inventory = scan(tmp_path / "nope")
    assert (inventory.readme_path, inventory.license_path, inventory.community_paths) == (
        None,
        None,
        {},
    )

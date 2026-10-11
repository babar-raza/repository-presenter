"""README, license, and community files are found regardless of casing, in a fixed order."""

from __future__ import annotations

from pathlib import Path

import pytest

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

    @pytest.mark.parametrize("directory", ["LICENSES", "licenses", "Licenses", "licence"])
    def test_finds_a_license_in_any_conventionally_named_directory(
        self, tmp_path: Path, directory: str
    ) -> None:
        """The real path, spelled as the tree spells it, is what the license fact cites."""
        nested = tmp_path / directory
        nested.mkdir()
        (nested / "License.txt").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path == nested / "License.txt"

    def test_a_reuse_layout_with_one_spdx_named_file_is_that_license(self, tmp_path: Path) -> None:
        nested = tmp_path / "LICENSES"
        nested.mkdir()
        (nested / "MIT.txt").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path == nested / "MIT.txt"

    def test_a_reuse_layout_with_several_licenses_names_none_of_them(self, tmp_path: Path) -> None:
        """Negative control: two licenses might be a dual license or a bundled dependency's, so
        no file is guessed to be the project's."""
        nested = tmp_path / "LICENSES"
        nested.mkdir()
        (nested / "MIT.txt").write_text("MIT", encoding="utf-8")
        (nested / "Apache-2.0.txt").write_text("Apache", encoding="utf-8")
        assert scan(tmp_path).license_path is None

    def test_a_root_license_wins_over_a_directory_one(self, tmp_path: Path) -> None:
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        (tmp_path / "LICENSES").mkdir()
        (tmp_path / "LICENSES" / "LICENSE.txt").write_text("Apache", encoding="utf-8")
        assert scan(tmp_path).license_path == tmp_path / "LICENSE"

    @pytest.mark.parametrize("directory", ["docs", "third_party", "legal", "vendor"])
    def test_a_license_in_any_other_directory_is_not_the_projects(
        self, tmp_path: Path, directory: str
    ) -> None:
        nested = tmp_path / directory
        nested.mkdir()
        (nested / "LICENSE.txt").write_text("MIT", encoding="utf-8")
        assert scan(tmp_path).license_path is None

    def test_a_non_license_file_in_a_license_directory_is_not_a_license(
        self, tmp_path: Path
    ) -> None:
        nested = tmp_path / "LICENSES"
        nested.mkdir()
        (nested / "README.md").write_text("about", encoding="utf-8")
        (nested / "MIT.txt").mkdir()
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


def test_a_notices_file_kept_beside_the_license_in_its_directory_is_the_notices_file(
    tmp_path: Path,
) -> None:
    """Cells-.NET and Cells-Python (wave 3) keep `License/ThirdPartyNotices.txt` beside
    `License/LICENSE.txt`, and the README links both. Without a record for the notices file the
    attribution has nowhere to render (BC-05 NOTICES_WITHOUT_RECORD)."""
    nested = tmp_path / "License"
    nested.mkdir()
    (nested / "LICENSE.txt").write_text("MIT License\n", encoding="utf-8")
    (nested / "ThirdPartyNotices.txt").write_text("zlib\n", encoding="utf-8")
    inventory = scan(tmp_path)
    assert inventory.notices_path == nested / "ThirdPartyNotices.txt"
    assert inventory.license_path == nested / "LICENSE.txt"


def test_the_license_itself_is_never_its_own_notices_file(tmp_path: Path) -> None:
    """Negative control: a `License` directory is not a notices directory, so a licence file in
    it (which matches the notice-bearing pattern) is not recorded as third-party attribution."""
    (tmp_path / "License").mkdir()
    (tmp_path / "License" / "LICENSE.txt").write_text("MIT License\n", encoding="utf-8")
    assert scan(tmp_path).notices_path is None


def test_a_root_notices_file_wins_over_one_in_the_license_directory(tmp_path: Path) -> None:
    (tmp_path / "License").mkdir()
    (tmp_path / "License" / "ThirdPartyNotices.txt").write_text("a\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "License" / "ThirdPartyNotices.txt"
    (tmp_path / "NOTICE").write_text("root\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "NOTICE"


def test_a_notices_file_in_a_license_directory_beats_a_covering_license_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "LICENSES").mkdir()
    (tmp_path / "LICENSES" / "NOTICE.txt").write_text("n\n", encoding="utf-8")
    (tmp_path / "LICENSE-FONTS").write_text("Knuth\n", encoding="utf-8")
    assert scan(tmp_path).notices_path == tmp_path / "LICENSES" / "NOTICE.txt"


def test_a_missing_root_yields_an_empty_inventory(tmp_path: Path) -> None:
    inventory = scan(tmp_path / "nope")
    assert (inventory.readme_path, inventory.license_path, inventory.community_paths) == (
        None,
        None,
        {},
    )

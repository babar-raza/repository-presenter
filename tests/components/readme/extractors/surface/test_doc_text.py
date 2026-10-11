"""A description quoted from a symbol's documentation reads whole, or it is not quoted.

Wave-3 acceptance review of the f69f75c7 reseal (2026-10-11), Aspose.3D FOSS for .NET: fourteen
API table rows and many more members read "Base class for  and", "The  contains the
transformation matrix for a bone node", "A  is defined by two  and ." - the upstream comment
itself lost each ``<see cref>`` - and one row ("... a knot vector The w component in co") was cut
mid-word at 200 characters. The strings below are the real ones.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.surface.doc_text import (
    doc_defect,
    normalise_source_docs,
    reference_name,
    resolve_jsdoc_inline,
    resolve_rst_roles,
    resolve_xml_inline,
    usable_doc,
    usable_symbol_docs,
)
from repository_presenter.components.readme.extractors.surface.extractor import surface_symbols
from repository_presenter.core.facts import Evidence, Fact
from repository_presenter.core.grammars import get_parser

# Every one of these is a real description from the Aspose.3D FOSS for .NET candidate.
HOLES = [
    "Base class for  and",
    "The  contains the transformation matrix for a bone node",
    "A MorphTargetChannel is used by  to organize the target geometries.",
    "A  curve consists of a set of points in the edge of the circle shape.",
    "A  is consisting of several curve segments.",
    "is a surface represented by NURBS(Non-uniform rational basis spline), A  is defined by "
    "two  and .",
    "A  is a parametric modeling surface, similar to , it's also defined by two",
    "A helper class to build polygon for",
    "represents a infinity space which is split by a plane, this can be used with",
    "A shorthand function to create and register the The first AnimationClip will be assigned "
    "to the",
    "Constructor of",
    "Initializes a new instance of the  class.",
    "Gets or sets whether it is rational, this value indicates whether this  is rational "
    "spline or non-rational spline.",
    "NURBS curve is a curve represented by NURBS(Non-uniform rational basis spline), A NURBS "
    "curve is defined by its control points, a set of weighted control points and a knot "
    "vector The w component in control point is used as control point's weight whatever the "
    "direction's type is a  or non-rational spline to the contro",
]
WHOLE = [
    "Box.",
    "Information of asset.",
    "The base class of Camera and Light",
    "Initializes a new instance of the Scene class.",
    "Initializes a new instance of the BasicLoadOptions class",
    "The pose is a set of BonePose, each BonePose saves the concrete transformation "
    "information of the bone node.",
    "Gets all BonePose instances.",
    "Calls Dispose() when the scene is released.",
    "Maps an int[] to a Vector3[] of positions.",
    "The format the scene was saved in.",
    "The A channel of an ARGB colour.",
    "Gets or sets the node.",
]


@pytest.mark.parametrize("text", HOLES)
def test_a_summary_with_a_lost_word_is_not_usable(text: str) -> None:
    assert doc_defect(text) is not None
    assert usable_doc(text) == ""


@pytest.mark.parametrize("text", WHOLE)
def test_a_summary_that_reads_whole_is_kept(text: str) -> None:
    assert doc_defect(text) is None
    assert usable_doc(text) == text


def test_a_summary_with_unresolved_markup_is_not_usable() -> None:
    assert doc_defect("Returns {@link } when empty.") == "unresolved markup"
    assert doc_defect("Gets the name. @param name the name") == "unresolved markup"
    assert usable_doc("Reads the value of {@code x} and {@link Foo#bar}.") == (
        "Reads the value of x and Foo.bar."
    )


@pytest.mark.parametrize(
    ("leaked", "description"),
    [
        # Aspose.3D FOSS for Java: a Javadoc with no sentence end in its first line arrives whole.
        (
            "Merge current bounding box with given point @param pt The point to merge /",
            "Merge current bounding box with given point.",
        ),
        (
            "The size of the bounding box @return The size of the bounding box /",
            "The size of the bounding box.",
        ),
        (
            "Initialize a finite bounding box with given minimum and maximum corner "
            "@param minimum The minimum corner @param maximum The maximum corner /",
            "Initialize a finite bounding box with given minimum and maximum corner.",
        ),
        ("Description copied from interface: Struct @return cloned instance /", ""),
        # The engine ends a sentence at "e.g. ": what arrives is the clause and an open bracket.
        ("Custom format string (e.g.", "Custom format string."),
        (
            "Compression large binary data in the FBX file(e.g.",
            "Compression large binary data in the FBX file.",
        ),
        ("@return the value", ""),
    ],
)
def test_a_comment_that_arrives_with_its_block_tags_keeps_only_what_precedes_them(
    leaked: str, description: str
) -> None:
    assert usable_doc(leaked) == description


@pytest.mark.parametrize(
    ("text", "symbol"),
    [
        # A preposition stranded on purpose is not a lost word (wave-3 Aspose.3D FOSS for .NET and
        # Aspose.Cells FOSS for Java/.NET): a relative clause, a passive verb, or the symbol's own
        # name ends the sentence.
        ("Gets the scene that this object belongs to.", "Aspose.ThreeD.Box.Scene"),
        ("Zero-based row index of the cell this comment is anchored to.", "Comment.getRow"),
        (
            "Gets or sets the last modified by.",
            "Aspose.Cells.CoreDocumentProperties.LastModifiedBy",
        ),
        ("Returns the sort by.", "AutoFilterSortCondition.getSortBy"),
        ("Gets the a.", "Aspose.Cells.Color.A"),
    ],
)
def test_a_deliberately_stranded_word_is_not_a_hole(text: str, symbol: str) -> None:
    assert usable_doc(text, symbol) == text


def test_the_symbols_own_name_excuses_only_its_own_last_word() -> None:
    assert usable_doc("Gets or sets the last modified by.", "Aspose.Cells.Other.Name") == ""
    assert usable_doc("Gets or sets the last modified by.") == ""


@pytest.mark.parametrize(
    ("reference", "name"),
    [
        ("Foo", "Foo"),
        ("T:Aspose.ThreeD.Scene", "Scene"),
        ("M:Aspose.ThreeD.Scene.Open(System.IO.Stream,Aspose.ThreeD.FileFormat)", "Open"),
        ("P:Aspose.ThreeD.Scene.RootNode", "RootNode"),
        ("List{T}", "List"),
        ("Dictionary{String,List{T}}", "Dictionary"),
        ("M:Aspose.ThreeD.Scene.#ctor(System.String)", "Scene"),
        ("Foo#bar", "bar"),
    ],
)
def test_a_reference_reads_as_the_name_it_refers_to(reference: str, name: str) -> None:
    assert reference_name(reference) == name


def test_inline_xml_tags_resolve_to_visible_text_and_never_vanish() -> None:
    assert resolve_xml_inline('Gets <see cref="Foo"/> or <see langword="null"/>.') == (
        "Gets Foo or null."
    )
    assert resolve_xml_inline('Use <see cref="Foo">the foo</see> here.') == "Use the foo here."
    assert resolve_xml_inline('See <seealso cref="M:Ns.Bar.Baz(System.Int32)"/> now.') == (
        "See Baz now."
    )
    assert resolve_xml_inline('Opens <paramref name="path"/> as <typeparamref name="T"/>.') == (
        "Opens path as T."
    )
    assert resolve_xml_inline('The <see href="https://example.org/spec">spec</see>.') == (
        "The spec."
    )


def test_jsdoc_and_rst_inline_markup_resolve_to_their_visible_text() -> None:
    assert resolve_jsdoc_inline("Wraps {@link Node | the node} and {@link Mesh}.") == (
        "Wraps the node and Mesh."
    )
    assert resolve_jsdoc_inline("Uses {@code Scene.open} and {@inheritDoc}.") == (
        "Uses Scene.open and ."
    )
    assert resolve_rst_roles("Returns a :class:`~aspose.threed.Scene`, see :meth:`save`.") == (
        "Returns a Scene, see save."
    )
    assert resolve_rst_roles("See :py:func:`the saver <aspose.save>`.") == "See the saver."


CSHARP = """namespace Aspose.Widget
{
    /// <summary>Gets <see cref="Foo"/> or <see langword="null"/>
    /// if <paramref name="x"/> is 0.</summary>
    public class A { }

    /// <summary>
    /// Call <see cref="M:Ns.Bar.Baz(System.Int32)"/> now
    /// </summary>
    /// <remarks>Never quoted.</remarks>
    public class B { }

    /// <summary>Use <see cref="Foo">the foo</see> here</summary>
    /// <param name="x">Leaked into the description when the summary has no period.</param>
    public class C { }

    /// <summary>
    /// Base class for <see cref="Foo"/> and
    /// </summary>
    public class D { }
}
"""


def _symbols(tmp_path: Path, source: str) -> dict[str, str]:
    package = tmp_path / "src" / "Aspose.Widget"
    package.mkdir(parents=True)
    (package / "W.cs").write_text(source, encoding="utf-8")
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "widget")
    return {s.value.rsplit(".", 1)[-1]: s.doc for s in symbols if s.symbol_kind == "class"}


def test_the_csharp_engine_reads_a_comment_whose_inline_tags_are_already_resolved(
    tmp_path: Path,
) -> None:
    docs = _symbols(tmp_path, CSHARP)
    assert docs["A"] == "Gets Foo or null if x is 0."
    assert docs["B"] == "Call Baz now."
    assert docs["C"] == "Use the foo here."
    # The summary closes at </summary>: the param text below it is not part of it.
    assert "Leaked" not in docs["C"]
    # The comment is unfinished upstream ("Base class for X and"): resolving its tag does not
    # complete it, and a sentence that stops on "and" is still not quoted.
    assert docs["D"] == "Base class for Foo and."
    assert usable_doc(docs["D"]) == ""


def test_resolving_a_comment_never_moves_a_line() -> None:
    source = CSHARP.encode("utf-8")
    rewritten = normalise_source_docs(source, "csharp")
    assert rewritten.count(b"\n") == source.count(b"\n")
    assert normalise_source_docs(source, "python") == source
    assert normalise_source_docs(b"\xff\xfe///", "csharp") == b"\xff\xfe///"
    crlf = CSHARP.replace("\n", "\r\n").encode("utf-8")
    assert normalise_source_docs(crlf, "csharp").count(b"\r\n") == crlf.count(b"\r\n")


def test_jsdoc_inline_tags_resolve_in_a_block_comment_and_nowhere_else() -> None:
    source = (
        b"/** Wraps {@link Node | the node}. */\nexport class A {}\n"
        b"const text = '{@link Not} a comment';\n"
    )
    rewritten = normalise_source_docs(source, "typescript")
    assert b"/** Wraps the node. */" in rewritten
    assert b"'{@link Not} a comment'" in rewritten


def test_the_typescript_engine_reads_a_comment_whose_link_tags_are_already_resolved(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "a.ts").write_text(
        "/** Wraps {@link Node | the node} and {@link Mesh}. */\n"
        "export class A {\n"
        "  /**\n   * Opens the scene from {@code path}.\n   * @param path the file\n   */\n"
        "  open(path: string): void {}\n}\n"
        "/** A scene {@link Scene#open} */\nexport class B {}\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text('{"name": "x", "main": "src/a.ts"}', encoding="utf-8")
    symbols = surface_symbols(get_parser("typescript"), "typescript", package, tmp_path, "widget")
    docs = {s.value: s.doc for s in symbols}
    assert docs["a.A"] == "Wraps the node and Mesh."
    assert docs["a.A.open"] == "Opens the scene from path."
    assert docs["a.B"] == "A scene Scene.open"


def test_a_base_class_constructor_is_not_a_member_of_the_derived_type(tmp_path: Path) -> None:
    """Aspose.3D for .NET's ``Scene`` listed ``A3DObject`` and ``SceneObject`` - its ancestors'
    constructors - as members of its own."""
    package = tmp_path / "src" / "Aspose.Widget"
    package.mkdir(parents=True)
    (package / "A3DObject.cs").write_text(
        "namespace Aspose.Widget {\n public class A3DObject {\n"
        "  /// <summary>Initializes a new instance of the A3DObject class with no name.</summary>\n"
        "  public A3DObject() { }\n"
        "  /// <summary>The name.</summary>\n  public string Name { get; set; }\n }\n}\n",
        encoding="utf-8",
    )
    (package / "Scene.cs").write_text(
        "namespace Aspose.Widget {\n public class Scene : A3DObject {\n"
        "  /// <summary>Initializes a new instance of the Scene class.</summary>\n"
        "  public Scene() : base() { }\n"
        "  /// <summary>The material.</summary>\n  public Material Material { get; set; }\n }\n"
        " public class Material { }\n}\n",
        encoding="utf-8",
    )
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "widget")
    members = {s.value for s in symbols if s.symbol_kind == "method"}
    assert "Aspose.Widget.Scene.A3DObject" not in members
    # Its own constructor, an inherited property and a property named like a type all stay.
    assert {
        "Aspose.Widget.Scene.Scene",
        "Aspose.Widget.Scene.Name",
        "Aspose.Widget.Scene.Material",
        "Aspose.Widget.A3DObject.A3DObject",
    } <= members


def _symbol(slug: str, kind: str, docstring: str | None) -> Fact:
    attributes = {"symbol_kind": kind}
    if docstring:
        attributes["docstring"] = docstring
    return Fact(
        f"public_symbol:{slug}",
        "public_symbol",
        slug,
        (Evidence("a.cs", f"line 1; {kind}; public by declaration"),),
        attributes=attributes,
    )


def test_a_symbol_whose_documentation_has_a_hole_keeps_its_facts_and_loses_the_quote() -> None:
    facts = [
        _symbol("deformer", "class", "Base class for  and"),
        _symbol("box", "class", "Box."),
        _symbol("scene.clear", "method", "Clears the <b>scene</b>"),
        _symbol("node", "class", None),
    ]
    cleaned = {f.id: f for f in usable_symbol_docs(facts)}
    assert "docstring" not in (cleaned["public_symbol:deformer"].attributes or {})
    assert cleaned["public_symbol:deformer"].attributes == {"symbol_kind": "class"}
    assert cleaned["public_symbol:box"] == facts[1]
    assert cleaned["public_symbol:node"] == facts[3]
    assert cleaned["public_symbol:scene.clear"].attributes == {
        "symbol_kind": "method",
        "docstring": "Clears the <b>scene</b>",
    }

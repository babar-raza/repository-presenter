- **Not in the public API**: charts (no `IShapeCollection.addChart`); SmartArt, OLE objects, video,
  and audio (not modelled); animations and slide transitions (no `ISlide.getTimeline`, no
  `ISlide.getSlideShowTransition`); group shapes (no `IShapeCollection.addGroupShape` — no shape
  can hold child shapes); hyperlinks (no `setHyperlinkClick` on a shape or a text portion); sections
  (no `IPresentation.getSections`); slide backgrounds (no `ISlide.getBackground`); themes (no
  `IPresentation.getMasterTheme`); slide size (no `IPresentation.getSlideSize` — a new deck is 4:3,
  `cx="9144000" cy="6858000" type="screen4x3"`, with no supported way to change it); and rendering
  or conversion of any kind (no PDF, HTML, SVG, image, or text export); VBA macros, digital
  signatures, and encryption are not modelled either.
- **A known defect: cloning a master.** `getMasters().addClone(...)` returns and the collection
  then reports a size of 2 — but the saved package contains one `<p:sldMasterId>` and one
  `ppt/slideMasters/slideMaster1.xml`. The clone never reaches the file, and nothing reports a
  problem. Do not rely on it.
- **Save formats**: `SaveFormat` declares 25 values. `save()` writes three of them — `PPTX`,
  `PPSX`, and `POTX`, each a genuinely different package with its own main-part content type — and
  raises `UnsupportedOperationException` for the other 22 (`PPT`, `PDF`, `XPS`, `TIFF`, `ODP`,
  `PPTM`, `PPSM`, `POTM`, `HTML`, `HTML5`, `SWF`, `OTP`, `PPS`, `POT`, `FODP`, `GIF`, `MD`, `XML`,
  `SVG`, `JPEG`, `PNG`, `BMP`); it never writes a package under a name that claims to be a format
  it did not produce, and nothing is left on disk when it refuses. The macro-enabled formats are
  refused because their content type declares a VBA project this library does not write. The
  refusal names the alternatives:

  ```
  Export format 'Pdf' is not supported. Writable formats are: Pptx, Ppsx, Potx
  ```

  Give the file the extension its format uses — `save("deck.pptx", SaveFormat.POTX)` writes a
  correct template that PowerPoint refuses to open, because the content type says template and the
  name says presentation.
- `Presentation.save()` requires an explicit output path or stream — there's no overload that infers a destination from `ISaveOptions` alone.
- `Table.mergeCells()` requires an XML-backed table; it cannot merge cells on a table built without a backing OOXML element.
- **What round-tripping does and does not guarantee**: opening a deck and saving it again
  preserves every part, and most of them byte for byte. Measured on a 41-part deck written by
  Apache POI — an independent writer, not this library: 41 parts in, 41 out, 0 dropped, 0 added,
  36 of 41 byte-identical afterwards. `docProps/app.xml`, `ppt/presentation.xml`, and the three
  slide parts are rewritten; `docProps/app.xml` is regenerated from the presentation, the others
  from the package model. Parts this library has no model for (`presProps`, `viewProps`,
  `tableStyles`, themes, unused layouts) are among the 36 that come back unchanged — a specific,
  measured claim about one real deck, deliberately narrower than "full fidelity". Re-saving is
  stable as well: a save with nothing modified in between does not change the file size or the
  slide XML.
- **Text language**: a deck written by this library contains no `lang=` attribute anywhere, and a
  portion that was never formatted gets no `<a:rPr>` at all — PowerPoint applies the authoring
  machine's default language rather than one the file states.

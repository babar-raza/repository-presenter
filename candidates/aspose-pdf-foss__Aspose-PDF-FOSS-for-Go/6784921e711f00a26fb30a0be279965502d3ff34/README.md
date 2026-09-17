# Aspose PDF FOSS for Go

[![Go Reference](https://pkg.go.dev/badge/github.com/aspose-pdf-foss/aspose-pdf-foss-for-go.svg)](https://pkg.go.dev/github.com/aspose-pdf-foss/aspose-pdf-foss-for-go) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go)](https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go/graphs/contributors)

[![Aspose PDF FOSS for Go](https://products.aspose.org/media/pdf/go/banner-readme.png)](https://products.aspose.org/pdf/go/)

Aspose PDF FOSS for Go is a Go library that enables developers to create, read, convert, and manipulate PDF documents programmatically. It solves problems related to document automation, such as splitting, merging, encrypting, signing, and exporting to formats like DOCX, XLSX, and EPUB, while supporting accessibility validation for PDF/A and PDF/UA standards. Developers working in Go 1.24 or later use this library to build server-side or CLI tools that generate reports, process scanned documents, or embed interactive forms and annotations. The library is available at `github.com/aspose-pdf-foss/aspose-pdf-foss-for-go` and has no external runtime dependencies.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart TD
  PRODUCT["Aspose PDF FOSS for Go"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Page operations and metadata"]
      c2["Content authoring with Flow engine"]
      c3["AcroForms and interactive fields"]
      c4["Annotations and interactive elements"]
    end
    subgraph capr[" "]
      direction TB
      c5["Vector graphics and SVG"]
      c6["Table detection and Office conversion"]
      c7["PDF/A and PDF/UA validation"]
      c8["AI document analysis"]
    end
  end
  PRODUCT --> Capabilities
```

## Key Capabilities

- **Page operations and metadata.** `Page` operations and metadata are handled through `Document.Split`, `Document.Append`, `Document.Extract`, `Document.Rotate`, `Document.Reorder`, `Document.SetPageLabels`, `Document.Info`, and `Document.XMP`.
- **Content authoring with Flow engine.** The `Flow` engine supports structured content authoring through `Flow.AddParagraph`, `Flow.AddHeading`, `Flow.AddTable`, `Flow.AddList`, and `Flow.Render` to generate formatted pages from high-level constructs.
- **AcroForms and interactive fields.** `Form.AddTextField`, `Form.AddCheckbox`, `Form.AddComboBox`, and `Form.AddRadioGroup` create interactive AcroForms fields using `FormFieldType` to define their behavior and appearance.
- **Annotations and interactive elements.** `LinkAnnotation`, `HighlightAnnotation`, `StampAnnotation`, and `RedactAnnotation` provide interactive and redaction capabilities, with `NewLinkAnnotation` and `NewHighlightAnnotation` simplifying their creation.
- **Vector graphics and SVG.** `Path`, `LinearGradient`, `RadialGradient`, and `TilingPattern` enable vector drawing, while `Page.AddSVG` and `Page.AddSVGFromStream` embed `SVG` graphics directly into pages.
- **Table detection and Office conversion.** `TableAbsorber` detects tabular content, and `Document.SaveDocx`, `Document.SaveXlsx`, and `Document.SaveEpub` convert PDF documents to Office and EPUB formats.
- **PDF/A and PDF/UA validation.** `Document.ValidatePDFA` and `Document.ValidatePDFUA` check compliance with PDF/A and PDF/UA standards, returning `PDFAValidationReport` and `PDFUAValidationReport` with detailed results.
- **AI document analysis.** The ai subpackage provides `OcrCopilot` for text recognition and searchable PDF generation, `SummaryCopilot` for document summarization, `ChatCopilot` for conversational queries, and `ImageDescriptionCopilot` for image description and alt-text generation.

## Installation

Install the published package from pkg.go.dev (`github.com/aspose-pdf-foss/aspose-pdf-foss-for-go`):

```bash
go get github.com/aspose-pdf-foss/aspose-pdf-foss-for-go
```

Verify the install:

```bash
go list github.com/aspose-pdf-foss/aspose-pdf-foss-for-go
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `go.mod`, no `require` directive a consumer would install is declared.

### Native and System Requirements

- Requires Go `1.24` (`go` in `go.mod`).

## Quick Start

The first example opens an existing PDF, splits it into individual page files, and then merges two separate PDFs into a single document using the Aspose PDF FOSS for Go library.

```go
package main

import (
	"fmt"
	"log"

	pdf "github.com/aspose-pdf-foss/aspose-pdf-foss-for-go"
)

func main() {
	// Open a PDF and split it into per-page documents.
	doc, err := pdf.Open("input.pdf")
	if err != nil {
		log.Fatal(err)
	}
	pages, err := doc.Split()
	if err != nil {
		log.Fatal(err)
	}
	for i, p := range pages {
		p.Save(fmt.Sprintf("page%03d.pdf", i+1))
	}

	// Merge two PDFs into one — Append mutates the receiver in place.
	a, _ := pdf.Open("file1.pdf")
	b, _ := pdf.Open("file2.pdf")
	a.Append(b)
	fmt.Println("merged:", a.PageCount(), "pages")
	a.Save("merged.pdf")
}
```

The second example creates a new PDF document from a standard page format, adds structured content such as headings, paragraphs, and lists, and renders it to pages using the Aspose PDF FOSS for Go library.

```go
doc := pdf.NewDocumentFromFormat(pdf.PageFormatA4)
flow := doc.NewFlow(pdf.FlowOptions{})
flow.AddHeading(1, "Quarterly Report", pdf.TextStyle{})
flow.AddParagraph("Revenue grew in every region this quarter.", pdf.TextStyle{Size: 11})
flow.AddList([]string{"North: +12%", "South: +8%"}, false, pdf.TextStyle{Size: 11})

pages, err := flow.Render()
if err != nil {
	log.Fatal(err)
}
fmt.Println("pages:", pages)
```

## Additional Examples

Create encrypted documents, build tables with custom styling, and render pages to images using Aspose PDF FOSS for Go.

### `Encrypt` a new document with AES-128 and verify access is restricted

```go
doc := pdf.NewDocumentFromFormat(pdf.PageFormatA4)
doc.SetEncryption(pdf.EncryptionOptions{
	UserPassword:  "secret",
	OwnerPassword: "owner-secret",
	Permissions:   &pdf.Permissions{AllowPrint: true, AllowCopy: true},
	Algorithm:     pdf.EncryptionAlgAES128,
})

var buf bytes.Buffer
if _, err := doc.WriteTo(&buf); err != nil {
	log.Fatal(err)
}

// The file is now encrypted; Open returns ErrEncrypted.
if _, err := pdf.OpenStream(&buf); err != nil {
	fmt.Println("encrypted")
}
```

<details>
<summary>View Additional Examples</summary>

### Create a styled table with headers and flow it onto a page

```go
doc := pdf.NewDocument(595, 842)
page, _ := doc.Page(1)

table := pdf.NewTable().
    SetColumnWidths([]float64{120, 200, 80}).
    SetBorder(pdf.BorderInfo{Sides: pdf.BorderSideAll, Width: 1}).
    SetDefaultCellBorder(pdf.BorderInfo{Sides: pdf.BorderSideAll, Width: 0.5}).
    SetDefaultCellMargin(pdf.MarginInfo{Top: 4, Right: 6, Bottom: 4, Left: 6}).
    SetDefaultCellStyle(pdf.TextStyle{Font: pdf.FontHelvetica, Size: 10})

header := table.AddRow()
header.AddCells("Name", "Description", "Qty")
for _, c := range header.Cells() {
    c.SetBackground(&pdf.Color{R: 0.9, G: 0.9, B: 0.9, A: 1})
    c.SetHAlign(pdf.HAlignCenter)
}

row := table.AddRow()
row.AddCells("Widget", "Standard widget", "5")

pagesAdded, _ := page.AddTable(table, pdf.Rectangle{LLX: 50, LLY: 600, URX: 545, URY: 750})
fmt.Printf("table flowed to %d additional pages\n", pagesAdded)
doc.Save("table.pdf")
```

### Render a page with text to an image and confirm dimensions

```go
doc := pdf.NewDocumentFromFormat(pdf.PageFormatA4)
page, _ := doc.Page(1)
_ = page.AddText("Preview me", pdf.TextStyle{Size: 24},
	pdf.Rectangle{LLX: 50, LLY: 700, URX: 545, URY: 780})

img, err := doc.RenderImage(1, pdf.RenderOptions{DPI: 96})
if err != nil {
	log.Fatal(err)
}
fmt.Println("rendered:", img.Bounds().Dx() > 0 && img.Bounds().Dy() > 0)
```

</details>

## API Reference

Aspose PDF FOSS for Go provides the `Document` class as the primary entry point for PDF operations, with supporting types like `Flow`, `Form`, `Annotation`, `Path`, `TableAbsorber`, and AI copilots in the ai subpackage. Each hub API offers focused capabilities for document manipulation, flow content, forms, annotations, vector graphics, table extraction, validation, AI features, encryption, page-level operations, and `JavaScript` actions.

The verified public surface has 229 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AbsorbedCell` | AbsorbedCell is one logical grid position. |
| `AbsorbedRow` | AbsorbedRow is one logical table row. |
| `AbsorbedTable` | AbsorbedTable is one recognized table. |
| `Action` | Action is the common interface implemented by every concrete action type. |
| `ActionType` | ActionType identifies the kind of action attached to an annotation (typically a LinkAnnotation's /A entry). |
| `Annotation` | Annotation is the common interface implemented by every concrete annotation type. |
| `AnnotationCollection` | AnnotationCollection is the live, ordered set of annotations attached to a single page. |
| `AnnotationType` | AnnotationType identifies the kind of annotation. |
| `BmpDevice` | BmpDevice renders a page to BMP. |
| `BookletBinding` | BookletBinding selects the binding edge of a booklet. |
| `BookletOptions` | BookletOptions configures Booklet imposition. |
| `BorderEffect` | BorderEffect controls the /BE/S entry per ISO 32000-1 §12.5.4 Table 167. |
| `BorderInfo` | BorderInfo describes a border drawn around a table or cell. |
| `BorderSide` | BorderSide is a bitmask selecting which sides of a rectangular border are drawn. |
| `BorderStyle` | BorderStyle controls the /BS dict for drawing annotations per ISO 32000-1 §12.5.4 Table 168. |
| `ButtonAppearance` | ButtonAppearance configures a push button's rich appearance: separate captions for the normal / rollover / down states, an optional icon image, and face/border/text colours. |
| `ButtonField` | ButtonField is a push button — action only, no value semantics. |
| `ButtonIconPosition` | ButtonIconPosition controls how a push button lays out its icon and caption — the /MK /TP entry per ISO 32000-1 §12.5.6.19 Table 189. |
| `CaretAnnotation` | CaretAnnotation marks a point of text insertion or deletion, drawn as an upward caret ("^") filled with the annotation colour. |
| `CaretSymbol` | CaretSymbol is the /Sy entry of a Caret annotation per ISO 32000-1 §12.5.6.11 Table 180 — an optional symbol drawn together with the caret to associate it with an editing action. |
| `Cell` | Cell is a single cell within a Row. |
| `CertifyPermission` | CertifyPermission is the DocMDP permission level of a certification signature (ISO 32000-1 §12.8.2.2 Table 254). |
| `CheckboxField` | CheckboxField is a checkbox with on/off state. |
| `ChoiceOption` | ChoiceOption is one option of a ComboBoxField or ListBoxField. |
| `CircleAnnotation` | CircleAnnotation draws an elliptical annotation. |
| `Collection` | Collection is the document's portfolio view over its embedded files. |
| `CollectionField` | CollectionField is one portfolio column. |
| `CollectionFieldType` | CollectionFieldType is a schema column's data type (the collection field's /Subtype). |
| `CollectionItem` | CollectionItem holds one attachment's values for the portfolio's schema fields (the file specification's /CI dictionary). |
| `CollectionSchema` | CollectionSchema is the portfolio's set of columns. |
| `CollectionView` | CollectionView selects how a viewer presents the portfolio's files (the /Collection /View entry). |
| `ComboBoxField` | ComboBoxField is a single-select dropdown choice field. |
| `ComparisonOptions` | ComparisonOptions narrows what is compared. |
| `ComparisonResult` | ComparisonResult holds the differences between two documents and can write a marked-up copy of either side. |
| `ComparisonStatistics` | ComparisonStatistics summarises a comparison. |
| `DateField` | DateField is a text field with a JavaScript date-format action and a format mask (e.g. |
| `Destination` | Destination is the common interface for all explicit destinations. |
| `DestinationFit` | DestinationFit — [page /Fit] |
| `DestinationFitB` | DestinationFitB — [page /FitB] |
| `DestinationFitBH` | DestinationFitBH — [page /FitBH top] |
| `DestinationFitBV` | DestinationFitBV — [page /FitBV left] |
| `DestinationFitH` | DestinationFitH — [page /FitH top] |
| `DestinationFitR` | DestinationFitR — [page /FitR left bottom right top] |
| `DestinationFitV` | DestinationFitV — [page /FitV left] |
| `DestinationType` | DestinationType identifies the destination flavor. |
| `DestinationXYZ` | DestinationXYZ — [page /XYZ left top zoom]. |
| `DiffMarkupOptions` | DiffMarkupOptions styles the marked-up copy. |
| `DiffMarkupSide` | DiffMarkupSide selects which document the markup is drawn on. |
| `DiffOperation` | DiffOperation is one run of adjacent words sharing an operation. |
| `DocRecognitionMode` | DocRecognitionMode selects the reconstruction algorithm — mirrors Aspose.PDF for .NET's DocSaveOptions.RecognitionMode. |
| `DocSaveOptions` | DocSaveOptions configures SaveDocx / WriteDocx. |
| `Document` | Document is a PDF document. |
| `DocumentInfo` | DocumentInfo contains document information from the PDF Info dictionary. |
| `EditOperationsOrder` | EditOperationsOrder decides how the two halves of a replacement are ordered. |
| `EmbeddedFile` | EmbeddedFile is one attachment: a /Filespec dictionary with an embedded stream. |
| `EmbeddedFiles` | EmbeddedFiles is the document's collection of attached (embedded) files — the /Catalog/Names/EmbeddedFiles name tree (ISO 32000-1 §7.11.4). |
| `EncryptionAlgorithm` | EncryptionAlgorithm selects the cipher and security-handler revision used by (*Document).SetEncryption. |
| `EncryptionOptions` | EncryptionOptions bundles every knob that controls how a document is encrypted when saved. |
| `EpubSaveOptions` | EpubSaveOptions configures SaveEpub / WriteEpub. |
| `Field` | Field is the common interface implemented by every concrete form field type (TextBoxField, CheckboxField, RadioButtonField, etc.). |
| `FieldStyle` | FieldStyle is the visual styling applied to a form field's widget(s). |
| `FigureAlt` | FigureAlt is a /Figure structure element that has no alternate text, paired with the image it brackets (when resolvable). |
| `FileAttachmentAnnotation` | FileAttachmentAnnotation embeds a file in the document and shows an icon at the annotation's /Rect. |
| `FileAttachmentIcon` | FileAttachmentIcon names per ISO 32000-1 §12.5.6.15 Table 178. |
| `FileSelectBoxField` | FileSelectBoxField is a text field whose value is a file path (FileSelect flag), used to attach a local file on submit. |
| `FloatSide` | FloatSide selects which edge a floated box hugs while text wraps around it. |
| `FloatingBox` | FloatingBox is a positioned content container (Tier 2 of the flow model): a box with an optional border, background and padding that lays its own content (paragraphs, headings, images, lists) inside its width. |
| `Flow` | Flow is a document generator that lays content out top-to-bottom and paginates automatically — the "flow" counterpart to the Rectangle-based drawing API. |
| `FlowOptions` | FlowOptions configures a Flow. |
| `Font` | Font is implemented by standard 14 fonts and embedded TTF fonts. |
| `Form` | Form is the document's AcroForm view. |
| `FormFieldType` | FormFieldType identifies the kind of form field. |
| `FreeTextAnnotation` | FreeTextAnnotation displays text directly on the page, rendered into /AP/N using an embedded font. |
| `FreeTextIntent` | FreeTextIntent per ISO 32000-1 §12.5.6.6 /IT entry. |
| `GenericAnnotation` | GenericAnnotation is the catch-all surface for /Subtype values this release does not yet model (Stamp, FreeText, Ink, etc.). |
| `GifDevice` | GifDevice renders a page to GIF. |
| `GoToAction` | GoToAction navigates to a page within the same document. |
| `GoToURIAction` | GoToURIAction opens a URI in the user's default handler (typically a web browser). |
| `Gradient` | Gradient is a fill that varies colour across a shape: either a LinearGradient or a RadialGradient. |
| `GradientStop` | GradientStop is one colour stop in a gradient, positioned at Offset (0 at the gradient's start, 1 at its end). |
| `HAlign` | HAlign specifies horizontal text alignment within a rectangle. |
| `HTMLMode` | HTMLMode selects how SaveHTML / WriteHTML represents page text. |
| `HTMLSaveOptions` | HTMLSaveOptions configures SaveHTML / WriteHTML. |
| `HighlightAnnotation` | HighlightAnnotation marks a region with a semi-transparent highlight colour, washed over the text the quads cover. |
| `Image` | Image holds an extracted image with its encoded data and metadata. |
| `ImageColorSpace` | ImageColorSpace describes the original color space of the image in the PDF. |
| `ImageFormat` | ImageFormat describes the output format of an extracted image. |
| `ImageInfo` | ImageInfo holds metadata about an image found on a page without decoding pixel data. |
| `ImageStamp` | ImageStamp overlays a raster image (PNG or JPEG), stretched to fill Rect. |
| `ImageToDocumentOptions` | ImageToDocumentOptions controls page sizing for ImageToDocument. |
| `InkAnnotation` | InkAnnotation draws a series of free-form strokes — typically used to represent handwritten ink. |
| `JSONExportOptions` | JSONExportOptions controls (*Form).ExportJSON / WriteJSON. |
| `JavaScriptAction` | JavaScriptAction holds a JavaScript snippet attached to an annotation. |
| `JavaScriptCollection` | JavaScriptCollection is the document-level JavaScript store, backed by the /Catalog/Names/JavaScript name tree (ISO 32000-1 §7.7.4 / §8.5.1). |
| `JpegDevice` | JpegDevice renders a page to JPEG. |
| `Layer` | Layer is one Optional Content Group (OCG) in the document. |
| `LineAnnotation` | LineAnnotation draws a straight line between two points, with optional line endings on each end (arrows, circles, etc. |
| `LineCap` | LineCap is the /J line cap style per ISO 32000-1 §8.4.3.3 Table 54. |
| `LineEndingStyle` | LineEndingStyle is one of the 10 line-ending shapes per ISO 32000-1 §12.5.6.7 Table 176, used in /Line annotations' /LE entry. |
| `LineJoin` | LineJoin is the /j line join style per ISO 32000-1 §8.4.3.4 Table 55. |
| `LineStyle` | LineStyle describes how a stroked path is drawn. |
| `LinearGradient` | LinearGradient interpolates colour along the line from (X1, Y1) to (X2, Y2). |
| `LinkAnnotation` | LinkAnnotation is a clickable region. |
| `LinkHighlightMode` | LinkHighlightMode controls the visual feedback when the link is activated by the user (the /H entry per ISO 32000-1 §12.5.6.5). |
| `ListBoxField` | ListBoxField is a single- or multi-select list choice field. |
| `MarginInfo` | MarginInfo describes margins or padding in points: Top / Right / Bottom / Left. |
| `MarkdownOptions` | MarkdownOptions configures Markdown rendering. |
| `MarkdownSaveOptions` | MarkdownSaveOptions configures SaveMarkdown / WriteMarkdown. |
| `MarkupParagraph` | MarkupParagraph is a run of consecutive lines forming one paragraph. |
| `MarkupSection` | MarkupSection is a column of paragraphs (left-to-right across the page). |
| `NUpOptions` | NUpOptions configures NUp imposition. |
| `NUpOrder` | NUpOrder controls the order in which source pages fill the grid cells of an N-up sheet. |
| `NamedAction` | NamedAction triggers a built-in viewer command (FirstPage, Print, ...). |
| `NamedActionType` | NamedActionType identifies one of the standard viewer commands supported by /Named actions per ISO 32000-1 §12.6.4.11. |
| `NamedDestination` | NamedDestination wraps a name reference into the document's NamedDestinations collection. |
| `NamedDestinations` | NamedDestinations is a name-to-destination map per ISO 32000-1 §12.3.2.3. |
| `NumberField` | NumberField is a text field with a JavaScript number-format action, so viewers display and validate the value as a formatted number. |
| `NumberFormatOptions` | NumberFormatOptions configures a NumberField's display formatting (maps to Acrobat's AFNumber_Format). |
| `Operation` | Operation is the kind of a difference. |
| `OptimizationOptions` | OptimizationOptions selects which reductions Document.Optimize applies. |
| `OptimizationResult` | OptimizationResult reports what Document.Optimize changed. |
| `OptimizeImageOptions` | OptimizeImageOptions controls image optimization behavior. |
| `OutlineItemCollection` | OutlineItemCollection represents an outline entry and the collection of its children. |
| `PDFAFormat` | PDFAFormat identifies a PDF/A conformance level. |
| `PDFAIssue` | PDFAIssue describes a single PDF/A conformance violation. |
| `PDFAValidationReport` | PDFAValidationReport is returned by (*Document).ValidatePDFA. |
| `PDFUAIssue` | PDFUAIssue describes a single PDF/UA (accessibility) conformance violation. |
| `PDFUAValidationReport` | PDFUAValidationReport is returned by (*Document).ValidatePDFUA. |
| `Page` | Page is a live view of a single page within a Document. |
| `PageFormat` | PageFormat describes a page size in points (1/72 inch). |
| `PageLabelRange` | PageLabelRange describes a contiguous run of pages that share a numbering style. |
| `PageLabelStyle` | PageLabelStyle is the numbering style applied within a PageLabelRange. |
| `PageMarkup` | PageMarkup is the structured text of one page. |
| `PageNumberStamp` | PageNumberStamp stamps the page number (and optionally the total), formatted by Format. |
| `PageRange` | PageRange specifies an inclusive range of pages (1-based). |
| `PageSize` | PageSize holds the width and height of a PDF page in points (1/72 inch). |
| `PasswordBoxField` | PasswordBoxField is a text field whose input is masked (Password flag). |
| `Path` | Path is a sequence of MoveTo/LineTo/CurveTo/Close operations defining an arbitrary 2D path in PDF user space (origin at page bottom-left, Y up). |
| `PdfPageStamp` | PdfPageStamp overlays (or underlays) a page from another PDF document as a stamp — the source page is imported once as a Form XObject and drawn into the stamp's Rect, scaled to fit while preserving aspect ratio, positioned by HAlign/VAlign, and honoring Opacity, RotateAngle and Background. |
| `Permissions` | Permissions controls what a viewer allows on an encrypted PDF. |
| `PngDevice` | PngDevice renders a page to PNG at a fixed resolution. |
| `Point` | Point is a single point in PDF user-space coordinates. |
| `PolygonAnnotation` | PolygonAnnotation draws a closed polygon through a list of vertices, with a stroked border and optional interior fill. |
| `PolylineAnnotation` | PolylineAnnotation draws an open polyline through a list of vertices, with a stroked border, optional line endings at the first and last vertex, and optional interior fill for closed endings. |
| `QuadPoint` | QuadPoint is one quadrilateral within a markup annotation's /QuadPoints array. |
| `RadialGradient` | RadialGradient interpolates colour from the focal point (FX, FY) out to the circle centred at (CX, CY) with radius R. |
| `RadioButtonField` | RadioButtonField is a group of mutually exclusive options. |
| `RadioButtonOptionField` | RadioButtonOptionField is one of the option widgets inside a RadioButtonField. |
| `RadioItem` | RadioItem describes one widget inside a radio group. |
| `Recipient` | Recipient is one certificate that may open a public-key-encrypted document, optionally with its own permission set. |
| `Rectangle` | Rectangle represents a PDF rectangle [llx, lly, urx, ury] in points (1/72 inch). |
| `RedactAnnotation` | RedactAnnotation marks regions for redaction. |
| `RenderOptions` | RenderOptions controls page rasterization. |
| `ReplaceOptions` | ReplaceOptions tunes how ReplaceText matches the search text. |
| `ResetFormAction` | ResetFormAction resets named form fields to their /DV defaults. |
| `Resolution` | Resolution is a rendering resolution in DPI. |
| `RichTextBoxField` | RichTextBoxField is a text field that carries a rich-text value (RichText flag + /RV) in addition to its plain /V. |
| `RotationAngle` | RotationAngle represents a valid PDF page rotation in clockwise degrees. |
| `Row` | Row is a single row within a Table. |
| `SVG` | SVG is the pre-parsed SVG document. |
| `SVGFontResolver` | SVGFontResolver maps an SVG font-family + style to a PDF.Font. |
| `SVGSaveOptions` | SVGSaveOptions configures SaveSVG / WriteSVG. |
| `SearchOptions` | SearchOptions tunes how SearchText interprets the query. |
| `ShapeStyle` | ShapeStyle combines a stroke (LineStyle) with an optional fill color. |
| `SignOptions` | SignOptions configures a digital signature. |
| `SignatureAppearance` | SignatureAppearance controls the visible signature block's content and styling. |
| `SignatureVerification` | SignatureVerification is the result of verifying one digital signature. |
| `SquareAnnotation` | SquareAnnotation draws a rectangular annotation with stroked border and optional interior fill. |
| `SquigglyAnnotation` | SquigglyAnnotation draws a wavy underline under text (typically used for spell-check style hints). |
| `Stamp` | Stamp is content overlaid on (or behind) a page: a TextStamp, an ImageStamp, or a PageNumberStamp. |
| `StampAnnotation` | StampAnnotation is a rubber-stamp annotation. |
| `StampName` | StampName names per ISO 32000-1 §12.5.6.13 Table 184. |
| `StrikeOutAnnotation` | StrikeOutAnnotation draws a horizontal line through text. |
| `StructElement` | StructElement is a node in the logical structure tree. |
| `StructType` | StructType is a PDF standard structure type (ISO 32000-1 §14.8.4), used as the /S value of a structure element. |
| `SubmitFormAction` | SubmitFormAction submits form field values to a URL. |
| `SubmitFormFlags` | SubmitFormFlags is the /Flags bitfield for a /SubmitForm action per ISO 32000-1 Table 237. |
| `TOCEntry` | TOCEntry is one line of a table of contents: a title, an indent level (0 = top level), and the page it points at. |
| `TOCOptions` | TOCOptions controls how a table of contents is rendered. |
| `Table` | Table is a transient builder for a tabular layout drawn onto a Page. |
| `TableAbsorber` | TableAbsorber detects tables on a page and exposes their logical structure (epic pdf-go-w4ht). |
| `TaggedContent` | TaggedContent is the facade for authoring a Tagged PDF (ISO 32000-1 §14.8): it owns the document's logical structure tree and sets the catalog marks PDF/UA requires. |
| `TextAnnotation` | TextAnnotation is a sticky-note annotation. |
| `TextBoxField` | TextBoxField is a single- or multi-line text input. |
| `TextExtractOptions` | TextExtractOptions configures ExtractText. |
| `TextExtractionMode` | TextExtractionMode selects how ExtractText orders the extracted text. |
| `TextFragment` | TextFragment represents a contiguous run of text with uniform font. |
| `TextIcon` | TextIcon names per ISO 32000-1 §12.5.6.4 Table 172, used in /Subtype /Text annotations' /Name entry. |
| `TextMatch` | TextMatch is a single occurrence located by SearchText. |
| `TextStamp` | TextStamp overlays a line (or wrapped block) of text. |
| `TextStyle` | TextStyle defines reusable text formatting properties. |
| `TiffDevice` | TiffDevice renders pages to TIFF. |
| `TilingPattern` | TilingPattern is a repeating fill (PatternType 1, ISO 32000-1 §8.7.3.1): a small cell of content tiled across whatever shape it fills. |
| `Type3Font` | Type3Font is a user-defined glyph-stream font. |
| `UnderlineAnnotation` | UnderlineAnnotation draws a horizontal line under text. |
| `VAlign` | VAlign specifies vertical text alignment within a rectangle. |
| `ValidationIssue` | ValidationIssue describes a single problem found in a PDF file. |
| `ValidationReport` | ValidationReport is returned by Validate and summarises the structural integrity of a PDF. |
| `WidgetAnnotation` | WidgetAnnotation is the read-only view of a form widget annotation surfaced through AnnotationCollection. |
| `XForm` | XForm is a reusable Form XObject (ISO 32000-1 §8.10) — a self-contained content stream (with its own resources) that can be placed on any number of pages and positions with a single Do invocation. |
| `XMPMetadata` | XMPMetadata is the document's XMP packet modelled as common schema fields plus a list of arbitrary Custom properties. |
| `XMPProperty` | XMPProperty is a single simple (string-valued) XMP property in an arbitrary namespace. |
| `XlsxRecognitionMode` | XlsxRecognitionMode selects what lands in the workbook. |
| `XlsxSaveOptions` | XlsxSaveOptions configures SaveXlsx / WriteXlsx. |
| `AIClient` | AIClient is the contract every copilot consumes: one call, one chat completion. |
| `APIError` | APIError is returned when the AI endpoint answers with a non-2xx status. |
| `ChatCopilot` | ChatCopilot answers questions about a document, keeping conversation history. |
| `ChatOptions` | ChatOptions configures a ChatCopilot. |
| `CompletionRequest` | CompletionRequest describes one chat-completion call. |
| `CompletionResponse` | CompletionResponse is the model's reply. |
| `ImageDescriptionCopilot` | ImageDescriptionCopilot describes images with a vision model. |
| `ImageDescriptionOptions` | ImageDescriptionOptions configures an ImageDescriptionCopilot. |
| `LLMOCREngine` | LLMOCREngine recognizes text by sending the page image to a vision-capable chat model. |
| `LLMOCROptions` | LLMOCROptions configures the vision-model OCR engine. |
| `Message` | Message is a single chat message. |
| `MessageImage` | MessageImage is an inline image attached to a message, sent as a base64 data: URL. |
| `OCRBox` | OCRBox is a rectangle in image pixel space: origin at the top-left corner, Y increasing downward (the usual raster convention — distinct from PDF user space on purpose). |
| `OCREngine` | OCREngine recognizes text on one page image. |
| `OCRLine` | OCRLine is one physical text line. |
| `OCRResult` | OCRResult is the recognized content of one page image. |
| `OCRWord` | OCRWord is word-level detail within a line, for engines that provide it. |
| `OcrCopilot` | OcrCopilot recognizes text on scanned pages. |
| `OcrOptions` | OcrOptions configures an OcrCopilot. |
| `OpenAIClient` | OpenAIClient talks to an OpenAI-compatible chat-completions endpoint using only the standard library. |
| `OpenAIClientOptions` | OpenAIClientOptions configures NewOpenAIClient. |
| `SummaryCopilot` | SummaryCopilot produces document summaries with an AI model. |
| `SummaryOptions` | SummaryOptions configures a SummaryCopilot. |
| `TextRecognitionResult` | TextRecognitionResult is the recognized text of one processed page. |
| `Usage` | Usage reports token counts when the provider returns them. |

#### Detailed Member Reference

### Document

The `Document` class supports opening PDFs via `Open`, `OpenStream`, `OpenWithPassword`, and `OpenStreamWithPassword`, and saving via `WriteTo` or format-specific methods like `SaveHTML`, `SaveSVG`, `SaveMarkdown`, and `SaveDocx`; it provides page manipulation through Split, Extract, Rotate, Reorder, `SetPageLabels`, and Info, and includes XMP metadata access and validation for PDF/A and PDF/UA standards.

- `AddBlankPage`: AddBlankPage appends a blank page to the end of the document.
- `AddBlankPageFromFormat`: AddBlankPageFromFormat appends a blank page using a predefined page format.
- `AddLayer`: AddLayer creates a new layer (OCG) named name and registers it in the document's optional-content properties.
- `AddSVGObjectWatermark`: AddSVGObjectWatermark uses a pre-parsed *SVG for the watermark content.
- `AddSVGWatermark`: AddSVGWatermark applies an SVG watermark to all pages (when pageNums is empty) or to the specified 1-based page numbers.
- `AddSVGWatermarkFromStream`: AddSVGWatermarkFromStream is the io.Reader variant of AddSVGWatermark.
- `AddStamp`: AddStamp draws a stamp onto the given 1-based pages (all pages when none are given) — convenient for watermarks, headers, footers, and page numbers.
- `AddTextWatermark`: AddTextWatermark adds a text watermark to selected pages of the document.
- `Append`: Append adds all pages from others to this document, merging their objects.
- `ApplyRedactions`: ApplyRedactions destructively removes content (text glyphs, image XObjects, paths) inside every /Redact annotation's /QuadPoints (or /Rect if /QuadPoints is empty).
- `Booklet`: Booklet returns a new Document that imposes this document's pages two-up, reordered for saddle-stitch binding: print double-sided, fold the stack in half, and the pages read in order.
- `ChangePassword`: ChangePassword re-encrypts the document with new passwords on the next Save, keeping the current encryption algorithm and permissions.
- `ClearInfo`: ClearInfo removes the Info dictionary entirely.
- `ClearPageLabels`: ClearPageLabels removes the document's /PageLabels entry.
- `ClearXMP`: ClearXMP removes the /Catalog/Metadata entry.
- `Collection`: Collection returns the document's portfolio facade.
- `ConvertToGrayscale`: ConvertToGrayscale converts the document to grayscale in place: every device colour set in a content stream (text, vector graphics), every raster image, shading and annotation colour is mapped to its luminance grey.
- `ConvertToPDFA`: ConvertToPDFA adjusts the document toward a PDF/A "b"-level conformance profile and returns a validation report describing any violations that remain.
- `CreateForm`: CreateForm creates an empty Form XObject of the given size (points).
- `CreateTilingPattern`: CreateTilingPattern creates an empty tiling pattern whose cell is width×height points.
- `CreateType3Font`: CreateType3Font returns an empty Type3 font bound to the document.
- `DeletePage`: DeletePage removes the page at the given 1-based number.
- `DeletePages`: DeletePages removes the pages at the given 1-based page numbers.
- `EmbeddedFiles`: EmbeddedFiles returns the document-level embedded-file collection.
- `Extract`: Extract returns a new Document containing only the pages in the specified ranges.
- `ExtractImages`: ExtractImages returns images from all pages (one slice per page).
- `ExtractText`: ExtractText returns the text content of each page (one entry per page, 0-indexed).
- `ExtractTextWithLayout`: ExtractTextWithLayout returns structured text lines for each page.
- `FiguresNeedingAltText`: FiguresNeedingAltText walks the document's logical structure tree and returns every /Figure element that lacks alternate text (/Alt or /ActualText), each paired with the image it brackets when that image can be located.
- `Flatten`: Flatten bakes the document's interactive form fields into static page content and removes the AcroForm, so the result renders identically but is no longer fillable.
- `Form`: Form returns the document's AcroForm.
- `GenerateTOC`: GenerateTOC builds a table of contents from the document's outline (bookmark) tree and inserts it as new page(s) at the front of the document.
- `ImageInfos`: ImageInfos returns image metadata for all pages (one slice per page) without decoding pixel data.
- `ImportForm`: ImportForm copies a Form XObject (and its whole resource graph: fonts, images, nested forms, …) from another document into this one, returning a new XForm ready to place with Page.AddForm.
- `Info`: Info returns the Info-dictionary metadata from this document.
- `InsertBlankPage`: InsertBlankPage inserts a blank page at the given 1-based position.
- `InsertBlankPageFromFormat`: InsertBlankPageFromFormat inserts a blank page at the given position using a predefined page format.
- `JavaScript`: JavaScript returns the document-level JavaScript collection.
- `Layers`: Layers returns the document's layers (OCGs), in /OCProperties/OCGs order.
- `LoadFont`: LoadFont reads a TTF file, parses it, embeds it into the document, and returns a Font that can be used in TextStyle.Font.
- `LoadFontByName`: LoadFontByName resolves a font by family name (with an optional bold / italic style) through the FontRepository — the folders and files registered with AddFontFolder / AddFontFile first, then the operating system's font directories — embeds the matched face into the document, and returns a Font usable in TextStyle.Font.
- `LoadFontFromStream`: LoadFontFromStream is like LoadFont but reads from an io.Reader.
- `LoadSVG`: LoadSVG reads and parses an SVG file once, returning a *SVG that can be passed to Page.AddSVGObject or Document.AddSVGObjectWatermark multiple times without re-parsing.
- `LoadSVGFromStream`: LoadSVGFromStream is the io.Reader variant of LoadSVG.
- `NUp`: NUp returns a new Document that imposes this document's pages onto larger sheets in a Rows×Cols grid (e.g.
- `NamedDestinations`: NamedDestinations returns the document's named-destination collection.
- `NewFlow`: NewFlow creates a flow that renders into the document d.
- `OpenAction`: OpenAction returns the action the viewer runs when the document is opened (/Catalog/OpenAction per ISO 32000-1 §12.3.2 / §12.6.1), or nil when none is set.
- `Optimize`: Optimize reduces the document's size in place per opts and returns a report of what changed.
- `OptimizeImages`: OptimizeImages optimizes all images in the document to reduce file size.
- `Outlines`: Outlines returns the document's root outline collection.
- `Page`: Page returns a live view of the page at the given 1-based number.
- `PageCount`: PageCount returns the number of pages in the document.
- `Pages`: Pages returns a live view of all pages in the document.
- `Paragraphs`: Paragraphs returns the structured text of every page.
- `Permissions`: Permissions returns the viewer-permission settings currently configured on this document, plus a boolean indicating whether the document is configured for encryption at all.
- `RemoveEncryption`: RemoveEncryption clears any previously configured encryption (passwords and permissions) so the next Save produces a plaintext PDF.
- `RemoveOpenAction`: RemoveOpenAction clears any /Catalog/OpenAction.
- `RemoveUnusedObjects`: RemoveUnusedObjects removes objects from the document that are not reachable from any page.
- `RenderImage`: RenderImage renders the 1-based page number to an image.
- `RenderTIFF`: RenderTIFF renders the document to a single multi-page TIFF written to w.
- `Reorder`: Reorder rearranges pages according to order, a slice of 1-based page numbers.
- `ReplaceText`: ReplaceText replaces every occurrence of old with replacement across all pages, returning the total number of replacements.
- `Rotate`: Rotate rotates selected pages clockwise by angle (Rotate90, Rotate180, or Rotate270).
- `Save`: Save writes the document to outputPath.
- `SaveDocx`: SaveDocx writes the document as a Word (.docx) file.
- `SaveEpub`: SaveEpub writes the document as an EPUB file.
- `SaveHTML`: SaveHTML writes the document as an HTML file — self-contained by default; with ResourceDir/ResourceWriter the heavy parts become external files, and with SplitPages each page becomes its own <stem>_p<N>.html.
- `SaveLinearized`: SaveLinearized writes the document to outputPath as a linearized ("fast web view") PDF (ISO 32000-1 Annex F): the first page's objects and a hint table sit at the front so a viewer can render page 1 before the whole file has downloaded.
- `SaveMarkdown`: SaveMarkdown writes the document as a Markdown file.
- `SaveSVG`: SaveSVG exports the document's pages as SVG files.
- `SaveXlsx`: SaveXlsx writes the document as an Excel (.xlsx) workbook file.
- `SearchText`: SearchText finds every occurrence of query across all pages of the document, returning matches page by page in reading order.
- `SetEncryption`: SetEncryption configures every encryption-related setting at once from an EncryptionOptions struct.
- `SetInfo`: SetInfo replaces the document's Info dictionary with the given metadata.
- `SetOpenAction`: SetOpenAction sets the action run when the document opens.
- `SetPageLabels`: SetPageLabels installs the document's /PageLabels number tree so PDF viewers display labels like "i, ii, 1, 2, …" in the navigation pane and page indicators.
- `SetPassword`: SetPassword configures the document to be encrypted when saved.
- `SetPermissions`: SetPermissions configures what operations a viewer allows on the encrypted document (printing, copying, modifying, etc.).
- `SetRotation`: SetRotation sets selected pages to exactly angle (Rotate0, Rotate90, Rotate180, or Rotate270), replacing any existing rotation.
- `SetSVGFontResolver`: SetSVGFontResolver installs a custom resolver.
- `SetXMP`: SetXMP serialises meta into a standard XMP packet and stores it as the /Catalog/Metadata stream (uncompressed, /Type /Metadata /Subtype /XML per ISO 32000-1 §14.3.2).
- `SetXMPRaw`: SetXMPRaw stores data verbatim as the /Catalog/Metadata stream — an escape hatch for callers that produce their own XMP packet.
- `Sign`: Sign configures a digital signature applied on the next Save/WriteTo.
- `Split`: Split returns each page of the document as a separate *Document.
- `SubsetFonts`: SubsetFonts shrinks every embedded TTF (loaded via LoadFont) to only the glyphs actually drawn, replacing each /FontFile2 with a rebuilt subset program and switching the CIDFont's /CIDToGIDMap from /Identity to a stream that maps the original glyph IDs (still used verbatim as CIDs in content streams) to the compact subset glyph IDs.
- `SyncInfoToXMP`: SyncInfoToXMP builds an XMP packet from the document's current /Info dictionary and installs it, so the two metadata stores agree (ISO 32000-1 §14.3.2 recommends consistency when both are present).
- `TaggedContent`: TaggedContent returns the document's tagged-content facade, creating the structure tree and the /MarkInfo, /ViewerPreferences and /StructTreeRoot catalog entries on first call.
- `ValidatePDFA`: ValidatePDFA checks the document against a PDF/A "b"-level conformance profile and returns a report of violations.
- `ValidatePDFUA`: ValidatePDFUA checks the document against a subset of PDF/UA-1 (ISO 14289-1, universal accessibility) and returns a report of violations.
- `ValidateRedactions`: ValidateRedactions performs a pre-flight dry-run parseability check on every page that has at least one RedactAnnotation.
- `VerifySignatures`: VerifySignatures verifies every digital signature in the document and returns one result per signature field, in document order.
- `WriteDocx`: WriteDocx writes the document as a Word (.docx) package to w.
- `WriteEpub`: WriteEpub writes the document as an EPUB 3 package to w.
- `WriteHTML`: WriteHTML writes the document as a single self-contained HTML file to w: per page, a raster background under a text layer (transparent in HTMLModeFaithful, visible in HTMLModeText) and link-annotation overlays.
- `WriteMarkdown`: WriteMarkdown writes the document as Markdown to w.
- `WriteTo`: WriteTo writes the document to w.
- `WriteToLinearized`: WriteToLinearized writes the document as a linearized PDF to w (implements an io.WriterTo-style contract).
- `WriteXlsx`: WriteXlsx writes the document as an Excel (.xlsx) workbook to w.
- `XMP`: XMP returns the document's XMP metadata parsed from the /Catalog/Metadata stream.
- `XMPRaw`: XMPRaw returns the raw bytes of the XMP packet from /Catalog/Metadata, or nil when the document has no XMP stream.

### Flow

`Flow` enables programmatic creation of structured content with paragraphs, headings, tables, and lists via `AddParagraph`, `AddHeading`, `AddTable`, and `AddList`, then renders the content to a `Document` using `FlowOptions` to control layout and styling.

- `AddColumnBreak`: AddColumnBreak forces the following content to start in the next column (or, from the last column, on the next page).
- `AddFloatBox`: AddFloatBox appends a floated box pinned to the given side at width points; the paragraphs that follow wrap around it until the text passes its bottom.
- `AddFloatingBox`: AddFloatingBox appends a floating box, which takes its measured height in the flow (moving to a new page if it does not fit).
- `AddHeading`: AddHeading appends a heading of the given level (1–6).
- `AddImage`: AddImage appends an image scaled to width×height points.
- `AddImageAlt`: AddImageAlt is AddImage with alternate text (used when the flow is tagged).
- `AddList`: AddList appends a bulleted (ordered=false) or numbered list.
- `AddMarkdown`: AddMarkdown appends a Markdown fragment to the flow: its blocks become flow elements (headings, paragraphs, lists, tables, images, …) rendered with the flow's Markdown options.
- `AddParagraph`: AddParagraph appends a paragraph of flowing text (wraps and splits across pages).
- `AddSpacer`: AddSpacer appends vertical space.
- `AddTable`: AddTable appends a table (paginated when taller than a page).
- `Render`: Render lays out the queued elements into the document and returns the number of pages the flow occupies.
- `SetMarkdownOptions`: SetMarkdownOptions sets the theme/options used by subsequent AddMarkdown calls on this flow (fonts, base size, image base path).

### Form

`Form` provides methods to add interactive form fields including text fields, checkboxes, combo boxes, and radio groups via `AddTextField`, `AddCheckbox`, `AddComboBox`, and `AddRadioGroup`, supports exporting form data as JSON or FDF/XFDF, and flattens fields into static content.

- `AddCheckbox`: AddCheckbox creates a checkbox widget on pageNum with the given rectangle and field name.
- `AddComboBox`: AddComboBox creates a single-select dropdown choice field.
- `AddDateField`: AddDateField adds a date field with the given format mask (e.g.
- `AddFileSelectField`: AddFileSelectField adds a file-select text field.
- `AddListBox`: AddListBox creates a single-select list field.
- `AddNumberField`: AddNumberField adds a number field formatted per opts.
- `AddPasswordField`: AddPasswordField adds a masked text field.
- `AddPushButton`: AddPushButton creates a non-toggling button.
- `AddRadioGroup`: AddRadioGroup creates a radio-button parent field plus one widget per item.
- `AddRichTextField`: AddRichTextField adds a rich-text field.
- `AddTextField`: AddTextField creates a single-line text input on pageNum with the given rectangle and field name, auto-creating /AcroForm and the default Helvetica font resource if needed.
- `ExportFDF`: ExportFDF serialises the form's field values as an FDF (Forms Data Format) document — a small PDF-syntax file (%FDF-1.2 … /FDF /Fields [ … ]) that Acrobat and other readers import.
- `ExportJSON`: ExportJSON serialises the form's field values to a typed JSON document keyed by each field's full name: {"name": {"type": "...", "value": ...}}.
- `ExportXFDF`: ExportXFDF serialises the form's field values as an XFDF document.
- `Field`: Field returns the leaf field by FullName, or nil if no such field exists.
- `Fields`: Fields returns all leaf form fields as a flat slice.
- `Flatten`: Flatten bakes every form field's current appearance into its page's content stream and then removes all fields, their widgets, and the /AcroForm dict, producing a non-interactive document that renders the same.
- `HasField`: HasField reports whether a leaf field with the given FullName exists.
- `ImportFDF`: ImportFDF applies field values from an FDF document and returns the number of fields set.
- `ImportJSON`: ImportJSON applies field values from a typed JSON document (the shape ExportJSON produces) and returns the number of fields actually set.
- `ImportXFDF`: ImportXFDF applies field values from an XFDF document and returns the number of fields set.
- `NeedAppearances`: NeedAppearances reports whether /AcroForm/NeedAppearances is true, which tells viewers to regenerate cached /AP appearance streams when displaying form fields.
- `ReadFDF`: ReadFDF reads an FDF document from r and applies it via ImportFDF.
- `ReadJSON`: ReadJSON reads a JSON document from r and applies it via ImportJSON.
- `ReadXFDF`: ReadXFDF reads an XFDF document from r and applies it via ImportXFDF.
- `RemoveField`: RemoveField removes the named field (and all its widget annotations) from /AcroForm/Fields and from each affected page's /Annots.
- `SetNeedAppearances`: SetNeedAppearances toggles /AcroForm/NeedAppearances.
- `WriteFDF`: WriteFDF writes ExportFDF output to w.
- `WriteJSON`: WriteJSON writes ExportJSON output to w.
- `WriteXFDF`: WriteXFDF writes ExportXFDF output to w.

### Annotation

`Annotation` types including `LinkAnnotation`, `HighlightAnnotation`, `StampAnnotation`, and `RedactAnnotation` can be created via `NewLinkAnnotation` and `NewHighlightAnnotation`, managed through `AnnotationCollection`, and attached to pages via `Page.Annotations`.

- `AnnotationType`: Defined as `AnnotationType AnnotationType()`.
- `Color`: Defined as `*Color Color()`.
- `Contents`: Defined as `string Contents()`.
- `Flatten`: Flatten bakes this annotation's normal appearance into the page content and removes the annotation, making it non-interactive.
- `PageIndex`: Defined as `int PageIndex()`.
- `Rect`: Defined as `Rectangle Rect()`.
- `SetColor`: Defined as `SetColor(*Color c)`.
- `SetContents`: Defined as `SetContents(string s)`.
- `SetRect`: Defined as `SetRect(Rectangle r)`.
- `SetTitle`: Defined as `SetTitle(string s)`.
- `Title`: Defined as `string Title()`.

### Path

`Path` and its gradient types `LinearGradient` and `RadialGradient`, along with `TilingPattern`, enable vector drawing on pages, while `Page.AddSVG` and `Page.AddSVGFromStream` import `SVG` content using `SVGFontResolver` for custom font handling.

- `Arc`: Arc adds an arc to the path, approximated by cubic Bezier curves.
- `Close`: Close closes the current subpath with a line back to the most recent MoveTo.
- `CurveTo`: CurveTo adds a cubic Bezier curve from the current point to (x, y) with control points (c1x, c1y) and (c2x, c2y).
- `LineTo`: LineTo adds a straight line segment from the current point to (x, y).
- `MoveTo`: MoveTo begins a new subpath at (x, y).
- `QuadTo`: QuadTo adds a quadratic Bezier curve (one control point) from the current point to (x, y), automatically converted to the equivalent cubic per the standard quadratic-to-cubic formula:

### TableAbsorber

`TableAbsorber` extracts tabular data from PDF pages, and `Document.SaveDocx`, `Document.SaveXlsx`, and `Document.SaveEpub` export documents to Word, Excel, and EPUB formats respectively.

- `TableList`: TableList returns the tables recognized by the last Visit, top-to-bottom.
- `Visit`: Visit runs table detection on the page, replacing the absorber's TableList.

### ValidatePDFA

`Document.ValidatePDFA` and `Document.ValidatePDFUA` validate conformance to PDF/A and PDF/UA standards respectively, returning `PDFAValidationReport` and `PDFUAValidationReport` with detailed compliance information.

### ai

The ai subpackage provides `OcrCopilot` for text recognition and searchable PDF generation, `SummaryCopilot` for document summarization, `ChatCopilot` for conversational queries, and `ImageDescriptionCopilot` for image description and alt-text generation.

### SetEncryption

`Document.SetEncryption` applies password or certificate-based encryption using `EncryptionOptions`, `Document.Sign` signs documents with PKCS#7 signatures using `SignOptions`, and `Document.VerifySignatures` validates existing signatures.

### Page

`Page` provides methods to add text, tables, and `SVG` content via `AddText`, `AddTable`, `AddSVG`, and `AddSVGFromStream`, render pages to images, and search or replace text content.

- `AddFloatingBox`: AddFloatingBox draws box at an absolute position inside rect: it paints the background and border, then lays out the box content within rect minus padding (content that overflows the box is clipped).
- `AddForm`: AddForm places the form on the page so its box maps onto rect, preserving the form's own scale per axis.
- `AddImage`: AddImage adds an image from a file to the page within the given rectangle.
- `AddImageFromStream`: AddImageFromStream adds an image from a reader to the page within the given rectangle.
- `AddInlineImage`: AddInlineImage draws a small image directly into the page content stream as an inline image (BI … ID … EI, ISO 32000-1 §8.9.7) rather than an Image XObject.
- `AddInlineImageFromStream`: AddInlineImageFromStream is the io.Reader variant of AddInlineImage.
- `AddMarkdown`: AddMarkdown renders a Markdown fragment inside the rectangle.
- `AddSVG`: AddSVG reads an SVG file and renders it into the given rectangle on the page.
- `AddSVGFromStream`: AddSVGFromStream renders an SVG from any io.Reader into the given rectangle on the page.
- `AddSVGObject`: AddSVGObject renders a pre-parsed SVG into the given rectangle on the page.
- `AddStamp`: AddStamp draws a stamp onto the page.
- `AddTOC`: AddTOC renders a table of contents from a supplied list of entries into rect on this page.
- `AddTable`: AddTable renders the table inside the given rectangle.
- `AddTaggedList`: AddTaggedList draws a bulleted (ordered=false) or numbered (ordered=true) list of items inside rect and builds its accessible structure: an /L element under parent (nil = the document root), with an /LI per item containing an /Lbl (the bullet/number) and an /LBody (the item text).
- `AddTaggedTable`: AddTaggedTable renders t inside rect like AddTable, and at the same time builds the table's logical structure (/Table → /TR → /TH/TD) under parent (nil = the document root), tagging each cell's content as marked content and bracketing cell backgrounds and borders as /Artifact.
- `AddText`: AddText draws text inside the rectangle using the given style.
- `Annotations`: Annotations returns the page's annotation collection.
- `ArtBox`: ArtBox returns the art box of the page as a Rectangle.
- `BeginLayer`: BeginLayer starts a marked-content section on the page assigned to layer: content drawn after this call (AddText, Draw*, AddImage, …) belongs to the layer until EndLayer.
- `BleedBox`: BleedBox returns the bleed box of the page as a Rectangle.
- `CropBox`: CropBox returns the crop box of the page as a Rectangle.
- `DrawCircle`: DrawCircle strokes and/or fills a circle.
- `DrawEllipse`: DrawEllipse strokes and/or fills an axis-aligned ellipse.
- `DrawLine`: DrawLine strokes a single line segment from→to with the given style.
- `DrawPath`: DrawPath strokes and/or fills the previously-built path.
- `DrawPolygon`: DrawPolygon strokes and/or fills a closed polygon (last point connects back to the first via h).
- `DrawPolyline`: DrawPolyline strokes an open polyline (first and last points are NOT connected).
- `DrawRectangle`: DrawRectangle strokes and/or fills an axis-aligned rectangle.
- `DrawRoundedRectangle`: DrawRoundedRectangle strokes and/or fills an axis-aligned rectangle with rounded corners of the given radius.
- `EndLayer`: EndLayer closes the marked-content section opened by BeginLayer.
- `ExtractImages`: ExtractImages returns all images found on the page.
- `ExtractText`: ExtractText returns the text content of the page.
- `ExtractTextWithLayout`: ExtractTextWithLayout returns structured text lines sorted in visual (top-to-bottom, left-to-right) reading order.
- `Forms`: Forms returns the Form XObjects referenced by the page's resources — the reusable content groups already present (e.g.
- `ImageInfos`: ImageInfos returns metadata for all images found on the page without decoding pixel data.
- `Label`: Label returns the formatted page label for this page as defined by the document's /PageLabels number tree (PDF spec §12.4.2).
- `MediaBox`: MediaBox returns the page's MediaBox as a Rectangle in PDF user space.
- `Number`: Number returns the 1-based page number within the document.
- `Paragraphs`: Paragraphs returns the page's text grouped into columns (sections) and paragraphs.
- `RenderBMP`: RenderBMP renders the page and writes it as an uncompressed BMP.
- `RenderGIF`: RenderGIF renders the page and writes it as GIF (256 colours, quantized).
- `RenderImage`: RenderImage rasterizes the page to an *image.RGBA at the requested DPI.
- `RenderJPEG`: RenderJPEG renders the page and writes it as JPEG.
- `RenderPNG`: RenderPNG renders the page and writes it as PNG.
- `RenderTIFF`: RenderTIFF renders the page and writes it as a single-page Deflate TIFF.
- `ReplaceText`: ReplaceText replaces every occurrence of old with replacement on the page and returns the number of replacements made.
- `Rotation`: Rotation returns the effective rotation of the page in degrees (0, 90, 180, 270).
- `SaveSVG`: SaveSVG writes the page as a standalone SVG file.
- `SearchText`: SearchText finds every occurrence of query on the page and returns the matches in visual reading order (top-to-bottom, left-to-right).
- `SetArtBox`: SetArtBox sets the page's ArtBox (meaningful content extent).
- `SetBleedBox`: SetBleedBox sets the page's BleedBox (production bleed region).
- `SetCropBox`: SetCropBox sets the page's CropBox (the visible region).
- `SetMediaBox`: SetMediaBox sets the page's MediaBox (the full page rectangle) in PDF user space.
- `SetPageSize`: SetPageSize resizes the page by setting its MediaBox to [0 0 width height] (points).
- `SetTrimBox`: SetTrimBox sets the page's TrimBox (intended finished dimensions).
- `Size`: Size returns the page dimensions from its MediaBox.
- `TagArtifact`: TagArtifact brackets a block of page drawing as an /Artifact marked-content sequence, so it is treated as decoration and excluded from the logical structure tree.
- `TagContent`: TagContent draws a block of page content (everything the draw callback emits) inside a marked-content sequence and adds a corresponding leaf structure element of type t as a child of parent (nil = the document root).
- `TrimBox`: TrimBox returns the trim box of the page as a Rectangle.
- `WriteSVG`: WriteSVG writes the page as one standalone SVG document to w.

### JavaScript

`Document.JavaScript` manages document-level `JavaScript`, while `Document.OpenAction`, `Document.SetOpenAction`, and `Document.RemoveOpenAction` control the action executed when the document opens, supporting `GoToAction`, `GoToURIAction`, and `JavaScriptAction`.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/pdf/go/)** — The getting started guide introduces the core concepts and initial setup steps for using Aspose PDF FOSS for Go.
- **[How-to guides & FAQ](https://kb.aspose.org/pdf/go/)** — The how-to guides and FAQ provide practical examples and answers to common questions about PDF operations in Aspose PDF FOSS for Go.
- **[Full API reference](https://reference.aspose.org/pdf/go/)** — The full API reference documents all exported types, functions, and methods available in the `github.com/aspose-pdf-foss/aspose-pdf-foss-for-go` package. It covers all 229 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- **[Contributing guide](CONTRIBUTING.md)** — The contributing guide outlines the process for submitting code changes, reporting issues, and collaborating on Aspose PDF FOSS for Go.
- **[Changelog](CHANGELOG.md)** — The changelog records notable changes, bug fixes, and new features introduced in each release of Aspose PDF FOSS for Go.
- **[Open an issue](https://github.com/aspose-pdf-foss/aspose-pdf-foss-for-go/issues)** — The issue tracker allows users to report bugs, request features, and discuss improvements for Aspose PDF FOSS for Go.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go/issues).

## Scope and Limitations

Aspose PDF FOSS for Go provides core PDF creation, manipulation, and conversion capabilities for the Go programming language, targeting developers who need programmatic control over PDF documents without requiring a commercial license.

- Viewer permissions enforced by PDF viewers are written as an encryption bitfield but the library itself does not act as a DRM mechanism, and linearization cannot be combined with encryption or digital signing in the same document.
- The `SaveLinearized` method optimizes PDFs for fast web viewing but cannot be used together with encryption or digital signing in the same document.
- Certificate-based encryption via Recipients accepts RSA recipients only using PKCS#1 v1.5 key transport, and does not support elliptic curve recipients or the legacy RC4 sub-filters.
- `SearchText` and `ReplaceText` match content only within a single text line, so queries that span line breaks are not found or replaced.
- `Page.RenderImage` does not support mesh shadings (PDF shading types 4-7); other shading types, patterns, and blend modes render normally.
- `Table` does not yet support content-driven auto-fit column widths, per-side border dash patterns, or a `RowSpan` group splitting across a page break.

These limitations don't apply to [Aspose PDF for Go — Enterprise Edition](https://products.aspose.com/pdf/go-cpp/). Aspose PDF FOSS for Go provides open-source PDF processing capabilities in Go, while Aspose.PDF for Go via C++ extends functionality with advanced features such as digital signature verification, form filling, and document conversion workflows.

## Development and Testing

Build and test the Aspose PDF FOSS for Go library by running go build ./... and go test ./... in the repository root, which uses the Go 1.24 runtime and the module `github.com/aspose-pdf-foss/aspose-pdf-foss-for-go`.

Releases run through the [lint workflow](.github/workflows/lint.yml).

```bash
go build ./...
go test ./...
```

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.

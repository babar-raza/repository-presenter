# Aspose.Cells FOSS for Cpp

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](License/LICENSE.txt) [![Contributors](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/graphs/contributors)

[![Aspose.Cells FOSS for Cpp](https://products.aspose.org/media/cells/cpp/banner-readme.png)](https://products.aspose.org/cells/cpp/)

Aspose.Cells FOSS for Cpp is a free, open-source, MIT-licensed C++ library for creating, loading, editing, and saving Excel .xlsx workbooks without requiring Microsoft Excel. It solves the problem of programmatic spreadsheet manipulation in C++ applications by exposing a familiar API surface built around `Workbook`, `Worksheet`, and `Cell` objects, matching the structure of Aspose's commercial spreadsheet products. Developers use it to generate reports, process templates, and automate Excel workflows in cross-platform C++17 projects with no external runtime dependencies.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [License](#license)

## At a Glance

```mermaid
flowchart TD
  PRODUCT["Aspose.Cells FOSS for Cpp"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Create and save .xlsx workbooks"]
      c2["Read and write cell values and formulas"]
      c3["Apply cell and range formatting"]
      c4["Manage worksheet features"]
    end
    subgraph capr[" "]
      direction TB
      c5["Apply conditional formatting and validation"]
      c6["Manage hyperlinks and defined names"]
      c7["Access document properties"]
      c8["Integrate via CMake"]
    end
  end
  PRODUCT --> Capabilities
```

## Key Capabilities

- **Create and save .xlsx workbooks.** Create a blank workbook with the default worksheet or load an existing file from a path or in-memory stream, then save it as an .xlsx file using the `SaveFormat` enumeration.
- **Read and write cell values and formulas.** Insert values of multiple types into cells using `PutValue` and retrieve them as a variant-typed `CellValue`, while setting and reading formulas with `SetFormula` and `GetFormula`.
- **Apply cell and range formatting.** Apply formatting to cells by retrieving and setting a `Style` that bundles `Font` properties, fill patterns, foreground and background colors, borders, and alignment options.
- **Manage worksheet features.** Configure worksheet visibility, zoom, gridlines, headers, right-to-left layout, and protection using the `AutoFilter`, `PageSetup`, and `WorksheetProtection` interfaces.
- **Apply conditional formatting and validation.** Apply rule-driven formatting to cell ranges with `ConditionalFormattingCollection` and enforce input constraints using `ValidationCollection` scoped to specific `CellArea` ranges.
- **Manage hyperlinks and defined names.** Attach hyperlinks to cells with `HyperlinkCollection` and manage workbook- or sheet-scoped named ranges through `DefinedNameCollection` with optional comment strings.
- **Access document properties.** Access core and extended metadata of a workbook through `WorkbookProperties` and `DocumentProperties` exposed by the `Workbook` class.
- **Integrate via CMake.** Integrate the library into a CMake project using version 3.16 or later with no external runtime dependencies.

## Installation

`aspose_cells_foss_cpp` is not yet published on any package registry; build it from a source checkout instead, verified against this revision:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp.git
cd Aspose.Cells-FOSS-for-Cpp
cmake -S . -B build
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`, no dependency is on the library target's public link interface, so a consumer links nothing beyond the library itself.

### Native and System Requirements

- Requires C++ `17` (`CMAKE_CXX_STANDARD` in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`).

## Quick Start

The example creates a new workbook, populates the first worksheet with product names, prices, and a SUM formula, applies header styling, and saves the file as `products.xlsx`.

```cpp
#include "aspose/cells_foss/Workbook.h"
#include "aspose/cells_foss/WorksheetCollection.h"
#include "aspose/cells_foss/Worksheet.h"
#include "aspose/cells_foss/Cell.h"
#include "aspose/cells_foss/Style.h"
#include "aspose/cells_foss/Color.h"
#include "aspose/cells_foss/Font.h"

using namespace Aspose::Cells_FOSS;

int main() {
    Workbook workbook;
    Worksheet& sheet = workbook.GetWorksheets()[0];

    sheet.SetName("Products");
    sheet.GetCells()["A1"].PutValue("Product");
    sheet.GetCells()["B1"].PutValue("Price");
    sheet.GetCells()["A2"].PutValue("Apple");
    sheet.GetCells()["B2"].PutValue(2.99);
    sheet.GetCells()["A3"].PutValue("Orange");
    sheet.GetCells()["B3"].PutValue(1.99);
    sheet.GetCells()["B4"].SetFormula("=SUM(B2:B3)");

    Style headerStyle = sheet.GetCells()["A1"].GetStyle();
    Font font;
    font.SetBold(true);
    font.SetColor(Color::FromArgb(255, 255, 255, 255));
    headerStyle.SetFont(font);
    headerStyle.SetPattern(FillPattern::Solid);
    headerStyle.SetForegroundColor(Color::FromArgb(255, 34, 120, 212));
    sheet.GetCells()["A1"].SetStyle(headerStyle);
    sheet.GetCells()["B1"].SetStyle(headerStyle);

    workbook.Save("products.xlsx");
    return 0;
}
```

## API Reference

Aspose.Cells FOSS for Cpp provides the `Aspose.Cells_FOSS.Workbook` class as the primary entry point for creating and manipulating spreadsheet files, with `Aspose.Cells_FOSS.Worksheet`, `Aspose.Cells_FOSS.Cells`, and `Aspose.Cells_FOSS.Cell` forming the core object graph for working with individual sheets and cells. The library supports C++17 and requires CMake 3.16 or later.

The verified public surface has 195 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AutoFilter` | Aspose.Cells_FOSS.AutoFilter represents an auto-filter applied to a range of cells in a worksheet, enabling filtering and sorting operations on tabular data. |
| `AutoFilterColorFilter` | Aspose.Cells_FOSS.AutoFilterColorFilter represents a color-based filter condition used in an auto-filter to include or exclude cells by their background or font color. |
| `AutoFilterCustomFilter` | Aspose.Cells_FOSS.AutoFilterCustomFilter represents a custom filter condition defined by an operator and a value for filtering cell contents. |
| `AutoFilterCustomFilterCollection` | Aspose.Cells_FOSS.AutoFilterCustomFilterCollection is a collection of custom filter conditions that can be applied together using logical AND or OR logic. |
| `AutoFilterCustomFilterCollection.Iterator` | Aspose.Cells_FOSS.AutoFilterCustomFilterCollection.Iterator provides sequential access to each custom filter condition stored in the collection. |
| `AutoFilterDynamicFilter` | Aspose.Cells_FOSS.AutoFilterDynamicFilter represents a dynamic filter condition such as above average or today, used to filter data based on computed criteria. |
| `AutoFilterSortCondition` | Aspose.Cells_FOSS.AutoFilterSortCondition defines a sorting rule for an auto-filtered range, including sort direction, sort by type, and optional custom lists or icon sets. |
| `AutoFilterSortConditionCollection` | Aspose.Cells_FOSS.AutoFilterSortConditionCollection holds a sequence of sort conditions applied to an auto-filtered range in order of priority. |
| `AutoFilterSortConditionCollection.Iterator` | Aspose.Cells_FOSS.AutoFilterSortConditionCollection.Iterator enables iteration over the sort conditions contained in the collection. |
| `AutoFilterSortState` | Aspose.Cells_FOSS.AutoFilterSortState stores the overall sorting configuration for an auto-filtered range, including the reference area and applied sort conditions. |
| `AutoFilterSupport` | Aspose.Cells_FOSS.AutoFilterSupport provides utility methods to manage auto-filter settings on a worksheet, such as setting the filtered range and retrieving sort state. |
| `AutoFilterTop10` | Aspose.Cells_FOSS.AutoFilterTop10 represents a top or bottom N items filter condition used to include only the largest or smallest values in an auto-filtered column. |
| `Border` | Aspose.Cells_FOSS.Border represents the border formatting of a cell or range, including style, color, and line weight. |
| `Borders` | Aspose.Cells_FOSS.Borders provides access to the individual border sides of a cell or range for setting their formatting properties. |
| `CalculationProperties` | Aspose.Cells_FOSS.CalculationProperties holds settings that control how formulas are calculated in a workbook, such as iteration options and precision mode. |
| `Cell` | Aspose.Cells_FOSS.Cell represents a single cell in a worksheet and provides methods to read or write its value, format, and style. |
| `CellArea` | Aspose.Cells_FOSS.CellArea defines a rectangular range of cells using start and end row and column indices. |
| `CellFormatValue` | Aspose.Cells_FOSS.CellFormatValue represents the formatted display string of a cell after applying number formatting rules. |
| `CellValue` | Aspose.Cells_FOSS.CellValue encapsulates the raw data stored in a cell, supporting multiple underlying types such as string, double, or boolean. |
| `Cells` | Aspose.Cells_FOSS.Cells represents the collection of all cells in a worksheet and provides indexed access to individual cells by address or index. |
| `CellsException` | Aspose.Cells_FOSS.CellsException is raised when an error occurs during cell-related operations within the library. |
| `Color` | Aspose.Cells_FOSS.Color represents a color value used for cell or font formatting, supporting ARGB components and predefined color names. |
| `Column` | Aspose.Cells_FOSS.Column represents a single column in a worksheet and provides methods to adjust its width, style, and visibility. |
| `ColumnCollection` | Aspose.Cells_FOSS.ColumnCollection is a container for all column objects in a worksheet, allowing indexed access and enumeration. |
| `ConditionalFormattingCollection` | Aspose.Cells_FOSS.ConditionalFormattingCollection holds all conditional formatting rules applied to a worksheet and supports adding or removing rules. |
| `AlignmentValue` | Aspose.Cells_FOSS.Core.AlignmentValue specifies the horizontal and vertical alignment of text within a cell. |
| `AutoFilterColorFilterModel` | Aspose.Cells_FOSS.Core.AutoFilterColorFilterModel provides a model for configuring color-based auto-filter conditions. |
| `AutoFilterCustomFilterModel` | Aspose.Cells_FOSS.Core.AutoFilterCustomFilterModel provides a model for configuring custom auto-filter conditions using operators and values. |
| `AutoFilterDynamicFilterModel` | Aspose.Cells_FOSS.Core.AutoFilterDynamicFilterModel provides a model for configuring dynamic auto-filter conditions such as above average or today. |
| `AutoFilterModel` | Aspose.Cells_FOSS.Core.AutoFilterModel provides a unified interface for creating and managing auto-filter configurations on a worksheet. |
| `AutoFilterSortConditionModel` | Aspose.Cells_FOSS.Core.AutoFilterSortConditionModel provides a model for defining sort conditions used in auto-filtered ranges. |
| `AutoFilterSortStateModel` | Aspose.Cells_FOSS.Core.AutoFilterSortStateModel provides a model for storing and applying the overall sort state of an auto-filtered range. |
| `AutoFilterTop10Model` | Aspose.Cells_FOSS.Core.AutoFilterTop10Model provides a model for configuring top or bottom N items auto-filter conditions. |
| `BorderSideValue` | Aspose.Cells_FOSS.Core.BorderSideValue specifies which side of a cell (top, bottom, left, right) a border applies to. |
| `BordersValue` | Aspose.Cells_FOSS.Core.BordersValue holds the combined border settings for all sides of a cell. |
| `CalculationPropertiesModel` | Aspose.Cells_FOSS.Core.CalculationPropertiesModel provides a model for configuring workbook-level calculation options. |
| `CellAddress` | Aspose.Cells_FOSS.Core.CellAddress represents the row and column indices of a cell within a worksheet. |
| `CellRecord` | Represents a cell record in a spreadsheet, storing its value, formula, style, and metadata such as kind and explicit storage flag. |
| `ColorValue` | Encapsulates a color using its red, green, blue, and alpha components. |
| `ColumnRangeModel` | Represents a range of columns in a worksheet, including their visibility, width, and style index. |
| `ConditionalFormattingModel` | Holds a collection of conditional formatting areas and their associated conditions for a worksheet. |
| `CoreDocumentPropertiesModel` | Provides access to core document properties such as title, author, creation date, and description. |
| `DateSerialConverter` | Converts between serial date numbers and date-time values using a specified date system. |
| `DefinedNameModel` | Represents a defined name in a workbook, associating a name with a cell reference or formula. |
| `DiagnosticBag` | Collects diagnostic entries generated during workbook processing for review and troubleshooting. |
| `DiagnosticEntry` | Represents a single diagnostic message with a severity level and descriptive text. |
| `DocumentPropertiesModel` | Extends core document properties with additional built-in properties like category and keywords. |
| `ExtendedDocumentPropertiesModel` | Provides access to extended document properties such as company name and manager. |
| `FilterColumnModel` | Represents a filtered column in a worksheet, including its index and filter criteria. |
| `FontValue` | Describes font attributes such as name, size, bold, italic, and color for text formatting. |
| `FormatConditionModel` | Represents a single format condition within a conditional formatting rule, defining its type and criteria. |
| `HeaderFooterModel` | Manages header and footer content for a worksheet, including left, center, and right sections. |
| `HyperlinkModel` | Represents a hyperlink attached to a cell, including its address, text display, and screen tip. |
| `MergeRegion` | Represents a merged cell region in a worksheet, defined by its top-left and bottom-right coordinates. |
| `NumberFormatValue` | Encapsulates a custom or built-in number format string applied to a cell. |
| `PageMarginsModel` | Stores page margin settings for a worksheet, including top, bottom, left, and right margins. |
| `PageSetupModel` | Provides page setup options for a worksheet, including orientation, paper size, and print area. |
| `PrintOptionsModel` | Controls print options for a worksheet, such as gridlines, headings, and draft quality. |
| `ProtectionValue` | Represents protection settings for a worksheet or workbook, such as password and allowed operations. |
| `RowModel` | Represents a row in a worksheet, including its height, visibility, and style index. |
| `SharedStringRepository` | Manages a shared string table used to optimize storage of repeated string values in a workbook. |
| `StyleRepository` | Stores and manages styles available for use in a workbook. |
| `StyleValue` | Encapsulates all formatting attributes for a cell, including font, alignment, border, and fill. |
| `ValidationModel` | Represents a data validation rule applied to a range of cells, including type, operator, and formulas. |
| `WorkbookModel` | Represents a workbook, providing access to worksheets, styles, defined names, and document properties. |
| `WorkbookPropertiesModel` | Stores workbook-level properties such as default sheet count and calculation settings. |
| `WorkbookProtectionModel` | Manages workbook-level protection settings, including structure and window protection. |
| `WorkbookSettingsModel` | Holds workbook-wide settings such as calculation mode, precision, and iteration options. |
| `WorkbookViewModel` | Represents the view settings for a workbook, such as window state, zoom level, and active sheet. |
| `WorksheetModel` | Represents a worksheet in a spreadsheet document and provides access to its cells, columns, rows, protection, view, and formatting settings. |
| `WorksheetProtectionModel` | Encapsulates the protection settings for a worksheet, including password hashing, algorithm configuration, and permissions for operations like formatting cells and inserting rows. |
| `WorksheetViewModel` | Stores the view settings for a worksheet, such as visibility state and tab color. |
| `CoreDocumentProperties` | Provides access to the core document properties of a spreadsheet file, such as title, author, and keywords. |
| `DateTime` | Represents a date and time value used within spreadsheet calculations and formatting. |
| `DefinedName` | Represents a defined name in a workbook, which can refer to a cell range, formula, or constant value. |
| `DefinedNameCollection` | Contains a collection of defined names in a workbook. |
| `DefinedNameUtility` | Provides utility methods for working with defined names, such as parsing and validating name references. |
| `DisplayFormatSectionInfo` | Describes a section of formatted display text, including its style and content. |
| `DisplayTextDateFormatSupport` | Supports date formatting when converting cell values to their display strings. |
| `DisplayTextFormatter` | Formats cell values into their display strings according to cell formatting rules. |
| `DisplayTextFormatterSupport` | Provides support for formatting cell values into display strings, including locale and date handling. |
| `DisplayTextLocaleSupport` | Provides locale-specific support for formatting cell values into display strings. |
| `DocumentProperties` | Encapsulates both core and extended document properties of a spreadsheet file. |
| `ExtendedDocumentProperties` | Provides access to extended document properties of a spreadsheet file, such as company name and manager. |
| `FillValue` | Represents the value used to fill a pattern in cell styling. |
| `FilterColumn` | Represents a filtered column in a worksheet's auto filter, including its filter criteria. |
| `FilterColumnCollection` | Contains a collection of filter columns used in a worksheet's auto filter. |
| `FilterColumnCollection.Iterator` | Provides an iterator to traverse the collection of filter columns in a worksheet's auto filter. |
| `FilterValueCollection` | Contains a collection of filter values used to filter data in a column. |
| `Font` | Represents the font settings used in cell styling, including name, size, color, and style attributes. |
| `FormatCondition` | Represents a conditional formatting rule applied to a cell range. |
| `FormatConditionCollection` | Contains a collection of conditional formatting rules for a worksheet. |
| `FormulaException` | Represents an exception thrown when a formula parsing or evaluation error occurs. |
| `Hyperlink` | Represents a hyperlink attached to a cell, including its address, display text, and screen tip. |
| `HyperlinkCollection` | Contains a collection of hyperlinks in a worksheet. |
| `IWarningCallback` | Defines a callback interface for receiving warnings during file loading or processing. |
| `ValidationMessage` | Represents a validation message shown to the user when input does not meet validation rules. |
| `WorkbookValidator` | Validates the data in a workbook against defined validation rules. |
| `InvalidFileFormatException` | Represents an exception thrown when a file is not in a supported or valid format. |
| `LoadDiagnostics` | Contains diagnostic information about issues encountered while loading a spreadsheet file. |
| `LoadIssue` | Represents a single issue encountered during file loading, including its description and severity. |
| `LoadOptions` | Provides options for customizing how a spreadsheet file is loaded. |
| `NumberFormat` | NumberFormat represents a number format used to display cell values in Aspose.Cells FOSS for Cpp. |
| `CaseInsensitiveEqual` | CaseInsensitiveEqual provides a case-insensitive equality comparison for string keys in packaging operations. |
| `CaseInsensitiveHash` | CaseInsensitiveHash computes a hash code for string keys in a case-insensitive manner for packaging operations. |
| `IPackageReader` | IPackageReader defines the interface for reading parts and relationships from a package in Aspose.Cells FOSS for Cpp. |
| `IPackageWriter` | IPackageWriter defines the interface for writing parts and relationships to a package in Aspose.Cells FOSS for Cpp. |
| `MissingPartException` | MissingPartException is raised when a required part is missing from a package during loading. |
| `PackageLoadContext` | PackageLoadContext provides access to the package and workbook being loaded during package loading operations. |
| `PackageModel` | PackageModel represents the in-memory structure of a package, including its parts and relationships. |
| `PackagePartDescriptor` | PackagePartDescriptor describes a part in a package, including its URI, content type, and category. |
| `PackageStructureException` | PackageStructureException is raised when the package structure is invalid or corrupted. |
| `PackagingConventions` | PackagingConventions defines the conventions and rules for organizing parts and relationships in a package. |
| `RelationshipDescriptor` | RelationshipDescriptor describes a relationship between parts in a package, including its type, target, and identifier. |
| `RelationshipResolutionException` | RelationshipResolutionException is raised when a relationship target cannot be resolved during package loading. |
| `PageSetup` | PageSetup controls page layout settings such as orientation, paper size, margins, headers, footers, and print area for a worksheet. |
| `Row` | Row represents a single row in a worksheet and provides access to its cells and formatting. |
| `RowCollection` | RowCollection contains all rows in a worksheet and provides indexed access to individual rows. |
| `SaveOptions` | SaveOptions provides configuration settings for customizing how a workbook is saved. |
| `Style` | Style defines the formatting attributes such as font, fill, border, and alignment applied to cells. |
| `StyleException` | StyleException is raised when an invalid style operation is attempted. |
| `StyleValueSanitizer` | StyleValueSanitizer ensures that style values conform to supported formats and constraints. |
| `StylesheetLoadContext` | StylesheetLoadContext provides access to the workbook and stylesheet being loaded during stylesheet loading. |
| `StylesheetSaveContext` | StylesheetSaveContext provides access to the workbook and stylesheet being saved during stylesheet saving. |
| `UnsupportedFeatureException` | UnsupportedFeatureException is raised when an unsupported feature is encountered during processing. |
| `Validation` | Validation defines data validation rules applied to cells to restrict the values that can be entered. |
| `ValidationCollection` | ValidationCollection contains all validation rules defined for a worksheet. |
| `WarningInfo` | WarningInfo provides details about a warning encountered during workbook processing. |
| `Workbook` | Workbook represents an entire Excel workbook and provides access to its worksheets, styles, and properties. |
| `WorkbookLoadException` | WorkbookLoadException is raised when an error occurs while loading a workbook from a file or stream. |
| `WorkbookProperties` | WorkbookProperties stores global settings and metadata for a workbook. |
| `WorkbookPropertySupport` | WorkbookPropertySupport provides methods to query and modify workbook property support capabilities. |
| `WorkbookProtection` | WorkbookProtection controls password-based protection options for a workbook structure and windows. |
| `WorkbookSaveException` | Represents an exception thrown when an error occurs while saving a workbook in Aspose.Cells FOSS for Cpp. |
| `WorkbookSettings` | Provides settings that control workbook-level behavior such as culture and the 1904 date system. |
| `WorkbookView` | Represents the view settings for a workbook, including window position, size, and visibility options. |
| `Worksheet` | Represents a worksheet within a workbook, providing access to cells, formatting, protection, and other sheet-level features. |
| `WorksheetCollection` | Represents a collection of worksheets contained within a workbook. |
| `WorksheetDefinedNamesState` | Encapsulates the state of defined names for a worksheet, including name-to-range mappings. |
| `WorksheetProtection` | Represents protection settings applied to a worksheet to restrict editing. |
| `XNamespace` | Represents an XML namespace used within workbook XML structures. |
| `XlsxDocumentProperties` | Encapsulates document properties for an XLSX workbook, such as title, author, and keywords. |
| `XlsxWorkbookArchiveHelpers` | Provides helper methods for working with archived XLSX workbook content. |
| `XlsxWorkbookAutoFilter` | Represents the auto-filter settings applied to a workbook. |
| `XlsxWorkbookConditionalFormatting` | Represents conditional formatting rules applied to a workbook. |
| `XlsxWorkbookDefinedNames` | Represents defined names scoped to the entire workbook. |
| `XlsxWorkbookHyperlinks` | Represents hyperlinks defined at the workbook level. |
| `XlsxWorkbookPageSetup` | Represents page setup options for the entire workbook. |
| `XlsxWorkbookProperties` | Encapsulates core workbook properties such as calculation mode and default sheet name. |
| `XlsxWorkbookSerializer` | Supports serialization of workbook data to XLSX format. |
| `XlsxWorkbookSerializerCommon` | Provides common functionality shared by workbook serializers. |
| `XlsxWorkbookStyles` | Represents the styles collection for a workbook. |
| `XlsxWorkbookStylesValueHelpers` | Provides helper methods for working with style values in a workbook. |
| `XlsxWorkbookStylesXml` | Handles XML serialization and deserialization of workbook styles. |
| `XlsxWorkbookValidations` | Represents data validation rules applied at the workbook level. |
| `XlsxWorkbookWorksheetProtection` | Encapsulates worksheet protection settings applied at the workbook level. |
| `XlsxWorkbookWorksheetViews` | Represents view settings for individual worksheets within a workbook. |
| `SharedStringTableXmlMapper` | Maps shared string table content in XML format for workbook processing. |
| `StylesheetXmlMapper` | Maps stylesheet content in XML format for workbook styling. |
| `WorkbookXmlMapper` | Maps workbook-level XML content during serialization or deserialization. |
| `WorksheetXmlMapper` | Maps worksheet-level XML content during serialization or deserialization. |
| `XmlParsingException` | Represents an exception thrown when an error occurs while parsing XML content. |
| `XmlAttribute` | Represents an XML attribute within a workbook's XML structure. |
| `XmlDocument` | Represents an XML document used in workbook processing. |
| `XmlElement` | Represents an XML element within a workbook's XML structure. |
| `XmlNodeData` | Encapsulates data associated with an XML node in workbook processing. |
| `ZipArchive` | Represents a ZIP archive used to store or retrieve XLSX workbook content. |
| `ZipArchiveEntry` | Represents a single entry within a ZIP archive used for XLSX workbook storage. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `BorderStyleType` | Aspose.Cells_FOSS.BorderStyleType enumerates the available line styles for cell borders, such as thin, thick, or dashed. |
| `CellValueType` | Aspose.Cells_FOSS.CellValueType enumerates the possible data types that a cell value can hold, such as string, numeric, or boolean. |
| `BorderStyle` | Aspose.Cells_FOSS.Core.BorderStyle defines the line style and color of a cell border. |
| `CellValueKind` | Indicates the data type of a cell value, such as boolean, numeric, string, or error. |
| `DateSystem` | Defines the date system used for serial date calculations, such as 1900 or 1904. |
| `Core.DiagnosticSeverity` | Indicates the severity level of a diagnostic entry, such as info, warning, or error. |
| `FillPatternKind` | Specifies the fill pattern used in a cell style, such as solid, gray75, or light horizontal. |
| `HorizontalAlignment` | Specifies the horizontal alignment of text within a cell, such as left, center, or right. |
| `PageOrientation` | Specifies the page orientation for printing, such as portrait or landscape. |
| `SheetVisibility` | Specifies the visibility state of a worksheet, such as visible, hidden, or very hidden. |
| `VerticalAlignment` | Specifies the vertical alignment of text within a cell, such as top, center, or bottom. |
| `Cells_FOSS.DiagnosticSeverity` | Indicates the severity level of a diagnostic issue encountered during file loading or processing. |
| `FillPattern` | Specifies the fill pattern used in cell styling, such as solid, gray75, or light horizontal. |
| `FilterOperatorType` | Specifies the operator used in filter criteria, such as equal, greater than, or between. |
| `FormatConditionType` | Specifies the type of conditional formatting rule, such as cell value, formula, or time period. |
| `HorizontalAlignmentType` | Specifies the horizontal alignment of text in a cell, such as left, center, or right. |
| `ValidationMessageSeverity` | Indicates the severity level of a validation message, such as warning or stop. |
| `LoadFormat` | Specifies the format of a file being loaded, such as Excel 97-2003 or Excel 2007+. |
| `OperatorType` | OperatorType specifies the comparison operator used in conditional formatting and validation rules. |
| `PageOrientationType` | PageOrientationType specifies the orientation of a page when printing or exporting a worksheet. |
| `PaperSizeType` | PaperSizeType specifies the paper size used when printing or exporting a worksheet. |
| `SaveFormat` | SaveFormat specifies the file format used when saving a workbook to disk. |
| `TargetModeType` | TargetModeType specifies whether a relationship target is internal to the package or external. |
| `ValidationAlertType` | ValidationAlertType specifies the type of alert displayed when a user enters invalid data. |
| `ValidationType` | ValidationType specifies the type of data validation applied to a cell or range. |
| `VerticalAlignmentType` | VerticalAlignmentType specifies the vertical alignment of text within a cell. |
| `VisibilityType` | VisibilityType specifies whether a worksheet or row/column is visible, hidden, or collapsed. |

#### Detailed Member Reference

### Workbook

The `Aspose.Cells_FOSS.Workbook` class enables creating new workbooks, loading existing files, and saving results in various formats including XLSX via the `Aspose.Cells_FOSS.SaveFormat` enumeration, while providing access to worksheets, properties, and defined names through its member methods.

- `Dispose`: Defined as `void Dispose()`.
- `EnsureUniqueDefinedName`: Defined as `void EnsureUniqueDefinedName(Core::DefinedNameModel currentDefinedName, std::string_view name, std::optional<int> localSheetIndex)`.
- `EnsureUniqueSheetName`: Defined as `void EnsureUniqueSheetName(std::string_view sheetName, std::optional<std::reference_wrapper<const Core::WorksheetModel>> currentSheet)`.
- `EnsureValidDefinedNameScope`: Defined as `void EnsureValidDefinedNameScope(std::optional<int> localSheetIndex)`.
- `GetDefinedNames`: Defined as `DefinedNameCollection GetDefinedNames()`.
- `GetDefinedNamesModel`: Defined as `std::vector<Core::DefinedNameModel> GetDefinedNamesModel()`.
- `GetDocumentProperties`: Defined as `DocumentProperties GetDocumentProperties()`.
- `GetLoadDiagnostics`: Defined as `LoadDiagnostics GetLoadDiagnostics()`.
- `GetModel`: Defined as `Core::WorkbookModel GetModel()`.
- `GetProperties`: Defined as `WorkbookProperties GetProperties()`.
- `GetSettings`: Defined as `WorkbookSettings GetSettings()`.
- `GetWorksheets`: Defined as `WorksheetCollection GetWorksheets()`.
- `Save`: Defined as `void Save(std::string_view fileName)`.
- `Workbook`: Defined as `Workbook Workbook()`.

### Cell

The `Aspose.Cells_FOSS.Cell` class represents a single cell in a worksheet and provides methods to set and retrieve values, formulas, and styles, with `Aspose.Cells_FOSS.CellValue` exposing typed access to the underlying data.

- `GetColumn`: Defined as `int GetColumn()`.
- `GetDisplayStringValue`: Defined as `std::string GetDisplayStringValue()`.
- `GetFormula`: Defined as `std::string GetFormula()`.
- `GetRow`: Defined as `int GetRow()`.
- `GetStringValue`: Defined as `std::string GetStringValue()`.
- `GetStyle`: Defined as `Style GetStyle()`.
- `GetType`: Defined as `CellValueType GetType()`.
- `GetValue`: Defined as `CellValue GetValue()`.
- `PutValue`: Defined as `void PutValue(char value)`.
- `SetFormula`: Defined as `void SetFormula(std::string_view value)`.
- `SetStyle`: Defined as `void SetStyle(Style style)`.
- `SetValue`: Defined as `void SetValue(CellValue value)`.

### Style

The `Aspose.Cells_FOSS.Style` class allows configuring cell appearance through font settings via `Aspose.Cells_FOSS.Font`, background and foreground colors via `Aspose.Cells_FOSS.Color`, and fill patterns via `Aspose.Cells_FOSS.FillPattern`.

- `Borders`: Defined as `Borders Borders()`.
- `Clone`: Defined as `Style Clone()`.
- `Color`: Defined as `Color Color()`.
- `FillPattern`: Defined as `FillPattern FillPattern()`.
- `Font`: Defined as `Font Font()`.
- `FromCore`: Defined as `Style FromCore(Core::StyleValue value)`.
- `GetBackgroundColor`: Defined as `Color GetBackgroundColor()`.
- `GetBorders`: Defined as `Borders GetBorders()`.
- `GetCustom`: Defined as `std::string GetCustom()`.
- `GetFont`: Defined as `Font GetFont()`.
- `GetForegroundColor`: Defined as `Color GetForegroundColor()`.
- `GetHorizontalAlignment`: Defined as `HorizontalAlignmentType GetHorizontalAlignment()`.
- `GetIndentLevel`: Defined as `int GetIndentLevel()`.
- `GetIsHidden`: Defined as `bool GetIsHidden()`.
- `GetIsLocked`: Defined as `bool GetIsLocked()`.
- `GetNumber`: Defined as `int GetNumber()`.
- `GetNumberFormat`: Defined as `std::string GetNumberFormat()`.
- `GetPattern`: Defined as `FillPattern GetPattern()`.
- `GetReadingOrder`: Defined as `int GetReadingOrder()`.
- `GetRelativeIndent`: Defined as `int GetRelativeIndent()`.
- `GetShrinkToFit`: Defined as `bool GetShrinkToFit()`.
- `GetTextRotation`: Defined as `int GetTextRotation()`.
- `GetVerticalAlignment`: Defined as `VerticalAlignmentType GetVerticalAlignment()`.
- `GetWrapText`: Defined as `bool GetWrapText()`.
- `HorizontalAlignmentType`: Defined as `HorizontalAlignmentType HorizontalAlignmentType()`.
- `SetBackgroundColor`: Defined as `void SetBackgroundColor(Color value)`.
- `SetBorders`: Defined as `void SetBorders(Borders value)`.
- `SetCustom`: Defined as `void SetCustom(std::string value)`.
- `SetFont`: Defined as `void SetFont(Font value)`.
- `SetForegroundColor`: Defined as `void SetForegroundColor(Color value)`.
- `SetHorizontalAlignment`: Defined as `void SetHorizontalAlignment(HorizontalAlignmentType value)`.
- `SetIndentLevel`: Defined as `void SetIndentLevel(int value)`.
- `SetIsHidden`: Defined as `void SetIsHidden(bool value)`.
- `SetIsLocked`: Defined as `void SetIsLocked(bool value)`.
- `SetNumber`: Defined as `void SetNumber(int value)`.
- `SetNumberFormat`: Defined as `void SetNumberFormat(std::string value)`.
- `SetPattern`: Defined as `void SetPattern(FillPattern value)`.
- `SetReadingOrder`: Defined as `void SetReadingOrder(int value)`.
- `SetRelativeIndent`: Defined as `void SetRelativeIndent(int value)`.
- `SetShrinkToFit`: Defined as `void SetShrinkToFit(bool value)`.
- `SetTextRotation`: Defined as `void SetTextRotation(int value)`.
- `SetVerticalAlignment`: Defined as `void SetVerticalAlignment(VerticalAlignmentType value)`.
- `SetWrapText`: Defined as `void SetWrapText(bool value)`.
- `ToCore`: Defined as `Core::StyleValue ToCore()`.
- `VerticalAlignmentType`: Defined as `VerticalAlignmentType VerticalAlignmentType()`.

### Worksheet

The `Aspose.Cells_FOSS.Worksheet` class provides access to cell data through `Aspose.Cells_FOSS.Cells`, supports data filtering via `Aspose.Cells_FOSS.AutoFilter`, and offers protection and page setup capabilities via `Aspose.Cells_FOSS.WorksheetProtection` and `Aspose.Cells_FOSS.PageSetup`.

- `GetAutoFilter`: Defined as `AutoFilter GetAutoFilter()`.
- `GetCells`: Defined as `Cells GetCells()`.
- `GetConditionalFormattings`: Defined as `ConditionalFormattingCollection GetConditionalFormattings()`.
- `GetHyperlinks`: Defined as `HyperlinkCollection GetHyperlinks()`.
- `GetModel`: Defined as `Core::WorksheetModel GetModel()`.
- `GetName`: Defined as `std::string GetName()`.
- `GetPageSetup`: Defined as `PageSetup GetPageSetup()`.
- `GetProtection`: Defined as `WorksheetProtection GetProtection()`.
- `GetRightToLeft`: Defined as `bool GetRightToLeft()`.
- `GetShowGridlines`: Defined as `bool GetShowGridlines()`.
- `GetShowRowColumnHeaders`: Defined as `bool GetShowRowColumnHeaders()`.
- `GetShowZeros`: Defined as `bool GetShowZeros()`.
- `GetTabColor`: Defined as `Color GetTabColor()`.
- `GetValidations`: Defined as `ValidationCollection GetValidations()`.
- `GetVisibilityType`: Defined as `VisibilityType GetVisibilityType()`.
- `GetWorkbook`: Defined as `Workbook GetWorkbook()`.
- `GetZoom`: Defined as `int GetZoom()`.
- `Protect`: Defined as `void Protect()`.
- `SetName`: Defined as `void SetName(std::string_view value)`.
- `SetRightToLeft`: Defined as `void SetRightToLeft(bool value)`.
- `SetShowGridlines`: Defined as `void SetShowGridlines(bool value)`.
- `SetShowRowColumnHeaders`: Defined as `void SetShowRowColumnHeaders(bool value)`.
- `SetShowZeros`: Defined as `void SetShowZeros(bool value)`.
- `SetTabColor`: Defined as `void SetTabColor(Color value)`.
- `SetVisibilityType`: Defined as `void SetVisibilityType(VisibilityType value)`.
- `SetZoom`: Defined as `void SetZoom(int value)`.
- `Unprotect`: Defined as `void Unprotect()`.
- `Worksheet`: Defined as `Worksheet Worksheet()`.

### ConditionalFormattingCollection

The `Aspose.Cells_FOSS.ConditionalFormattingCollection` class manages conditional formatting rules applied to cell ranges, while `Aspose.Cells_FOSS.ValidationCollection` handles data validation rules for input control.

- `Add`: Defined as `int Add()`.
- `GetCount`: Defined as `int GetCount()`.
- `GetNextPriority`: Defined as `int GetNextPriority(std::vector<Core::ConditionalFormattingModel> collections)`.
- `RemoveArea`: Defined as `void RemoveArea(int startRow, int startColumn, int totalRows, int totalColumns)`.
- `RemoveAt`: Defined as `void RemoveAt(int index)`.

### HyperlinkCollection

The `Aspose.Cells_FOSS.HyperlinkCollection` class provides methods to add and manage hyperlinks within a worksheet, with `Aspose.Cells_FOSS.DefinedNameCollection` supporting named ranges for formula references.

- `Add`: Defined as `int Add(int firstRow, int firstColumn, int totalRows, int totalColumns, std::string_view address)`.
- `GetCount`: Defined as `int GetCount()`.
- `RemoveAt`: Defined as `void RemoveAt(int index)`.

### WorkbookProperties

The `Aspose.Cells_FOSS.WorkbookProperties` class exposes workbook-level metadata, while `Aspose.Cells_FOSS.DocumentProperties` provides access to standard document properties such as author and title.

- `GetBackupFile`: Defined as `bool GetBackupFile()`.
- `GetCalculation`: Defined as `CalculationProperties GetCalculation()`.
- `GetCodeName`: Defined as `std::string GetCodeName()`.
- `GetDefaultThemeVersion`: Defined as `std::optional<int> GetDefaultThemeVersion()`.
- `GetFilterPrivacy`: Defined as `bool GetFilterPrivacy()`.
- `GetHidePivotFieldList`: Defined as `bool GetHidePivotFieldList()`.
- `GetProtection`: Defined as `WorkbookProtection GetProtection()`.
- `GetSaveExternalLinkValues`: Defined as `bool GetSaveExternalLinkValues()`.
- `GetShowBorderUnselectedTables`: Defined as `bool GetShowBorderUnselectedTables()`.
- `GetShowInkAnnotation`: Defined as `bool GetShowInkAnnotation()`.
- `GetShowObjects`: Defined as `std::string GetShowObjects()`.
- `GetUpdateLinks`: Defined as `std::string GetUpdateLinks()`.
- `GetView`: Defined as `WorkbookView GetView()`.
- `SetBackupFile`: Defined as `void SetBackupFile(bool value)`.
- `SetCodeName`: Defined as `void SetCodeName(std::string_view value)`.
- `SetDefaultThemeVersion`: Defined as `void SetDefaultThemeVersion(std::optional<int> value)`.
- `SetFilterPrivacy`: Defined as `void SetFilterPrivacy(bool value)`.
- `SetHidePivotFieldList`: Defined as `void SetHidePivotFieldList(bool value)`.
- `SetSaveExternalLinkValues`: Defined as `void SetSaveExternalLinkValues(bool value)`.
- `SetShowBorderUnselectedTables`: Defined as `void SetShowBorderUnselectedTables(bool value)`.
- `SetShowInkAnnotation`: Defined as `void SetShowInkAnnotation(bool value)`.
- `SetShowObjects`: Defined as `void SetShowObjects(std::string_view value)`.
- `SetUpdateLinks`: Defined as `void SetUpdateLinks(std::string_view value)`.
- `WorkbookProperties`: Defined as `WorkbookProperties WorkbookProperties()`.

### WorksheetCollection

The `Aspose.Cells_FOSS.WorksheetCollection` class manages the collection of worksheets within a workbook, with `Aspose.Cells_FOSS.Cells` providing direct access to individual cells by row and column indices.

- `Add`: Defined as `int Add()`.
- `GetActiveSheetIndex`: Defined as `int GetActiveSheetIndex()`.
- `GetActiveSheetName`: Defined as `std::string GetActiveSheetName()`.
- `GetCount`: Defined as `int GetCount()`.
- `RemoveAt`: Defined as `void RemoveAt(int index)`.
- `SetActiveSheetIndex`: Defined as `void SetActiveSheetIndex(int value)`.
- `SetActiveSheetName`: Defined as `void SetActiveSheetName(std::string_view value)`.
- `WorksheetCollection`: Defined as `WorksheetCollection WorksheetCollection()`.
- `begin`: Defined as `std::vector<std::unique_ptr<Worksheet>>::const_iterator begin()`.
- `end`: Defined as `std::vector<std::unique_ptr<Worksheet>>::const_iterator end()`.

### Validation

The `Aspose.Cells_FOSS.Validation` class defines data validation rules with types from `Aspose.Cells_FOSS.ValidationType` and operators from `Aspose.Cells_FOSS.ValidationAlertType` for error messaging.

- `AddArea`: Defined as `void AddArea(CellArea area)`.
- `GetAlertStyle`: Defined as `ValidationAlertType GetAlertStyle()`.
- `GetAreas`: Defined as `std::vector<CellArea> GetAreas()`.
- `GetErrorMessage`: Defined as `std::string GetErrorMessage()`.
- `GetErrorTitle`: Defined as `std::string GetErrorTitle()`.
- `GetFormula1`: Defined as `std::string GetFormula1()`.
- `GetFormula2`: Defined as `std::string GetFormula2()`.
- `GetIgnoreBlank`: Defined as `bool GetIgnoreBlank()`.
- `GetInCellDropDown`: Defined as `bool GetInCellDropDown()`.
- `GetInputMessage`: Defined as `std::string GetInputMessage()`.
- `GetInputTitle`: Defined as `std::string GetInputTitle()`.
- `GetOperator`: Defined as `OperatorType GetOperator()`.
- `GetShowError`: Defined as `bool GetShowError()`.
- `GetShowInput`: Defined as `bool GetShowInput()`.
- `GetType`: Defined as `ValidationType GetType()`.
- `RemoveArea`: Defined as `void RemoveArea(CellArea area)`.
- `SetAlertStyle`: Defined as `void SetAlertStyle(ValidationAlertType value)`.
- `SetErrorMessage`: Defined as `void SetErrorMessage(std::string value)`.
- `SetErrorTitle`: Defined as `void SetErrorTitle(std::string value)`.
- `SetFormula1`: Defined as `void SetFormula1(std::string value)`.
- `SetFormula2`: Defined as `void SetFormula2(std::string value)`.
- `SetIgnoreBlank`: Defined as `void SetIgnoreBlank(bool value)`.
- `SetInCellDropDown`: Defined as `void SetInCellDropDown(bool value)`.
- `SetInputMessage`: Defined as `void SetInputMessage(std::string value)`.
- `SetInputTitle`: Defined as `void SetInputTitle(std::string value)`.
- `SetOperator`: Defined as `void SetOperator(OperatorType value)`.
- `SetShowError`: Defined as `void SetShowError(bool value)`.
- `SetShowInput`: Defined as `void SetShowInput(bool value)`.
- `SetType`: Defined as `void SetType(ValidationType value)`.

### AutoFilter

The `Aspose.Cells_FOSS.AutoFilter` class enables filtering of worksheet data using color-based filters via `Aspose.Cells_FOSS.AutoFilterColorFilter` and custom filter expressions via `Aspose.Cells_FOSS.AutoFilterCustomFilter`.

- `Clear`: Defined as `void Clear()`.
- `GetFilterColumns`: Defined as `FilterColumnCollection GetFilterColumns()`.
- `GetRange`: Defined as `std::string GetRange()`.
- `GetSortState`: Defined as `AutoFilterSortState GetSortState()`.
- `SetRange`: Defined as `void SetRange(std::string value)`.

### PageSetup

The `Aspose.Cells_FOSS.PageSetup` class controls print layout options including orientation from `Aspose.Cells_FOSS.PageOrientationType`, paper size from `Aspose.Cells_FOSS.PaperSizeType`, and print area definitions.

- `AddHorizontalPageBreak`: Defined as `void AddHorizontalPageBreak(int rowIndex)`.
- `AddVerticalPageBreak`: Defined as `void AddVerticalPageBreak(int columnIndex)`.
- `ClearHorizontalPageBreaks`: Defined as `void ClearHorizontalPageBreaks()`.
- `ClearVerticalPageBreaks`: Defined as `void ClearVerticalPageBreaks()`.
- `GetBottomMargin`: Defined as `double GetBottomMargin()`.
- `GetBottomMarginInch`: Defined as `double GetBottomMarginInch()`.
- `GetCenterFooter`: Defined as `std::string GetCenterFooter()`.
- `GetCenterHeader`: Defined as `std::string GetCenterHeader()`.
- `GetCenterHorizontally`: Defined as `bool GetCenterHorizontally()`.
- `GetCenterVertically`: Defined as `bool GetCenterVertically()`.
- `GetFirstPageNumber`: Defined as `std::optional<int> GetFirstPageNumber()`.
- `GetFitToPagesTall`: Defined as `std::optional<int> GetFitToPagesTall()`.
- `GetFitToPagesWide`: Defined as `std::optional<int> GetFitToPagesWide()`.
- `GetFooterMargin`: Defined as `double GetFooterMargin()`.
- `GetFooterMarginInch`: Defined as `double GetFooterMarginInch()`.
- `GetHeaderMargin`: Defined as `double GetHeaderMargin()`.
- `GetHeaderMarginInch`: Defined as `double GetHeaderMarginInch()`.
- `GetHorizontalPageBreaks`: Defined as `std::vector<int> GetHorizontalPageBreaks()`.
- `GetLeftFooter`: Defined as `std::string GetLeftFooter()`.
- `GetLeftHeader`: Defined as `std::string GetLeftHeader()`.
- `GetLeftMargin`: Defined as `double GetLeftMargin()`.
- `GetLeftMarginInch`: Defined as `double GetLeftMarginInch()`.
- `GetOrientation`: Defined as `PageOrientationType GetOrientation()`.
- `GetPaperSize`: Defined as `PaperSizeType GetPaperSize()`.
- `GetPrintArea`: Defined as `std::string GetPrintArea()`.
- `GetPrintGridlines`: Defined as `bool GetPrintGridlines()`.
- `GetPrintHeadings`: Defined as `bool GetPrintHeadings()`.
- `GetPrintTitleColumns`: Defined as `std::string GetPrintTitleColumns()`.
- `GetPrintTitleRows`: Defined as `std::string GetPrintTitleRows()`.
- `GetRightFooter`: Defined as `std::string GetRightFooter()`.
- `GetRightHeader`: Defined as `std::string GetRightHeader()`.
- `GetRightMargin`: Defined as `double GetRightMargin()`.
- `GetRightMarginInch`: Defined as `double GetRightMarginInch()`.
- `GetScale`: Defined as `std::optional<int> GetScale()`.
- `GetTopMargin`: Defined as `double GetTopMargin()`.
- `GetTopMarginInch`: Defined as `double GetTopMarginInch()`.
- `GetVerticalPageBreaks`: Defined as `std::vector<int> GetVerticalPageBreaks()`.
- `SetBottomMargin`: Defined as `void SetBottomMargin(double value)`.
- `SetBottomMarginInch`: Defined as `void SetBottomMarginInch(double value)`.
- `SetCenterFooter`: Defined as `void SetCenterFooter(std::string_view value)`.
- `SetCenterHeader`: Defined as `void SetCenterHeader(std::string_view value)`.
- `SetCenterHorizontally`: Defined as `void SetCenterHorizontally(bool value)`.
- `SetCenterVertically`: Defined as `void SetCenterVertically(bool value)`.
- `SetFirstPageNumber`: Defined as `void SetFirstPageNumber(std::optional<int> value)`.
- `SetFitToPagesTall`: Defined as `void SetFitToPagesTall(std::optional<int> value)`.
- `SetFitToPagesWide`: Defined as `void SetFitToPagesWide(std::optional<int> value)`.
- `SetFooterMargin`: Defined as `void SetFooterMargin(double value)`.
- `SetFooterMarginInch`: Defined as `void SetFooterMarginInch(double value)`.
- `SetHeaderMargin`: Defined as `void SetHeaderMargin(double value)`.
- `SetHeaderMarginInch`: Defined as `void SetHeaderMarginInch(double value)`.
- `SetLeftFooter`: Defined as `void SetLeftFooter(std::string_view value)`.
- `SetLeftHeader`: Defined as `void SetLeftHeader(std::string_view value)`.
- `SetLeftMargin`: Defined as `void SetLeftMargin(double value)`.
- `SetLeftMarginInch`: Defined as `void SetLeftMarginInch(double value)`.
- `SetOrientation`: Defined as `void SetOrientation(PageOrientationType value)`.
- `SetPaperSize`: Defined as `void SetPaperSize(PaperSizeType value)`.
- `SetPrintArea`: Defined as `void SetPrintArea(std::string_view value)`.
- `SetPrintGridlines`: Defined as `void SetPrintGridlines(bool value)`.
- `SetPrintHeadings`: Defined as `void SetPrintHeadings(bool value)`.
- `SetPrintTitleColumns`: Defined as `void SetPrintTitleColumns(std::string_view value)`.
- `SetPrintTitleRows`: Defined as `void SetPrintTitleRows(std::string_view value)`.
- `SetRightFooter`: Defined as `void SetRightFooter(std::string_view value)`.
- `SetRightHeader`: Defined as `void SetRightHeader(std::string_view value)`.
- `SetRightMargin`: Defined as `void SetRightMargin(double value)`.
- `SetRightMarginInch`: Defined as `void SetRightMarginInch(double value)`.
- `SetScale`: Defined as `void SetScale(std::optional<int> value)`.
- `SetTopMargin`: Defined as `void SetTopMargin(double value)`.
- `SetTopMarginInch`: Defined as `void SetTopMarginInch(double value)`.

### Color

The `Aspose.Cells_FOSS.Color` class supports color definitions using ARGB values and integrates with `Aspose.Cells_FOSS.FillPattern` and `Aspose.Cells_FOSS.Border` to style cell backgrounds and borders.

- `Color`: Defined as `Color Color()`.
- `Empty`: Defined as `Color Empty()`.
- `Equals`: Defined as `bool Equals(Color other)`.
- `FromArgb`: Defined as `Color FromArgb(int a, int r, int g, int b)`.
- `FromCore`: Defined as `Color FromCore(Core::ColorValue value)`.
- `GetA`: Defined as `std::uint8_t GetA()`.
- `GetB`: Defined as `std::uint8_t GetB()`.
- `GetG`: Defined as `std::uint8_t GetG()`.
- `GetHashCode`: Defined as `int GetHashCode()`.
- `GetR`: Defined as `std::uint8_t GetR()`.
- `ToCore`: Defined as `Core::ColorValue ToCore()`.


- `Workbook`
  - `Workbook()`, `Workbook(fileName)`, `Workbook(fileName, LoadOptions)`, `Workbook(stream, LoadOptions)`
  - `Save(fileName)`, `Save(fileName, SaveFormat)`, `Save(fileName, SaveOptions)`, `Save(stream, SaveFormat)`, `Save(stream, SaveOptions)`
  - Properties: `Worksheets: WorksheetCollection`, `Settings: WorkbookSettings`, `Properties: WorkbookProperties`, `DocumentProperties: DocumentProperties`, `DefinedNames: DefinedNameCollection`, `LoadDiagnostics: LoadDiagnostics`
- `Worksheet`
  - `Protect()`, `Unprotect()`
  - Properties: `Name: string`, `VisibilityType: VisibilityType`, `TabColor: Color`, `ShowGridlines/ShowRowColumnHeaders/ShowZeros/RightToLeft: bool`, `Zoom: int`, `Cells: Cells`, `Hyperlinks: HyperlinkCollection`, `Validations: ValidationCollection`, `ConditionalFormattings: ConditionalFormattingCollection`, `PageSetup: PageSetup`, `Protection: WorksheetProtection`, `AutoFilter: AutoFilter`
- `Cells`
  - `operator[](cellName)`, `operator()(row, column)`, `Merge(firstRow, firstColumn, totalRows, totalColumns)`
  - Properties: `Rows: RowCollection`, `Columns: ColumnCollection`, `MergedCells: vector<CellArea>`
- `Cell`
  - `PutValue(value)` (string/int/double/bool/`DateTime` overloads), `GetValue()`, `SetValue(CellValue)`, `GetStringValue()`, `GetDisplayStringValue()`, `SetFormula(text)`, `GetFormula()`, `GetStyle()`, `SetStyle(Style)`
  - Properties: `Row: int`, `Column: int`, `Type: CellValueType`
- `Style`
  - `GetFont()`/`SetFont(Font)`, `GetBorders()`/`SetBorders(Borders)`, `GetPattern()`/`SetPattern(FillPattern)`, `GetForegroundColor()`/`SetForegroundColor(Color)`, `GetBackgroundColor()`/`SetBackgroundColor(Color)`, `GetNumberFormat()`/`SetNumberFormat(text)`, `GetHorizontalAlignment()`/`SetHorizontalAlignment(...)`, `GetWrapText()`/`SetWrapText(bool)`
- `ConditionalFormattingCollection`
  - `Add()`, `RemoveAt(index)`, `RemoveArea(startRow, startColumn, totalRows, totalColumns)`, `operator[](index) -> FormatConditionCollection`
  - Properties: `Count: int`
- `FormatConditionCollection`
  - `operator[](index) -> FormatCondition`, `AddArea(CellArea)`, `AddCondition(FormatConditionType, OperatorType, formula1, formula2)`, `RemoveArea(CellArea)`, `RemoveCondition(index)`
  - Properties: `Count: int`, `RangeCount: int`
- `FormatCondition`
  - Properties: `Priority: int`, `StopIfTrue: bool`, `Style: Style`, `Formula1: string`, `Formula2: string`, `Type: FormatConditionType`, `Operator: OperatorType`
- `ValidationCollection`
  - `Add(CellArea)`, `operator[](index) -> Validation`, `RemoveACell(row, column)`, `RemoveArea(CellArea)`, `GetValidationInCell(row, column)`
  - Properties: `Count: int`
- `Validation`
  - `AddArea(CellArea)`
  - Properties: `Type: ValidationType`, `Operator: OperatorType`, `Formula1: string`, `Formula2: string`, `ShowError: bool`, `ErrorTitle: string`, `ErrorMessage: string`
- `HyperlinkCollection`
  - `Add(cellName, totalRows, totalColumns, address)`, `RemoveAt(index)`
  - Properties: `Count: int`
- `Hyperlink`
  - Properties: `Area: string`, `Address: string`, `TextToDisplay: string`, `ScreenTip: string`
- `DefinedNameCollection`
  - `Add(name, formula)`, `Add(name, formula, localSheetIndex)`, `RemoveAt(index)`
  - Properties: `Count: int`
- `DefinedName`
  - Properties: `Comment: string`
- `PageSetup`
  - `SetOrientation(PageOrientationType)`, `SetPaperSize(PaperSizeType)`, `SetFitToPagesWide/Tall(int)`, `SetPrintArea(range)`, `SetPrintTitleRows/Columns(range)`, `SetLeftHeader/CenterFooter(text)`, `AddHorizontalPageBreak(row)`, `AddVerticalPageBreak(column)`
  - Properties: `LeftMargin/RightMargin: double`, `Scale: optional<int>`, `PrintGridlines/CenterHorizontally: bool`
- Exceptions
  - `CellsException` — base error type for invalid indices, ranges, and arguments
  - `WorkbookLoadException` / `WorkbookSaveException` — load/save-specific failures
  - `InvalidFileFormatException` — the loaded bytes are not a readable OOXML package
  - `UnsupportedFeatureException` — a requested operation (e.g. non-XLSX save) is not implemented
  - `FormulaException` / `StyleException` — invalid formula text or style value

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/cells/cpp/)** — The getting started guide covers installation, basic walkthroughs, and feature introductions for `aspose_cells_foss_cpp`.
- **[How-to guides & FAQ](https://kb.aspose.org/cells/cpp/)** — The how-to guides and FAQ provide task-focused answers for common spreadsheet operations using `aspose_cells_foss_cpp`.
- **[Full API reference](https://reference.aspose.org/cells/cpp/)** — The full API reference offers a complete, browsable reference for all public types in `aspose_cells_foss_cpp`. It covers all 195 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues).

## Scope and Limitations

Aspose.Cells FOSS for Cpp provides read and write access to Excel workbooks in the .xlsx format using C++17 and CMake 3.16 or later.

- Only .xlsx (OOXML) is supported for load and save, with `LoadFormat` and `SaveFormat` each declaring a single Xlsx member, and saving to any other format throws `UnsupportedFeatureException`.
- Legacy SpreadsheetML (the pre-OOXML Excel 2003 XML dialect) is not implemented, as the mapper classes for it exist in source but their read/write methods unconditionally throw `UnsupportedFeatureException`.
- `Cell`-level comments or notes are not modeled as a distinct object, since the only Comment field in the public API belongs to `DefinedName` and represents a description string on a named range rather than an Excel cell note or threaded comment.
- Some advanced conditional-formatting rule types are recognized on load but not preserved, as an unsupported rule type is dropped with a `WarningInfo` diagnostic rather than failing the load outright.
- `AutoFilter` date-group filters using certain patterns are rejected as unsupported during load rather than approximated.
- Aspose.Cells FOSS for Cpp ships prebuilt static libraries for Windows only built with the MSVC v14x toolset, and its build system errors the build for any other toolset or platform.

These limitations don't apply to [Aspose.Cells for Cpp — Enterprise Edition](https://products.aspose.com/cells/cpp/). The commercial edition of Aspose.Cells FOSS for Cpp extends this package with additional file format support, advanced rendering capabilities, and enterprise-grade features.

## License

This project is licensed under the [MIT License](License/LICENSE.txt). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.

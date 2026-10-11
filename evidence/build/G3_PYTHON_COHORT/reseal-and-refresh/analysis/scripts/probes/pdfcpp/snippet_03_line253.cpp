#include <aspose/pdf/document.hpp>
#include <aspose/pdf/page_collection.hpp>
#include <aspose/pdf/text_builder.hpp>
#include <aspose/pdf/text_fragment.hpp>
#include <aspose/pdf/font_repository.hpp>
#include <aspose/pdf/position.hpp>
#include <aspose/pdf/table.hpp>
#include <aspose/pdf/border_info.hpp>
#include <aspose/pdf/drawing/graph.hpp>
#include <aspose/pdf/drawing/circle.hpp>
#include <aspose/pdf/watermark_artifact.hpp>
int main() {

namespace pdf = Aspose::Pdf;
namespace txt = Aspose::Pdf::Text;
namespace draw = Aspose::Pdf::Drawing;

pdf::Document doc;
pdf::Page page = doc.Pages().Add();   // Page is a lightweight handle
page.SetPageSize(595.0, 842.0);

// Positioned text
txt::TextFragment frag("Hello from Aspose.PDF FOSS for C++");
frag.TextState().Font(txt::FontRepository::FindFont("Helvetica"));
frag.TextState().FontSize(18.0f);
frag.Position(txt::Position(60.0, 760.0));
txt::TextBuilder{page}.AppendText(frag);

// Table — keep alive until doc.Save()
pdf::Table table;
table.ColumnWidths("250 120 120");
table.Border(pdf::BorderInfo(pdf::BorderSide::All, 0.5f));
pdf::Row& header = table.Rows().Add();
header.Cells().Add("Item"); header.Cells().Add("Qty"); header.Cells().Add("Price");
page.Paragraphs().Add(table);

// Vector graphics — keep alive until doc.Save()
draw::Graph g(495.0, 420.0);
g.Left(40.0); g.Top(40.0);
g.Shapes().push_back(std::make_unique<draw::Circle>(180.0f, 500.0f, 70.0f));
page.Paragraphs().Add(g);

// Watermark
pdf::WatermarkArtifact watermark;
page.Artifacts().Add(watermark);

doc.Save("scratch.pdf");
return 0;
}

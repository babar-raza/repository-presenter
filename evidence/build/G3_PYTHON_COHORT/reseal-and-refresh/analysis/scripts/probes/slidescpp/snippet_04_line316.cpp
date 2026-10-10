#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/table.h>
#include <Aspose/Slides/Foss/fill_type.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
int main() {

using namespace Aspose::Slides::Foss;
using namespace Aspose::Slides::Foss::Drawing;

Presentation pres;
std::vector<double> col_widths = {150, 150};
std::vector<double> row_heights = {50};
auto& table = pres.slides()[0].shapes().add_table(50, 50, col_widths, row_heights);
auto& cell = table.rows()[0][0];
cell.text_frame()->set_text("Blue");
cell.cell_format().fill_format().set_fill_type(FillType::SOLID);
cell.cell_format().fill_format().solid_fill_color().set_color(Color::light_blue);
pres.save("table.pptx", SaveFormat::PPTX);
return 0;
}

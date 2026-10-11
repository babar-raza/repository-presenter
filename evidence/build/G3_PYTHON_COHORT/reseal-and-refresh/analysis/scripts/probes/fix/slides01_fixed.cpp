#include <Aspose/Slides/Foss/slide.h>
#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/export/save_format.h>

using namespace Aspose::Slides::Foss;

int main() {
    // Create a new presentation (starts with one blank slide).
    Presentation pres;
    auto& slide = pres.slides()[0];

    // Add a rectangle and set its text.
    auto& shape = slide.shapes().add_auto_shape(ShapeType::RECTANGLE, 50, 50, 400, 150);
    shape.add_text_frame("Hello, Aspose.Slides!");

    pres.save("output.pptx", SaveFormat::PPTX);
    return 0;
}

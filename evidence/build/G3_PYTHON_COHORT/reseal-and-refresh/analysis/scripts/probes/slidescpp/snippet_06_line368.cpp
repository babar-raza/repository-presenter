#include <Aspose/Slides/Foss/presentation.h>
#include <Aspose/Slides/Foss/shape_type.h>
#include <Aspose/Slides/Foss/auto_shape.h>
#include <Aspose/Slides/Foss/drawing/color.h>
#include <Aspose/Slides/Foss/export/save_format.h>
int main() {

using namespace Aspose::Slides::Foss;
using namespace Aspose::Slides::Foss::Drawing;

Presentation pres;
auto& shape = pres.slides()[0].shapes().add_auto_shape(ShapeType::RECTANGLE, 100, 100, 200, 100);
auto& ef = shape.effect_format();
ef.enable_outer_shadow_effect();
auto* shadow = ef.outer_shadow_effect();
shadow->set_blur_radius(10);
shadow->set_direction(315);
shadow->set_distance(8);
shadow->shadow_color().set_color(Color::from_argb(128, 0, 0, 0));
pres.save("shadow.pptx", SaveFormat::PPTX);
return 0;
}

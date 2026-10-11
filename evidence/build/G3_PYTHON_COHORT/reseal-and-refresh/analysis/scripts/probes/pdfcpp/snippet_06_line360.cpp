#include <aspose/pdf/document.hpp>
#include <aspose/pdf/tiff_device.hpp>
#include <aspose/pdf/tiff_settings.hpp>
#include <aspose/pdf/color_depth.hpp>
#include <aspose/pdf/resolution.hpp>
#include <fstream>
int main() {

Aspose::Pdf::Document doc("input.pdf");

// Every page -> one multi-page TIFF
Aspose::Pdf::Devices::TiffDevice tiff(Aspose::Pdf::Devices::Resolution(150));
std::ofstream tiffOut("all_pages.tiff", std::ios::binary);
tiff.Process(doc, 1, static_cast<int>(doc.Pages().Count()), tiffOut);

// 8-bpp palettised TIFF (median-cut palette)
Aspose::Pdf::Devices::TiffSettings settings;
settings.Depth(Aspose::Pdf::Devices::ColorDepth::Format8bpp);
Aspose::Pdf::Devices::TiffDevice indexed(Aspose::Pdf::Devices::Resolution(150), settings);
return 0;
}

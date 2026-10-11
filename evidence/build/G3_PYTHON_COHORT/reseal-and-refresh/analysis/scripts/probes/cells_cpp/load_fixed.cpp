// README.md "Load an Existing Workbook and Read Cells" (lines 172-185), verbatim, wrapped in main()
#include <string>
#include "aspose/cells_foss/Workbook.h"
#include "aspose/cells_foss/WorksheetCollection.h"
#include "aspose/cells_foss/Worksheet.h"
#include "aspose/cells_foss/Cell.h"

using namespace Aspose::Cells_FOSS;

int main() {
Workbook workbook("products.xlsx");
Worksheet& sheet = workbook.GetWorksheets()["Products"];

std::string name = sheet.GetCells()["A2"].GetStringValue();
double price = sheet.GetCells()["B2"].GetValue().AsDouble();
std::string total = sheet.GetCells()["B4"].GetDisplayStringValue();  // formatted formula result
return 0;
}

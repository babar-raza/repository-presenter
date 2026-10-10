#include <aspose/pdf/forms/text_box_field.hpp>
int main() {

namespace frm = Aspose::Pdf::Forms;
frm::TextBoxField name(doc, pdf::Rectangle(190, 700, 470, 720, true));  // keep alive until Save()
name.PartialName("fullName");
name.Value("Alice Sample");
doc.Form().Add(name, /*pageNumber=*/1);
// doc.Form().Flatten();   // bake every field into static page content
return 0;
}

#include <aspose/pdf/outline_collection.hpp>
#include <aspose/pdf/outline_item_collection.hpp>
#include <aspose/pdf/annotations/xyz_explicit_destination.hpp>
int main() {

auto& root = doc.Outlines();
pdf::OutlineItemCollection item(root);               // keep alive until Save()
item.Title("Chapter 1");
item.Bold(true);
item.Destination(ann::XYZExplicitDestination(page, 0.0, 842.0, 0.0));
root.Add(item);
return 0;
}
